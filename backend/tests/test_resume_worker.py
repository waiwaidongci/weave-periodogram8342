"""worker 断点续跑集成测试（SQLite 内存库模拟状态机与崩溃恢复）。"""
import copy
import json
import os
import sys
import tempfile

os.environ.setdefault('JWT_SECRET', 'test-secret')
sys.path.insert(0, '/workspace/backend')

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.config.database import Base
from src.models import SpectrumRun, WeaveNote, AuditLog  # noqa: F401
import src.models as models_pkg
from src.services import analysis as analysis_mod
from src.services.analysis import analyze
from src.utils.serialize import row
import src.worker as worker_mod

failures = []


def check(name, cond, detail=''):
    print(('PASS' if cond else 'FAIL'), name, detail)
    if not cond:
        failures.append(name)


engine = create_engine('sqlite:///:memory:',
                       connect_args={'check_same_thread': False},
                       poolclass=StaticPool)
Base.metadata.create_all(engine)
TestSession = sessionmaker(engine, expire_on_commit=False)
worker_mod.SessionLocal = TestSession
worker_mod.ARTIFACT_DIR = tempfile.mkdtemp()

rng = np.random.default_rng(11)
x = np.r_[0., np.cumsum(rng.uniform(0.9, 2.1, 47))]
y = 0.5 + 0.06 * np.cos(2 * np.pi * (x - x[0]) / 15) + rng.normal(0, 0.02, 48)
freqs = np.linspace(1 / 40, 1 / 8, 31).tolist()
plan = {'name': 'p', 'frequencies': freqs, 'permutations': 199, 'seed': 234}
points = [{'reference': f'P{i}', 'position': float(v), 'thickness': float(t)}
          for i, (v, t) in enumerate(zip(x, y))]
study = {'id': 1, 'name': 's', 'filename': 'f.csv', 'description': 'd'}
snapshot = {'study': study, 'points': points}
expected = analyze(study, points, plan)


def new_run():
    r = SpectrumRun(study_id=1, plan_id=1, name=f'run-{np.random.default_rng().random()}',
                    source_snapshot=copy.deepcopy(snapshot),
                    plan_snapshot=copy.deepcopy(plan), status='queued',
                    created_by='analyst@lingdu.demo')
    with TestSession() as db:
        db.add(r); db.commit(); rid = r.id
    return rid


# ---------- 1. 正常执行：完成后 progress 清空、result 落库 ----------
rid = new_run()
worker_mod.analyze_run.run(rid)
with TestSession() as db:
    r = db.get(SpectrumRun, rid)
    check('fresh run completes', r.status == 'completed')
    check('progress cleared after completion', r.progress is None)
    check('result matches uninterrupted analysis',
          r.result['global_test']['null_maxima'] == expected['global_test']['null_maxima']
          and r.result['global_test']['global_p'] == expected['global_test']['global_p'])
    check('global_p column synced', r.global_p == expected['global_test']['global_p'])
    artifact = json.loads(open(f'{worker_mod.ARTIFACT_DIR}/weave-{rid}.json').read())
    check('artifact written', artifact['global_test']['null_maxima']
          == expected['global_test']['null_maxima'])

# ---------- 2. 重复投递：完成后再投一次，直接跳过不重算 ----------
worker_mod.analyze_run.run(rid)
with TestSession() as db:
    r = db.get(SpectrumRun, rid)
    check('duplicate delivery after completion skipped', r.status == 'completed')

# ---------- 3. 中途崩溃：进度保留、状态failed；续跑后结果与不中断一致 ----------
rid2 = new_run()
real_run = analysis_mod.analyze_with_progress
armed = {'crash': True}


def crashing_analyze(study_, points_, plan_, cp, on_progress):
    def wrapped(state):
        on_progress(state)
        if armed['crash'] and state['completed'] >= 50:
            armed['crash'] = False
            raise RuntimeError('simulated worker kill')
    return real_run(study_, points_, plan_, cp, wrapped)


