from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import ForeignKey,String,Double,JSON,Text,DateTime
from datetime import datetime,timezone
from src.config.database import Base
class FrequencyPlan(Base):
 __tablename__='frequency_plans'
 id:Mapped[int]=mapped_column(primary_key=True)
 study_id:Mapped[int]=mapped_column(ForeignKey('traverse_studies.id'))
 name:Mapped[str]=mapped_column(String(180),unique=True)
 protocol:Mapped[str]=mapped_column(Text)
 min_frequency:Mapped[float]=mapped_column(Double(asdecimal=False))
 max_frequency:Mapped[float]=mapped_column(Double(asdecimal=False))
 grid_size:Mapped[int]=mapped_column()
 frequencies:Mapped[list]=mapped_column(JSON)
 permutations:Mapped[int]=mapped_column()
 seed:Mapped[int]=mapped_column()
 created_by:Mapped[str]=mapped_column(String(120))
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
