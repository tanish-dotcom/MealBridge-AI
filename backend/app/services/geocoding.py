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
    # Structured components (populated by reverse geocoding so the frontend can
    # auto-fill the address/city fields when a user drops a pin on the map).
    line1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None


class GeocodingError(Exception):
    pass


NOMINATIM_HEADERS = {
    "User-Agent": "MealBridgeAI/1.0 (food-donation-platform; contact: admin@mealbridge.ai)"
}


def _nominatim_address_components(entry: dict) -> dict:
    """Flatten a Nominatim `address` block into our Address-shaped fields."""
    addr = entry.get("address") or {}
    line1 = (
        addr.get("road")
        or addr.get("pedestrian")
        or addr.get("neighbourhood")
        or addr.get("suburb")
        or addr.get("hamlet")
        or addr.get("village")
        or addr.get("amenity")
    )
    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("municipality")
        or addr.get("village")
        or addr.get("state_district")
        or addr.get("county")
    )
    return {
        "line1": line1,
        "city": city,
        "state": addr.get("state"),
        "postal_code": addr.get("postcode"),
        "country": addr.get("country"),
    }


def _google_address_components(entry: dict) -> dict:
    """Flatten Google's address_components list into our Address-shaped fields."""
    wanted = {
        "route": "line1",
        "sublocality": "line1",
        "sublocality_level_1": "line1",
        "neighborhood": "line1",
        "locality": "city",
        "postal_town": "city",
        "administrative_area_level_2": "city",
        "administrative_area_level_1": "state",
        "postal_code": "postal_code",
        "country": "country",
    }
    out: dict = {"line1": None, "city": None, "state": None, "postal_code": None, "country": None}
    for comp in entry.get("address_components", []):
        for ctype in comp.get("types", []):
            field = wanted.get(ctype)
            if field and not out.get(field):
                out[field] = comp.get("long_name")
    return out


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


async def _search_nominatim(query: str, limit: int) -> list[GeocodeResult]:
    params = {
        "q": query,
        "format": "json",
        "limit": limit,
        "addressdetails": 1,
        "countrycodes": "in",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/search",
            params=params,
            headers=NOMINATIM_HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()
    results: list[GeocodeResult] = []
    for entry in data:
        components = _nominatim_address_components(entry)
        results.append(
            GeocodeResult(
                lat=float(entry["lat"]),
                lng=float(entry["lon"]),
                display_name=entry.get("display_name"),
                provider="nominatim",
                **components,
            )
        )
    return results


async def _search_google(query: str, limit: int) -> list[GeocodeResult]:
    if not settings.google_maps_api_key:
        return []
    params = {"address": query, "key": settings.google_maps_api_key, "region": "in"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get("https://maps.googleapis.com/maps/api/geocode/json", params=params)
        resp.raise_for_status()
        data = resp.json()
    if data.get("status") != "OK":
        return []
    results: list[GeocodeResult] = []
    for entry in data.get("results", [])[:limit]:
        loc = entry["geometry"]["location"]
        results.append(
            GeocodeResult(
                lat=float(loc["lat"]),
                lng=float(loc["lng"]),
                display_name=entry.get("formatted_address"),
                provider="google",
                **_google_address_components(entry),
            )
        )
    return results


async def search(query: str, limit: int = 5) -> list[GeocodeResult]:
    """Forward-geocode a free-text query and return several candidates.

    Used by the map picker's search box; honours `geocoder_provider` then falls
    back to the other provider so a missing Google key never blocks search."""
    limit = max(1, min(limit, 10))
    provider = settings.geocoder_provider
    if provider == "google":
        results = await _search_google(query, limit)
        return results or await _search_nominatim(query, limit)
    results = await _search_nominatim(query, limit)
    return results or await _search_google(query, limit)


async def _reverse_nominatim(lat: float, lng: float) -> GeocodeResult | None:
    params = {
        "lat": lat,
        "lon": lng,
        "format": "jsonv2",
        "addressdetails": 1,
        "zoom": 18,
        "countrycodes": "in",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            "https://nominatim.openstreetmap.org/reverse",
            params=params,
            headers=NOMINATIM_HEADERS,
        )
        resp.raise_for_status()
        data = resp.json()
    if not data or data.get("error"):
        return None
    return GeocodeResult(
        lat=lat,
        lng=lng,
        display_name=data.get("display_name"),
        provider="nominatim",
        **_nominatim_address_components(data),
    )


async def _reverse_google(lat: float, lng: float) -> GeocodeResult | None:
    if not settings.google_maps_api_key:
        return None
    params = {"latlng": f"{lat},{lng}", "key": settings.google_maps_api_key, "region": "in"}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get("https://maps.googleapis.com/maps/api/geocode/json", params=params)
        resp.raise_for_status()
        data = resp.json()
    if data.get("status") != "OK" or not data.get("results"):
        return None
    entry = data["results"][0]
    return GeocodeResult(
        lat=lat,
        lng=lng,
        display_name=entry.get("formatted_address"),
        provider="google",
        **_google_address_components(entry),
    )


async def reverse(lat: float, lng: float) -> GeocodeResult:
    """Reverse-geocode a map pin into a readable address (with structured parts)."""
    provider = settings.geocoder_provider
    if provider == "google":
        result = await _reverse_google(lat, lng)
        if result:
            return result
        result = await _reverse_nominatim(lat, lng)
        if result:
            return result
    else:
        result = await _reverse_nominatim(lat, lng)
        if result:
            return result
        result = await _reverse_google(lat, lng)
        if result:
            return result
    raise GeocodingError(f"Could not reverse-geocode coordinates: {lat},{lng}")


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
