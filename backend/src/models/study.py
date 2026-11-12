from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import String,Text
from src.config.database import Base
class TraverseStudy(Base):
 __tablename__='traverse_studies'
 id:Mapped[int]=mapped_column(primary_key=True)
 name:Mapped[str]=mapped_column(String(150),unique=True)
 filename:Mapped[str]=mapped_column(String(180))
 description:Mapped[str]=mapped_column(Text,default='')
