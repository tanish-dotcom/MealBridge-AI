"""Donation request/response schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import DonationStatus, FoodCategory, QuantityUnit
from app.schemas.user import AddressOut


class DonationCreate(BaseModel):
    food_name: str = Field(min_length=2, max_length=255)
    food_category: FoodCategory
    quantity_value: float = Field(gt=0, le=1_000_000)
    quantity_unit: QuantityUnit = QuantityUnit.meals
    preparation_time: datetime | None = None
    best_before: datetime | None = None
    notes: str | None = Field(default=None, max_length=2000)
    address: str = Field(min_length=5, max_length=500)
    city: str = Field(min_length=1, max_length=120)

    @field_validator("best_before")
    @classmethod
    def best_before_not_past(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            raise ValueError("best_before must be timezone-aware")
        return v


class DonationUpdate(BaseModel):
    food_name: str | None = None
    food_category: FoodCategory | None = None
    quantity_value: float | None = Field(default=None, gt=0)
    quantity_unit: QuantityUnit | None = None
    best_before: datetime | None = None
    notes: str | None = None


class DonationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    donor_id: uuid.UUID
    food_name: str
    food_category: FoodCategory
    quantity_value: float
    quantity_unit: QuantityUnit
    preparation_time: datetime | None = None
    best_before: datetime | None = None
    notes: str | None = None
    status: DonationStatus
    pickup_lat: float | None = None
    pickup_lng: float | None = None
    matched_ngo_id: uuid.UUID | None = None
    completed_by_donor: bool
    completed_by_ngo: bool
    created_at: datetime
    updated_at: datetime
    address: AddressOut | None = None
    photos: list["DonationPhotoOut"] = []
    donor_name: str | None = None
    donor_type: str | None = None


class DonationPhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str


class DonationStats(BaseModel):
    active_donations: int
    completed_donations: int
    meals_donated: int
    people_helped: int


DonationOut.model_rebuild()
