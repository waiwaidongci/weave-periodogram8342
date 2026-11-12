import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
class ErrorMiddleware(BaseHTTPMiddleware):
 async def dispatch(self,request,call_next):
  try:return await call_next(request)
  except Exception:
   logging.exception('request failure')
   return JSONResponse({'detail':'服务暂时不可用，请稍后重试','request_id':getattr(request.state,'request_id','')},status_code=500)
