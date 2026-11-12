from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers
from src.models import FrequencyPlan
from src.schemas.plan import PlanInput
from src.services.plans import create_plan
from src.utils.serialize import row
router=APIRouter()
@router.get('/plans')
def plans(db:Session=Depends(get_db),user=Depends(current_user)):return [row(p) for p in db.scalars(select(FrequencyPlan).order_by(FrequencyPlan.id.desc()))]
@router.post('/plans')
def create(data:PlanInput,db:Session=Depends(get_db),user=Depends(writers)):return create_plan(db,data,user.email)
