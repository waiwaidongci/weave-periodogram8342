import json
from pathlib import Path
from celery import Celery
from src.config.database import SessionLocal
from src.config.settings import REDIS_URL,ARTIFACT_DIR
from src.models import SpectrumRun
from src.services.analysis import analyze_with_progress
from src.services.audit import record
app=Celery('weave_periodogram',broker=REDIS_URL,backend=REDIS_URL)
app.conf.update(task_track_started=True,worker_prefetch_multiplier=1,task_acks_late=True)

def _persist_artifact(id,result):
 Path(ARTIFACT_DIR).mkdir(parents=True,exist_ok=True)
 Path(ARTIFACT_DIR,f'weave-{id}.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False))

def _save_progress(run_id,checkpoint):
 """独立短事务落盘：长计算被kill时已完成批次仍在库；只允许从当前完成数单调向前推进。"""
 with SessionLocal() as writer:
  target=writer.get(SpectrumRun,run_id)
  if target is None or target.status!='running':
   raise RuntimeError('运行状态已变化，拒绝写入进度')
  if (target.progress or {}).get('completed',0)>checkpoint['completed']:
   raise RuntimeError('检测到更新的进度，拒绝覆盖')
  target.progress=checkpoint;writer.commit()

def _execute(run_id,resuming):
 """执行体：只读取排队时冻结的快照，进度按批落盘，完成结果在独立事务中一次性提交。"""
 with SessionLocal() as reader:
  run=reader.get(SpectrumRun,run_id)
  if run is None or run.status!='running':
   raise RuntimeError('运行未处于计算中，拒绝执行')
  snapshot=run.source_snapshot;plan=run.plan_snapshot
  checkpoint=run.progress if resuming else None
  result=analyze_with_progress(snapshot['study'],snapshot['points'],plan,checkpoint,
                               lambda state:_save_progress(run_id,state))
 _persist_artifact(run_id,result)
 with SessionLocal() as writer:
  target=writer.get(SpectrumRun,run_id)
  if target is None or target.status!='running':
   raise RuntimeError('运行状态已变化，拒绝写入结果')
  target.result=result;target.peak_frequency=result['best']['frequency']
  target.max_power=result['observed_max_power']
  target.global_p=result['global_test']['global_p']
  target.status='completed';target.error=None;target.progress=None
  writer.commit()
 with SessionLocal() as audit:
  record(audit,'worker','run.completed',{'run_id':run_id,'global_p':result['global_test']['global_p'],'resumed':resuming})

def _claim(db,id,allow_resume):
 """行锁认领运行；重复投递、并发恢复在这里被挡下，绝不重复累计。"""
 run=db.query(SpectrumRun).filter(SpectrumRun.id==id).with_for_update().first()
 if run is None:return None,'missing'
 if run.status=='completed':return run,'completed'
 if run.status=='running':return run,'busy'
 if run.status=='queued':
  if run.progress is not None:
   # 带进度的queued是resume端点投递的续跑任务：仅resume投递可认领，普通投递跳过
   if not allow_resume:return run,'queued_resume_skip'
   run.status='running';run.error=None;db.commit()
   return run,'resume'
  run.status='running';run.error=None;db.commit()
  return run,'fresh'
 if run.status=='failed':
  if not allow_resume:return run,'failed_no_resume'
  if run.progress is None:return run,'no_checkpoint'
  # 损坏或不匹配的进度在_execute内validate_checkpoint明确拒绝，不拼成功结果
  run.status='running';run.error=None;db.commit()
  return run,'resume'
 return run,'unknown'

@app.task(name='weave.analyze',bind=True,soft_time_limit=120,time_limit=150)
def analyze_run(self,id,resume=False):
 with SessionLocal() as db:
  try:
   run,mode=_claim(db,id,allow_resume=bool(resume))
  except ValueError as error:
   db.rollback()
   with SessionLocal() as fail:
    target=fail.get(SpectrumRun,id)
    if target is not None and target.status=='failed':target.error=str(error)[:1000];fail.commit()
   with SessionLocal() as audit:
    record(audit,'worker','run.resume_rejected',{'run_id':id,'reason':str(error)})
   return
  if run is None:return
  if mode!='fresh' and mode!='resume':
   with SessionLocal() as audit:
    record(audit,'worker','run.skipped',{'run_id':id,'reason':mode})
   return
  resuming=mode=='resume'
 try:
  _execute(id,resuming)
 except Exception as error:
  with SessionLocal() as fail:
   target=fail.get(SpectrumRun,id)
   if target is None:return
   # 进度保留在progress列中，供下次断点续跑；不写result，不产出伪造成功
   target.status='failed';target.error=str(error)[:1000];fail.commit()
   completed=(target.progress or {}).get('completed',0)
  with SessionLocal() as audit:
   record(audit,'worker','run.failed',{'run_id':id,'error':str(error)[:1000],
          'resumed':resuming,'completed':completed})
