"""断点续跑算法层测试：数值等价、确定性顺序、损坏/不匹配拒绝、重复批次不累计。"""
import copy
import json
import sys

import numpy as np

sys.path.insert(0, '/workspace/backend')

from src.services.qr_cache import build_cache
from src.services.spectrum import observed_spectrum
from src.services.permutation import (
    global_permutation, new_checkpoint, validate_checkpoint,
    run_permutations, permutation_sequence, BATCH_SIZE,
)
from src.services.analysis import analyze, analyze_with_progress

rng = np.random.default_rng(7)
x = np.r_[0., np.cumsum(rng.uniform(0.8, 2.3, 59))]
y = 0.5 + 0.07 * np.cos(2 * np.pi * (x - x[0]) / 12 - 0.4) + rng.normal(0, 0.02, 60)
freqs = np.linspace(1 / 40, 1 / 8, 41).tolist()
plan = {'frequencies': freqs, 'permutations': 199, 'seed': 234, 'name': 't'}

cache = build_cache(x.tolist(), freqs)
result, centered = observed_spectrum(cache, y)
obs, rss0 = result['observed_max_power'], result['rss0']

failures = []


def check(name, cond, detail=''):
    print(('PASS' if cond else 'FAIL'), name, detail)
    if not cond:
        failures.append(name)


# 1. 确定性置换序列：两次生成完全一致，且与旧rng.permutation逐条相同
seq_a = permutation_sequence(len(centered), 199, 234)
legacy_rng = np.random.default_rng(234)
seq_legacy = [legacy_rng.permutation(len(centered)) for _ in range(199)]
check('deterministic sequence stable',
      all(np.array_equal(a, b) for a, b in zip(seq_a, permutation_sequence(len(centered), 199, 234))))
check('sequence matches legacy rng order',
      all(np.array_equal(a, b) for a, b in zip(seq_a, seq_legacy)))

# 2. 直通结果（旧口径）与分段续跑结果完全一致
full = global_permutation(cache, centered, rss0, obs, 199, 234)

saved_states = []
cp = new_checkpoint(plan, len(centered), obs, rss0)
resumed = run_permutations(cache, centered, rss0, obs, plan, cp,
                           on_progress=lambda s: saved_states.append(copy.deepcopy(s)))
check('resumed equals uninterrupted global_p', resumed['global_p'] == full['global_p'])
check('resumed equals uninterrupted null maxima',
      resumed['null_maxima'] == full['null_maxima'])
check('resumed equals histogram',
      resumed['histogram'] == full['histogram'])
check('all B permutations counted', resumed['permutations'] == 199)
check('progress saved in batches only', len(saved_states) == int(np.ceil(199 / BATCH_SIZE)))
check('batch progress monotonic',
      all(s['completed'] == min(BATCH_SIZE * (i + 1), 199) for i, s in enumerate(saved_states)))

# 3. 从任意中间断点恢复，结果仍与不中断一致（模拟崩溃后重投）
for cut in (1, 25, 26, 100, 175):
    mid = copy.deepcopy(saved_states[[s['completed'] for s in saved_states].index(
        min(c for c in [s['completed'] for s in saved_states] if c >= cut))])
    again = run_permutations(cache, centered, rss0, obs, plan, mid, on_progress=lambda s: None)
    check(f'resume from {mid["completed"]} identical', again['null_maxima'] == full['null_maxima'])
    check(f'resume from {mid["completed"]} no duplicate accumulation',
          again['permutations'] == 199)

# 4. analyze 与 analyze_with_progress 全结果一致
points = [{'reference': f'P{i}', 'position': float(v), 'thickness': float(t)}
          for i, (v, t) in enumerate(zip(x, y))]
study = {'id': 1, 'name': 's', 'filename': 'f.csv', 'description': 'd'}
r1 = analyze(study, points, plan)
r2 = analyze_with_progress(study, points, plan, None, on_progress=lambda s: None)
check('analyze == analyze_with_progress',
      json.dumps(r1, sort_keys=True, allow_nan=False) == json.dumps(r2, sort_keys=True, allow_nan=False))

# 5. 损坏/不匹配快照必须明确拒绝，不能拼出成功
def expect_reject(label, mutate):
    bad = copy.deepcopy(saved_states[-1])
    mutate(bad)
    try:
        validate_checkpoint(bad, plan, len(centered), obs, rss0)
        check(label, False, '未拒绝')
    except ValueError as e:
        check(label, True, str(e)[:30])

expect_reject('reject non-dict', lambda b: b.clear())
expect_reject('reject wrong version', lambda b: b.update(version=9))
expect_reject('reject tampered B', lambda b: b.update(total=300))
expect_reject('reject tampered seed', lambda b: b.update(seed=999))
expect_reject('reject completed overflow', lambda b: b.update(completed=200))
expect_reject('reject count/list mismatch', lambda b: b.update(completed=10))
expect_reject('reject NaN null value', lambda b: b['null_maxima'].__setitem__(0, float('nan')))
expect_reject('reject out-of-range null', lambda b: b['null_maxima'].__setitem__(0, 1.7))
expect_reject('reject bool counter', lambda b: b.update(completed=True))
expect_reject('reject extra field', lambda b: b.update(extra=1))
expect_reject('reject missing field', lambda b: b.pop('seed'))
expect_reject('reject bad fingerprint hex', lambda b: b.update(fingerprint='z' * 64))

# 指纹不匹配：改计划/测点规模/观测统计
mismatch_plan = dict(plan, seed=235)
try:
    validate_checkpoint(saved_states[-1], mismatch_plan, len(centered), obs, rss0)
    check('reject mismatched plan fingerprint', False)
except ValueError:
    check('reject mismatched plan fingerprint', True)
try:
    validate_checkpoint(saved_states[-1], plan, len(centered) - 1, obs, rss0)
    check('reject mismatched n_points', False)
except ValueError:
    check('reject mismatched n_points', True)
try:
    validate_checkpoint(saved_states[-1], plan, len(centered), obs + 1e-6, rss0)
    check('reject mismatched observed max', False)
except ValueError:
    check('reject mismatched observed max', True)
# 篡改指纹内容但保持hex合法
bad = copy.deepcopy(saved_states[-1]); bad['fingerprint'] = 'a' * 64
try:
    validate_checkpoint(bad, plan, len(centered), obs, rss0)
    check('reject forged fingerprint', False)
except ValueError:
    check('reject forged fingerprint', True)

# 6. 重复投递同一批进度不重复累计：以已完成50的快照再跑，仍恰好199且顺序位置正确
mid50 = copy.deepcopy(next(s for s in saved_states if s['completed'] == 50))
out = run_permutations(cache, centered, rss0, obs, plan, mid50, on_progress=lambda s: None)
check('redelivery does not double count', out['permutations'] == 199
      and out['null_maxima'] == full['null_maxima'])

print()
if failures:
    print(f'{len(failures)} FAILURES:', failures); sys.exit(1)
print('ALL ALGORITHM TESTS PASSED')
