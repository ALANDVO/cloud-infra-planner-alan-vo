# backend/app/schemas/auth.py
"""Authentication request/response schemas."""
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class CsrfResponse(BaseModel):
    csrf_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


TokenResponse.model_rebuild()