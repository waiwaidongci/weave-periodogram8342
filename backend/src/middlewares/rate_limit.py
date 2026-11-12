import hashlib,time
from redis import Redis,RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from src.config.settings import REDIS_URL,RATE_LIMIT_WRITES
class RateLimitMiddleware(BaseHTTPMiddleware):
 async def dispatch(self,request,call_next):
  if request.method in ('POST','PATCH','DELETE'):
   identity=request.headers.get('authorization') or (request.client.host if request.client else 'unknown');digest=hashlib.sha256(identity.encode()).hexdigest()[:24];bucket=int(time.time()//60);key=f'weave:write-limit:{digest}:{bucket}'
   try:
    redis=Redis.from_url(REDIS_URL,socket_timeout=2);count=redis.incr(key)
    if count==1:redis.expire(key,120)
   except RedisError:return JSONResponse({'detail':'限流计数服务不可用，请稍后重试'},status_code=503)
   if count>RATE_LIMIT_WRITES:return JSONResponse({'detail':'本分钟写请求超过配额，请稍后重试'},status_code=429,headers={'Retry-After':str(60-int(time.time()%60))})
  return await call_next(request)
