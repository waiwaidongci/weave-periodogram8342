from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import ForeignKey,String,JSON,Text,DateTime
from datetime import datetime,timezone
from src.config.database import Base
class WeaveNote(Base):
 __tablename__='weave_notes'
 id:Mapped[int]=mapped_column(primary_key=True)
 run_id:Mapped[int]=mapped_column(ForeignKey('spectrum_runs.id'))
 name:Mapped[str]=mapped_column(String(180),unique=True)
 interpretation:Mapped[str]=mapped_column(Text)
 next_step:Mapped[str]=mapped_column(Text)
 result_snapshot:Mapped[dict]=mapped_column(JSON)
 status:Mapped[str]=mapped_column(String(24),default='draft')
 review_note:Mapped[str]=mapped_column(Text,default='')
 created_by:Mapped[str]=mapped_column(String(120))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
