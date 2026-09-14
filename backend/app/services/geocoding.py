"""Address geocoding with provider abstraction (Nominatim default, Google optional)."""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_GEOCODE_ATTEMPTS = 3


@dataclass
class GeocodeResult:
    lat: float | None
    lng: float | None
    display_name: str | None = None
    provider: str = ""


class GeocodingError(Exception):
    pass


async def _geocode_nominatim(query: str) -> GeocodeResult | None:
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 0,
        "countrycodes": "in",
    }
    headers = {"User-Agent": "MealBridgeAI/1.0 (food-donation-platform; contact: admin@mealbridge.ai)"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get("https://nominatim.openstreetmap.org/search", params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        entry = data[0]
        return GeocodeResult(
            lat=float(entry["lat"]),
            lng=float(entry["lon"]),
            display_name=entry.get("display_name"),
            provider="nominatim",
        )


async def _geocode_google(query: str) -> GeocodeResult | None:
    if not settings.google_maps_api_key:
        return None
    params = {"address": query, "key": settings.google_maps_api_key, "region": "in"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get("https://maps.googleapis.com/maps/api/geocode/json", params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK" or not data.get("results"):
            return None
        loc = data["results"][0]["geometry"]["location"]
        return GeocodeResult(
            lat=float(loc["lat"]),
            lng=float(loc["lng"]),
            display_name=data["results"][0].get("formatted_address"),
            provider="google",
        )


async def geocode(query: str) -> GeocodeResult:
    """Geocode a free-text address. Tries the configured provider, then falls back."""
    provider = settings.geocoder_provider
    if provider == "google":
        result = await _geocode_google(query)
        if result:
            return result
        result = await _geocode_nominatim(query)
        if result:
            return result
    else:
        result = await _geocode_nominatim(query)
        if result:
            return result
        result = await _geocode_google(query)
        if result:
            return result
    raise GeocodingError(f"Could not geocode address: {query!r}")


async def sync_geography(session: AsyncSession, address_id: str, lat: float, lng: float) -> None:
    """Populate the PostGIS geography column for an address (ST_MakePoint)."""
    if not settings.use_postgis:
        return
    try:
        await session.execute(
            text(
                "UPDATE addresses SET geog = ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography WHERE id = :id"
            ),
            {"lng": lng, "lat": lat, "id": address_id},
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to update geography for address %s: %s", address_id, exc)
