"""User models for authentication and database storage."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    """Schema for user registration."""
    name: str = Field(..., min_length=1)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserInDB(BaseModel):
    """Schema for user stored in database."""
    id: str
    name: str
    email: str
    password_hash: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """Schema for user response (without sensitive data)."""
    id: str
    name: str
    email: str
    created_at: datetime


class Token(BaseModel):
    """Schema for JWT token response."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for decoded token data."""
    user_id: Optional[str] = None
    email: Optional[str] = None