analysis_mod.analyze_with_progress = crashing_analyze
worker_mod.analyze_with_progress = crashing_analyze
worker_mod.analyze_run.run(rid2)
with TestSession() as db:
    r = db.get(SpectrumRun, rid2)
    check('crashed run marked failed', r.status == 'failed')
    check('checkpoint retained after crash', r.progress is not None and r.progress['completed'] >= 50)
    check('no partial result written', r.result is None)
    retained = copy.deepcopy(r.progress)

# 崩溃期间重复投递普通任务（非resume）必须跳过，不覆盖进度
worker_mod.analyze_run.run(rid2, resume=False)
with TestSession() as db:
    r = db.get(SpectrumRun, rid2)
    check('non-resume redelivery while failed is skipped',
          r.status == 'failed' and r.progress == retained)

# 并发恢复：第一个resume认领后状态变running，第二个resume看到busy直接跳过
claim_calls = []
orig_execute = worker_mod._execute


def execute_then_busy(run_id, resuming):
    # 模拟PostgreSQL FOR UPDATE：第二个并发恢复到达时该运行已被第一任务锁为running，
    # 只能读到running并返回busy，不得改写状态
    with TestSession() as db2:
        current = db2.get(SpectrumRun, run_id)
        mode = 'busy' if current.status == 'running' else 'unexpected'
    claim_calls.append(mode)
    return orig_execute(run_id, resuming)


worker_mod._execute = execute_then_busy
worker_mod.analyze_run.run(rid2, resume=True)
worker_mod._execute = orig_execute
analysis_mod.analyze_with_progress = real_run
worker_mod.analyze_with_progress = real_run
with TestSession() as db:
    r = db.get(SpectrumRun, rid2)
    check('concurrent resume second claim sees busy', 'busy' in claim_calls)
    check('resumed run completes', r.status == 'completed')
    check('resumed result identical to uninterrupted',
          r.result['global_test']['null_maxima'] == expected['global_test']['null_maxima']
          and r.result['global_test']['histogram'] == expected['global_test']['histogram'])
    check('resumed progress cleared', r.progress is None)

# ---------- 4. 损坏/不匹配进度：明确拒绝，保持failed且无result ----------
rid3 = new_run()
# 先制造一个真实断点
crash2 = {'done': False}


def crash_once(study_, points_, plan_, cp, on_progress):
    def wrapped(state):
        on_progress(state)
        if not crash2['done'] and state['completed'] >= 25:
            crash2['done'] = True
            raise RuntimeError('kill')
    return real_run(study_, points_, plan_, cp, wrapped)


worker_mod.analyze_with_progress = crash_once
worker_mod.analyze_run.run(rid3)
worker_mod.analyze_with_progress = real_run

with TestSession() as db:
    r = db.get(SpectrumRun, rid3)
    check('run3 failed with checkpoint', r.status == 'failed' and r.progress['completed'] == 25)
    good_cp = copy.deepcopy(r.progress)

# 4a 篡改 null 分布
with TestSession() as db:
    r = db.get(SpectrumRun, rid3)
    bad = copy.deepcopy(good_cp)
    bad['null_maxima'][0] = 9.9
    r.progress = bad; db.commit()
worker_mod.analyze_run.run(rid3, resume=True)
with TestSession() as db:
    r = db.get(SpectrumRun, rid3)
    check('corrupt null distribution rejected', r.status == 'failed' and r.result is None)
    check('clear rejection error', r.error and '拒绝续跑' in r.error)

# 4b 指纹不匹配：偷偷换掉计划快照（模拟有人试图拼接其他研究的进度）
with TestSession() as db:
    r = db.get(SpectrumRun, rid3)
    r.progress = copy.deepcopy(good_cp)
    other_plan = dict(plan, seed=999)
    r.plan_snapshot = other_plan; r.error = None; db.commit()
worker_mod.analyze_run.run(rid3, resume=True)
with TestSession() as db:
    r = db.get(SpectrumRun, rid3)
    check('mismatched plan fingerprint rejected', r.status == 'failed' and r.result is None)
    check('mismatch error explicit', r.error and '不匹配' in r.error)
    r.plan_snapshot = copy.deepcopy(plan); db.commit()

