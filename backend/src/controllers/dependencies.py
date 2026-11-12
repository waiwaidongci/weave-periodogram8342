from fastapi import Depends,HTTPException
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.models import User
from src.constants.enums import Role
from src.utils.security import decode_token
bearer=HTTPBearer(auto_error=False)
def current_user(credentials:HTTPAuthorizationCredentials|None=Depends(bearer),db:Session=Depends(get_db)):
 try:
  user=db.get(User,int(decode_token(credentials.credentials)['sub'])) if credentials else None
 except Exception: user=None
 if not user: raise HTTPException(401,'登录已失效，请重新登录')
 return user
def writers(user:User=Depends(current_user)):
 if user.role not in (Role.ADMIN,Role.ANALYST): raise HTTPException(403,'观察员只能阅读')
 return user
def admins(user:User=Depends(current_user)):
 if user.role!=Role.ADMIN: raise HTTPException(403,'仅织纹研究负责人可审核')
 return user
