"""HTTP 层冒烟：路由注册、鉴权、resume 门禁与完整崩溃-续跑链路。"""
import copy
import os
import sys
import tempfile

os.environ['JWT_SECRET'] = 'test-secret'
sys.path.insert(0, '/workspace/backend')

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

import redis
from src.config.database import Base
from src.models import SpectrumRun, User
import src.config.database as db_pkg
import src.worker as worker_mod
from src.services.analysis import analyze
from src.services.audit import record
from src.utils.security import issue_token, hash_password

# 旁路 Redis 限流
class FakeRedis:
    def __init__(self, *a, **k): pass
    @classmethod
    def from_url(cls, *a, **k): return cls()
    def incr(self, key): return 1
    def expire(self, key, ttl): return True
    def ping(self): return True
redis.Redis = FakeRedis

engine = create_engine('sqlite:///:memory:',
                       connect_args={'check_same_thread': False},
                       poolclass=StaticPool)
Base.metadata.create_all(engine)
TestSession = sessionmaker(engine, expire_on_commit=False)
db_pkg.engine = engine
db_pkg.SessionLocal = TestSession
worker_mod.SessionLocal = TestSession
worker_mod.ARTIFACT_DIR = tempfile.mkdtemp()

from src.main import app

failures = []


def check(name, cond, detail=''):
    print(('PASS' if cond else 'FAIL'), name, detail)
    if not cond:
        failures.append(name)


with TestSession() as db:
    db.add(User(email='analyst@lingdu.demo', name='a', role='analyst',
                password_hash=hash_password('pw')))
    db.add(User(email='viewer@lingdu.demo', name='v', role='viewer',
                password_hash=hash_password('pw')))
    db.commit()
    uid = db.query(User).filter_by(email='analyst@lingdu.demo').first().id
    vuid = db.query(User).filter_by(email='viewer@lingdu.demo').first().id

token = issue_token(type('U', (), {'id': uid})())
vtok = issue_token(type('U', (), {'id': vuid})())
H = {'Authorization': f'Bearer {token}'}
VH = {'Authorization': f'Bearer {vtok}'}

client = TestClient(app)

# 路由注册
paths = {r.path for r in app.routes}
check('resume route registered', '/runs/{id}/resume' in paths)
check('resume requires auth', client.post('/runs/1/resume').status_code == 401)
check('resume forbidden for viewer',
      client.post('/runs/1/resume', headers=VH).status_code == 403)
check('resume missing run 404', client.post('/runs/999/resume', headers=H).status_code == 404)

# 构造一个失败且带进度的运行
rng = np.random.default_rng(3)
x = np.r_[0., np.cumsum(rng.uniform(0.9, 2.1, 35))]
y = 0.5 + 0.05 * np.cos(2 * np.pi * (x - x[0]) / 10) + rng.normal(0, 0.02, 36)
plan = {'name': 'p', 'frequencies': np.linspace(1 / 30, 1 / 6, 21).tolist(),
        'permutations': 199, 'seed': 234}
points = [{'reference': f'P{i}', 'position': float(v), 'thickness': float(t)}
          for i, (v, t) in enumerate(zip(x, y))]
study = {'id': 1, 'name': 's', 'filename': 'f.csv', 'description': 'd'}
expected = analyze(study, points, plan)

from src.services.permutation import new_checkpoint
from src.services.spectrum import observed_spectrum
from src.services.qr_cache import build_cache
cache = build_cache([p['position'] for p in points], plan['frequencies'])
obs_res, _ = observed_spectrum(cache, [p['thickness'] for p in points])
cp = new_checkpoint(plan, len(points), obs_res['observed_max_power'], obs_res['rss0'])
cp['completed'] = 25
cp['null_maxima'] = expected['global_test']['null_maxima'][:25]

with TestSession() as db:
    run = SpectrumRun(study_id=1, plan_id=1, name='http-run',
                      source_snapshot={'study': study, 'points': points},
                      plan_snapshot=copy.deepcopy(plan), status='failed',
                      progress=copy.deepcopy(cp), error='old failure',
                      created_by='analyst@lingdu.demo')
    db.add(run); db.commit(); rid = run.id

# 无进度的失败运行 -> 409
with TestSession() as db:
    r2 = SpectrumRun(study_id=1, plan_id=1, name='http-run-no-cp',
                     source_snapshot={'study': study, 'points': points},
                     plan_snapshot=copy.deepcopy(plan), status='failed',
                     progress=None, created_by='analyst@lingdu.demo')
    db.add(r2); db.commit(); rid2 = r2.id
resp = client.post(f'/runs/{rid2}/resume', headers=H)
check('resume without checkpoint 409', resp.status_code == 409, resp.text[:80])

# 正常续跑请求：入队并以resume=True投递
real_task = worker_mod.analyze_run
delivered = []


class StubTask:
    def delay(self, id_, **kw):
        delivered.append((id_, kw))


worker_mod.analyze_run = StubTask()
resp = client.post(f'/runs/{rid}/resume', headers=H)
check('resume accepted 200', resp.status_code == 200, resp.text[:120])
check('resume enqueued with flag', delivered == [(rid, {'resume': True})])
check('status flipped to queued', resp.json()['status'] == 'queued'
      and resp.json()['error'] is None)

# 队列中的重复恢复请求 -> 409，不重复投递
resp = client.post(f'/runs/{rid}/resume', headers=H)
check('concurrent resume while queued 409', resp.status_code == 409)
check('no duplicate enqueue', len(delivered) == 1)

# 模拟 worker 真正执行续跑（恢复真实任务函数）
worker_mod.analyze_run = real_task
worker_mod.analyze_run.run(rid, resume=True)
with TestSession() as db:
    done = db.get(SpectrumRun, rid)
    if done.status != 'completed':
        print('DEBUG failed status:', done.status, 'error:', done.error,
              'progress:', done.progress)
    check('worker resume completes run', done.status == 'completed')
    check('resumed p equals uninterrupted',
          done.global_p == expected['global_test']['global_p'])
    check('full null distribution identical',
          done.result['global_test']['null_maxima']
          == expected['global_test']['null_maxima'])
    check('progress wiped after success', done.progress is None)

# 完成后再续跑 -> 409
resp = client.post(f'/runs/{rid}/resume', headers=H)
check('resume completed run 409', resp.status_code == 409)

# GET /runs 能看到进度字段（序列化链路）
with TestSession() as db:
    r3 = SpectrumRun(study_id=1, plan_id=1, name='http-run-visible',
                     source_snapshot={'study': study, 'points': points},
                     plan_snapshot=copy.deepcopy(plan), status='failed',
                     progress=copy.deepcopy(cp), created_by='analyst@lingdu.demo')
    db.add(r3); db.commit(); rid3 = r3.id
resp = client.get('/runs', headers=H)
visible = next(r for r in resp.json() if r['id'] == rid3)
check('progress exposed via API', visible['progress']['completed'] == 25
      and visible['progress']['total'] == 199)

print()
if failures:
    print(f'{len(failures)} FAILURES:', failures); sys.exit(1)
print('ALL HTTP SMOKE TESTS PASSED')
