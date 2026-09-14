"""Admin dashboard / analytics schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class AdminOverviewStats(BaseModel):
    total_restaurants: int
    verified_ngos: int
    pending_ngos: int
    total_donations: int
    meals_redistributed: int


class SeriesPoint(BaseModel):
    label: str
    value: float


class RecentActivityItem(BaseModel):
    id: uuid.UUID
    type: str
    actor: str
    subject: str
    status: str
    created_at: datetime


class AdminDashboardOverview(BaseModel):
    stats: AdminOverviewStats
    donation_volume: list[SeriesPoint]
    food_categories: list[SeriesPoint]
    recent_activity: list[RecentActivityItem]


class ImpactStats(BaseModel):
    meals_redistributed: int
    food_saved_kg: float
    people_served: int
    co2_reduced_kg: float
    co2_is_estimate: bool = True


class TopContributor(BaseModel):
    name: str
    meals: int
    food_kg: float


class GoalProgress(BaseModel):
    key: str
    label: str
    current: float
    target: float
    percent: int


class ImpactReport(BaseModel):
    stats: ImpactStats
    monthly_redistribution: list[SeriesPoint]
    food_categories: list[SeriesPoint]
    top_contributors: list[TopContributor]
    goals: list[GoalProgress]
