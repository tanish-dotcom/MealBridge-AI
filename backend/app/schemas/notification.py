"""Notification and review schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationType


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: NotificationType
    title: str
    body: str | None = None
    payload: dict | None = None
    read_at: datetime | None = None
    created_at: datetime


class NotificationRead(BaseModel):
    notification_id: uuid.UUID


class ReviewCreate(BaseModel):
    donation_id: uuid.UUID
    reviewee_user_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    donation_id: uuid.UUID
    reviewer_user_id: uuid.UUID
    reviewee_user_id: uuid.UUID
    rating: int
    comment: str | None = None
    created_at: datetime
