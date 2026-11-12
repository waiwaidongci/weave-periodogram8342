import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from redis import Redis
from src.config.database import Base,engine
from src.config.settings import REDIS_URL,SEED_DEMO
from src.models import *
from src.middlewares.request_id import RequestIDMiddleware
from src.middlewares.errors import ErrorMiddleware
from src.middlewares.rate_limit import RateLimitMiddleware
from src.routes import auth,source,plans,runs,notes,audit
@asynccontextmanager
async def lifespan(app):
 Base.metadata.create_all(engine)
 if SEED_DEMO:
  try:
   from scripts.seed_demo import seed
   seed()
  except Exception:logging.exception('seed failure; startup continues')
 yield
app=FastAPI(title='绫度织纹谱峰研究册',lifespan=lifespan)
@app.exception_handler(RequestValidationError)
async def invalid_input(request,error):return JSONResponse({'detail':[{'loc':e['loc'],'message':e['msg'],'type':e['type']} for e in error.errors()]},status_code=422)
app.add_middleware(ErrorMiddleware);app.add_middleware(RateLimitMiddleware);app.add_middleware(RequestIDMiddleware)
for route in (auth,source,plans,runs,notes,audit):app.include_router(route.router)
@app.get('/health')
def health():
 with engine.connect() as c:c.execute(text('select 1'))
 Redis.from_url(REDIS_URL).ping();return {'status':'ok'}
