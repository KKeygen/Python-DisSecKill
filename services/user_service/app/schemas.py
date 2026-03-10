from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


# ========== 请求模型 ==========

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=6, max_length=128)
    email: EmailStr


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserUpdateRequest(BaseModel):
    email: EmailStr | None = None
    phone: str | None = Field(None, pattern=r"^1[3-9]\d{9}$")


# ========== 响应模型 ==========

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    phone: str | None = None
    is_active: bool
    create_time: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
