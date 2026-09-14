"""User/profile schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import DonorType, VerificationStatus


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    lat: float | None = None
    lng: float | None = None


class DonorProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    restaurant_name: str
    owner_name: str
    donor_type: DonorType
    is_verified: bool
    address: AddressOut | None = None


class NgoProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    org_name: str
    registration_number: str
    contact_person: str
    verification_status: VerificationStatus
    capacity_meals_per_day: int | None = None
    food_requirements: list[str] = []
    reliability_score: float
    address: AddressOut | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    phone: str | None = None
    role: str
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    preferences: dict = {}
    is_active: bool
    created_at: datetime
    donor_profile: DonorProfileOut | None = None
    ngo_profile: NgoProfileOut | None = None


class UserUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    email: EmailStr | None = None
    avatar_url: str | None = None


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class PreferencesUpdate(BaseModel):
    email_notifications: bool = True
    sms_alerts: bool = False
