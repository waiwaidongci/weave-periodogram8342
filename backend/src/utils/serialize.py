from datetime import datetime,date
from sqlalchemy import inspect
def row(obj):
 return {c.key:(getattr(obj,c.key).isoformat() if isinstance(getattr(obj,c.key),(datetime,date)) else getattr(obj,c.key)) for c in inspect(obj).mapper.column_attrs if c.key!='password_hash'}
