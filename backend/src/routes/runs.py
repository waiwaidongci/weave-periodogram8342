from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers
from src.models import SpectrumRun
from src.schemas.run import RunInput
from src.services.runs import create_run
from src.utils.serialize import row
router=APIRouter()
@router.get('/runs')
def runs(db:Session=Depends(get_db),user=Depends(current_user)):return [row(r) for r in db.scalars(select(SpectrumRun).order_by(SpectrumRun.id.desc()))]
@router.get('/runs/{id}')
def one(id:int,db:Session=Depends(get_db),user=Depends(current_user)):
 run=db.get(SpectrumRun,id)
 if not run:raise HTTPException(404,'运行不存在')
 return row(run)
@router.post('/runs')
def create(data:RunInput,db:Session=Depends(get_db),user=Depends(writers)):return create_run(db,data,user.email)
