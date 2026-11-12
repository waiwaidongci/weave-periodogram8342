from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,DateTime,JSON
from datetime import datetime,timezone
from src.config.database import Base
class AuditLog(Base):
 __tablename__='audit_logs'
 id:Mapped[int]=mapped_column(primary_key=True)
 actor:Mapped[str]=mapped_column(String(120))
 action:Mapped[str]=mapped_column(String(100))
 detail:Mapped[dict]=mapped_column(JSON,default=dict)
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