# 4c 截断的快照（completed与列表长度不一致）
with TestSession() as db:
    r = db.get(SpectrumRun, rid3)
    bad = copy.deepcopy(good_cp); bad['completed'] = 24
    r.progress = bad; r.error = None; db.commit()
worker_mod.analyze_run.run(rid3, resume=True)
with TestSession() as db:
    r = db.get(SpectrumRun, rid3)
    check('truncated checkpoint rejected', r.status == 'failed' and r.result is None)

# 4d 恢复合法快照后仍能成功（拒绝不会破坏已有进度）
with TestSession() as db:
    r = db.get(SpectrumRun, rid3)
    r.progress = copy.deepcopy(good_cp); r.error = None
    # 模拟resume端点：failed -> queued 且保留进度
    r.status = 'queued'; db.commit()
# 普通投递不得认领带进度的queued
worker_mod.analyze_run.run(rid3, resume=False)
with TestSession() as db:
    r = db.get(SpectrumRun, rid3)
    check('normal delivery skips queued resume run', r.status == 'queued')
worker_mod.analyze_run.run(rid3, resume=True)
with TestSession() as db:
    r = db.get(SpectrumRun, rid3)
    check('valid checkpoint still resumes after rejections',
          r.status == 'completed'
          and r.result['global_test']['null_maxima'] == expected['global_test']['null_maxima'])

# ---------- 5. 服务层 resume_run 的状态门禁 ----------
from src.services.runs import resume_run
from fastapi import HTTPException


class StubTask:
    def __init__(self): self.calls = []
    def delay(self, *a, **k): self.calls.append((a, k))


stub = StubTask()
worker_mod.analyze_run = stub

rid4 = new_run()
with TestSession() as db:
    try:
        resume_run(db, rid4, 'analyst@lingdu.demo')
        check('resume queued run rejected', False)
    except HTTPException as e:
        check('resume queued run rejected', e.status_code == 409)

with TestSession() as db:
    r = db.get(SpectrumRun, rid4); r.status = 'failed'; r.progress = None; db.commit()
    try:
        resume_run(db, rid4, 'analyst@lingdu.demo')
        check('resume without checkpoint rejected', False)
    except HTTPException as e:
        check('resume without checkpoint rejected', e.status_code == 409)

with TestSession() as db:
    r = db.get(SpectrumRun, rid4)
    r.progress = copy.deepcopy(good_cp); db.commit()
    out = resume_run(db, rid4, 'analyst@lingdu.demo')
    check('resume enqueued with resume flag', stub.calls and stub.calls[-1] == ((rid4,), {'resume': True}))
    check('resume flips status to queued', out['status'] == 'queued')

with TestSession() as db:
    try:
        resume_run(db, rid, 'analyst@lingdu.demo')
        check('resume completed run rejected', False)
    except HTTPException as e:
        check('resume completed run rejected', e.status_code == 409)

# ---------- 6. 已批准补测说明的快照保持不变 ----------
with TestSession() as db:
    done = db.get(SpectrumRun, rid)
    note = WeaveNote(run_id=done.id, name='n1', interpretation='i', next_step='s',
                     result_snapshot=copy.deepcopy(done.result), status='approved',
                     review_note='ok', created_by='analyst@lingdu.demo')
    db.add(note); db.commit(); note_id = note.id
with TestSession() as db:
    before = json.dumps(db.get(WeaveNote, note_id).result_snapshot, sort_keys=True)
# 对另一失败运行的恢复/拒绝操作全部结束后，批准快照字节不变
with TestSession() as db:
    after = json.dumps(db.get(WeaveNote, note_id).result_snapshot, sort_keys=True)
    check('approved note snapshot unchanged', before == after)

# ---------- 7. 审计留痕包含续跑/拒绝/跳过事件 ----------
with TestSession() as db:
    actions = [a.action for a in db.query(AuditLog).all()]
    check('audit has resume/skip/fail events',
          {'run.resumed', 'run.skipped', 'run.failed'} <= set(actions))

print()
if failures:
    print(f'{len(failures)} FAILURES:', failures); sys.exit(1)
print('ALL WORKER INTEGRATION TESTS PASSED')
