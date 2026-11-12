from pydantic import BaseModel,Field,ConfigDict
from .point import PointInput
class StudyInput(BaseModel):
 model_config=ConfigDict(str_strip_whitespace=True)
 name:str=Field(min_length=2,max_length=150)
 filename:str=Field(min_length=2,max_length=180)
 description:str=Field(default='',max_length=3000)
 points:list[PointInput]=Field(min_length=4,max_length=240)
