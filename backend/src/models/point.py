from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import ForeignKey,String,Double,UniqueConstraint
from src.config.database import Base
class TraversePoint(Base):
 __tablename__='traverse_points'
 __table_args__=(UniqueConstraint('study_id','reference'),UniqueConstraint('study_id','position'))
 id:Mapped[int]=mapped_column(primary_key=True)
 study_id:Mapped[int]=mapped_column(ForeignKey('traverse_studies.id'))
 reference:Mapped[str]=mapped_column(String(80))
 position:Mapped[float]=mapped_column(Double(asdecimal=False))
 thickness:Mapped[float]=mapped_column(Double(asdecimal=False))
