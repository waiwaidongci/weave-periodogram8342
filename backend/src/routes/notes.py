from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.controllers.dependencies import current_user,writers,admins
from src.models import WeaveNote
from src.schemas.note import NoteInput,ApprovalInput
from src.services.notes import create_note,approve_note
from src.controllers.export import export_note
from src.utils.serialize import row
router=APIRouter()
@router.get('/notes')
def notes(db:Session=Depends(get_db),user=Depends(current_user)):return [row(n) for n in db.scalars(select(WeaveNote).order_by(WeaveNote.id.desc()))]
@router.post('/notes')
def create(data:NoteInput,db:Session=Depends(get_db),user=Depends(writers)):return create_note(db,data,user.email)
@router.patch('/notes/{id}/approval')
def approve(id:int,data:ApprovalInput,db:Session=Depends(get_db),user=Depends(admins)):return approve_note(db,id,data,user.email)
@router.get('/notes/{id}/export')
def export(id:int,db:Session=Depends(get_db),user=Depends(current_user)):return export_note(db,id,user.email)
