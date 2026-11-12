from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.config.database import get_db
from src.models import User
from src.schemas.auth import LoginInput
from src.utils.security import verify_password,issue_token
from src.utils.serialize import row
from src.services.audit import record
from src.controllers.dependencies import current_user
router=APIRouter(prefix='/auth',tags=['auth'])
@router.post('/login')
def login(data:LoginInput,db:Session=Depends(get_db)):
 user=db.scalar(select(User).where(User.email==data.email))
 if not user or not verify_password(data.password,user.password_hash): raise HTTPException(401,'邮箱或密码错误')
 record(db,user.email,'auth.login');return {'token':issue_token(user),'user':row(user)}
@router.get('/me')
def me(user=Depends(current_user)): return row(user)
