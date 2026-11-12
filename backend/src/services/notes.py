from sqlalchemy import select
from fastapi import HTTPException
from src.models import SpectrumRun,WeaveNote
from src.utils.serialize import row
from .audit import record

def create_note(db,data,actor):
 run=db.get(SpectrumRun,data.run_id)
 if not run or run.status!='completed':raise HTTPException(422,'仅成功谱研究可提交补测说明')
 if db.scalar(select(WeaveNote).where(WeaveNote.name==data.name)):raise HTTPException(409,'说明名已存在')
 note=WeaveNote(**data.model_dump(),result_snapshot=run.result,created_by=actor);db.add(note);db.commit();record(db,actor,'note.created',{'note_id':note.id});return row(note)

def approve_note(db,id,data,actor):
 note=db.scalar(select(WeaveNote).where(WeaveNote.id==id).with_for_update())
 if not note:raise HTTPException(404,'说明不存在')
 if note.status!='draft':raise HTTPException(409,'已审阅，不可重复审批')
 note.status=data.status;note.review_note=data.review_note;db.commit();record(db,actor,'note.reviewed',{'note_id':id,'status':note.status});return row(note)
