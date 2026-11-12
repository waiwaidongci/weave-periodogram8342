from pydantic import BaseModel,Field,ConfigDict
class PlanInput(BaseModel):
 model_config=ConfigDict(allow_inf_nan=False,str_strip_whitespace=True)
 study_id:int=Field(gt=0,strict=True)
 name:str=Field(min_length=2,max_length=180)
 protocol:str=Field(min_length=5,max_length=3000)
 min_frequency:float=Field(gt=0,le=1,strict=True)
 max_frequency:float=Field(gt=0,le=1,strict=True)
 grid_size:int=Field(ge=3,le=401,strict=True)
 permutations:int=Field(ge=199,le=499,strict=True)
 seed:int=Field(ge=0,le=1000000000,strict=True)
