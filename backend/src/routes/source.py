from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers
from src.models import TraverseStudy,TraversePoint
from src.schemas.study import StudyInput
from src.schemas.point import PointPatch
from src.services.source import create_study,edit_point
from src.utils.serialize import row
router=APIRouter()
@router.get('/studies')
def studies(db:Session=Depends(get_db),user=Depends(current_user)):return [row(s) for s in db.scalars(select(TraverseStudy).order_by(TraverseStudy.id))]
@router.post('/studies')
def create(data:StudyInput,db:Session=Depends(get_db),user=Depends(writers)):return create_study(db,data,user.email)
@router.get('/points')
def points(db:Session=Depends(get_db),user=Depends(current_user)):return [row(p) for p in db.scalars(select(TraversePoint).order_by(TraversePoint.study_id,TraversePoint.position))]
@router.patch('/points/{id}')
def point(id:int,data:PointPatch,db:Session=Depends(get_db),user=Depends(writers)):return edit_point(db,id,data,user.email)
