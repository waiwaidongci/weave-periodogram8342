from pydantic import BaseModel,Field
from typing import Literal
class NoteInput(BaseModel):
 run_id:int=Field(gt=0,strict=True)
 name:str=Field(min_length=2,max_length=180)
 interpretation:str=Field(min_length=5,max_length=4000)
 next_step:str=Field(min_length=5,max_length=4000)
class ApprovalInput(BaseModel):
 status:Literal['approved','rejected']
 review_note:str=Field(min_length=2,max_length=2000)
