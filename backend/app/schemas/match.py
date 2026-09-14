"""Matching / NGO-side schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MatchRequestStatus


class MatchCandidate(BaseModel):
    match_request_id: uuid.UUID | None = None
    ngo_id: uuid.UUID
    ngo_name: str
    contact_person: str | None = None
    distance_km: float
    match_percent: int
    estimated_pickup_minutes: int
    capacity_headroom_ratio: float
    reliability_score: float
    quality_tags: list[str] = []
    lat: float | None = None
    lng: float | None = None


class MatchResult(BaseModel):
    donation_id: uuid.UUID
    top_match: MatchCandidate
    alternatives: list[MatchCandidate]


class MatchRespondRequest(BaseModel):
    action: str = Field(pattern="^(accept|reject)$")


class MatchRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    donation_id: uuid.UUID
    ngo_id: uuid.UUID
    rank_score: float
    match_percent: int
    distance_km: float
    status: MatchRequestStatus
    offered_at: datetime
    responded_at: datetime | None = None


class NgoStats(BaseModel):
    available_donations: int
    accepted_donations: int
    meals_received: int
    people_served: int


class DirectionsOut(BaseModel):
    distance_km: float
    duration_minutes: int
    polyline: list[dict] = []
    steps: list[str] = []
    provider: str


class AvailableDonationItem(BaseModel):
    donation: dict
    distance_km: float
    time_since_posted_minutes: int
    match_request_id: uuid.UUID
