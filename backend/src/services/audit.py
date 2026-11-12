from src.models import AuditLog
def record(db,actor,action,detail=None):
 db.add(AuditLog(actor=actor,action=action,detail=detail or {}));db.commit()
