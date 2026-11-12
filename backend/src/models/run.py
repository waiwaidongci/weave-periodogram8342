from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import ForeignKey,String,Double,JSON,Text,DateTime
from datetime import datetime,timezone
from src.config.database import Base
class SpectrumRun(Base):
 __tablename__='spectrum_runs'
 id:Mapped[int]=mapped_column(primary_key=True)
 study_id:Mapped[int]=mapped_column(ForeignKey('traverse_studies.id'))
 plan_id:Mapped[int]=mapped_column(ForeignKey('frequency_plans.id'))
 name:Mapped[str]=mapped_column(String(180),unique=True)
 source_snapshot:Mapped[dict]=mapped_column(JSON)
 plan_snapshot:Mapped[dict]=mapped_column(JSON)
 status:Mapped[str]=mapped_column(String(24),default='queued')
 result:Mapped[dict|None]=mapped_column(JSON,nullable=True)
 error:Mapped[str|None]=mapped_column(Text,nullable=True)
 peak_frequency:Mapped[float|None]=mapped_column(Double(asdecimal=False),nullable=True)
 max_power:Mapped[float|None]=mapped_column(Double(asdecimal=False),nullable=True)
 global_p:Mapped[float|None]=mapped_column(Double(asdecimal=False),nullable=True)
 created_by:Mapped[str]=mapped_column(String(120))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
