
import uuid
from pydantic import BaseModel, Field
from typing import Literal


FoodType = Literal[
    "Cooked",
    "Packaged",
    "Fruits",
    "Vegetables",
]


class DonationFeatures(BaseModel):
    food_quantity: float = Field(gt=0)
    hours_remaining: float = Field(gt=0)
    food_type: FoodType


class NGOFeatures(BaseModel):
    id: int
    name: str
    distance_km: float = Field(ge=0)
    ngo_capacity: float = Field(ge=0)
    ngo_demand: float = Field(ge=0)
    acceptance_rate: float = Field(ge=0, le=1)


class MatchRequest(BaseModel):
    donation: DonationFeatures
    ngos: list[NGOFeatures] = Field(max_length=500)


class NGORecommendation(BaseModel):
    ngo_id: int
    ngo_name: str
    match_score: float


class MatchResponse(BaseModel):
    recommendations: list[NGORecommendation]


class TopNgoRecommendation(BaseModel):
    """One ML-ranked NGO suggestion for a live donation (UUID ids from the DB)."""

    ngo_id: uuid.UUID
    ngo_name: str
    match_score: float
    distance_km: float
    capacity_meals_per_day: float | None = None
    ngo_demand: float
    acceptance_rate: float
    reliability_score: float
    estimated_pickup_minutes: int
    reasons: list[str] = []


class TopNgoResponse(BaseModel):
    donation_id: uuid.UUID
    model_name: str
    recommendations: list[TopNgoRecommendation]
