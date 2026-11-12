from pydantic import BaseModel,Field
class RunInput(BaseModel):
 study_id:int=Field(gt=0,strict=True)
 plan_id:int=Field(gt=0,strict=True)
 name:str=Field(min_length=2,max_length=180)
