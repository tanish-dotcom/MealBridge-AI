"""Auth request/response schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import TokenPair


class DonorSignupRequest(BaseModel):
    restaurant_name: str = Field(min_length=2, max_length=255)
    owner_name: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=32)
    address: str = Field(min_length=5, max_length=500)
    city: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("password must contain at least one letter and one number")
        return v


class NgoSignupRequest(BaseModel):
    org_name: str = Field(min_length=2, max_length=255)
    registration_number: str = Field(min_length=3, max_length=255)
    contact_person: str = Field(min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=32)
    address: str = Field(min_length=5, max_length=500)
    city: str = Field(min_length=1, max_length=120)
    food_requirements: list[str] = Field(default_factory=list)
    capacity_meals_per_day: int | None = Field(default=None, ge=1, le=1000000)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("password must contain at least one letter and one number")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    remember_me: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class RefreshTokenInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    jti: str
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


class AuthResponse(BaseModel):
    token_pair: TokenPair
    user_id: uuid.UUID
    email: str
    role: str
    profile_status: str | None = None
