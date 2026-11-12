from pydantic import BaseModel,Field,ConfigDict
class PointInput(BaseModel):
 model_config=ConfigDict(allow_inf_nan=False,str_strip_whitespace=True)
 reference:str=Field(min_length=1,max_length=80)
 position:float=Field(ge=0,le=1e12,strict=True)
 thickness:float=Field(ge=0,le=1000000,strict=True)
class PointPatch(BaseModel):
 model_config=ConfigDict(allow_inf_nan=False)
 position:float=Field(ge=0,le=1e12,strict=True)
 thickness:float=Field(ge=0,le=1000000,strict=True)
