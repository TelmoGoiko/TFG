from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=4)


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime


class LoginResponse(BaseModel):
    user: UserResponse
