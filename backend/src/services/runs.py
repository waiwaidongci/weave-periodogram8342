from sqlalchemy import select
from fastapi import HTTPException
from src.models import SpectrumRun,FrequencyPlan
from src.utils.serialize import row
from .source import source_data
from .validation import validate_points,validate_plan
from .audit import record
def create_run(db,data,actor):
 study,points=source_data(db,data.study_id);plan=db.get(FrequencyPlan,data.plan_id)
 if not plan or plan.study_id!=study['id']:raise HTTPException(422,'频率计划不属于该测线')
 snapshot=row(plan)
 try:validate_points(points);validate_plan(snapshot)
 except ValueError as error:raise HTTPException(422,str(error))
 if db.scalar(select(SpectrumRun).where(SpectrumRun.name==data.name)):raise HTTPException(409,'运行名已存在')
 run=SpectrumRun(study_id=study['id'],plan_id=plan.id,name=data.name,source_snapshot={'study':study,'points':points},plan_snapshot=snapshot,created_by=actor);db.add(run);db.commit()
 try:
  from src.worker import analyze_run
  analyze_run.delay(run.id)
 except Exception:
  run.status='failed';run.error='队列不可用，请稍后重建';db.commit();raise HTTPException(503,run.error)
 record(db,actor,'run.queued',{'run_id':run.id});return row(run)

def resume_run(db,id,actor):
 """失败运行断点续跑：沿用排队时的测点/频率计划快照与随机顺序，不新建运行。"""
 run=db.query(SpectrumRun).filter(SpectrumRun.id==id).with_for_update().first()
 if not run:raise HTTPException(404,'运行不存在')
 if run.status=='completed':raise HTTPException(409,'运行已完成，无需续跑')
 if run.status=='running' or run.status=='queued':raise HTTPException(409,'运行仍在队列或计算中，禁止并发恢复')
 if run.status!='failed':raise HTTPException(409,'仅失败运行可断点续跑')
 if not run.progress:raise HTTPException(409,'无可用进度快照，须重新排队运行')
 # 快照不可变：续跑只读取排队时冻结的source_snapshot/plan_snapshot，不接受任何新输入
 run.status='queued';run.error=None;db.commit()
 try:
  from src.worker import analyze_run
  analyze_run.delay(run.id,resume=True)
 except Exception:
  run.status='failed';run.error='队列不可用，请稍后重建';db.commit();raise HTTPException(503,run.error)
 record(db,actor,'run.resumed',{'run_id':id,'completed':run.progress.get('completed',0),
        'total':run.progress.get('total')});return row(run)
