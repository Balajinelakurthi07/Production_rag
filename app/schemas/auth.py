import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ==========================================
# User Registration & Login Schemas
# ==========================================

class UserCreate(BaseModel):
    """Schema for registering a new user."""
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Password must be between 8 and 72 characters long"
    )
    full_name: Optional[str] = Field(default=None, max_length=255)


class UserLogin(BaseModel):
    """Schema for user login credentials."""
    email: EmailStr
    password: str = Field(..., max_length=72)


# ==========================================
# Token Schemas
# ==========================================

class Token(BaseModel):
    """Returned upon successful login."""
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Data stored and verified inside the JWT."""
    sub: str  # User ID (UUID as string)
    exp: Optional[int] = None


# ==========================================
# User & Department Output Schemas
# ==========================================

class DepartmentOut(BaseModel):
    """Department info representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None


class UserResponse(BaseModel):
    """Safe user profile representation (never exposes password)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime


class UserWithDepartments(UserResponse):
    """User profile along with their accessible departments."""
    departments: List[DepartmentOut] = []
