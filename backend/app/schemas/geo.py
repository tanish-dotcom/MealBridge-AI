"""Geocoding search / reverse-geocode schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class GeoSuggestion(BaseModel):
    """One forward-geocoding result for the map picker's search box."""

    label: str
    lat: float
    lng: float
    line1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None


class GeoSearchResponse(BaseModel):
    query: str
    results: list[GeoSuggestion] = Field(default_factory=list)


class GeoReverseResponse(BaseModel):
    """Structured address for a dropped map pin."""

    lat: float
    lng: float
    label: str | None = None
    line1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
