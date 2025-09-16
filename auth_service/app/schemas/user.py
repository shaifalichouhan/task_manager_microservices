from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    user_type: str | None = "normal"

class UserOut(BaseModel):
    id: int
    email: EmailStr
    user_type: str

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
