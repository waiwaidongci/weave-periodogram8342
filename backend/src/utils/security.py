import hashlib,hmac,secrets
from datetime import datetime,timedelta,timezone
import jwt
from src.config.settings import JWT_SECRET
def hash_password(password):
 salt=secrets.token_hex(16)
 digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),210000).hex()
 return f'{salt}${digest}'
def verify_password(password,stored):
 salt,digest=stored.split('$')
 return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),210000).hex(),digest)
def issue_token(user):
 return jwt.encode({'sub':str(user.id),'exp':datetime.now(timezone.utc)+timedelta(hours=8)},JWT_SECRET,algorithm='HS256')
def decode_token(token): return jwt.decode(token,JWT_SECRET,algorithms=['HS256'])
