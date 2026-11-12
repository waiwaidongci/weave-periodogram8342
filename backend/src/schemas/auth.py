from pydantic import BaseModel,Field
class LoginInput(BaseModel):
 email:str=Field(min_length=3,max_length=120)
 password:str=Field(min_length=1,max_length=120)
