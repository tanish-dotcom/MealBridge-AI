"""Geo routes: forward geocoding search for the map picker and reverse geocoding
for a dropped pin (so the pickup address text can be auto-filled)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.rate_limit import limiter
from app.schemas.geo import GeoReverseResponse, GeoSearchResponse, GeoSuggestion
from app.services import geocoding
from app.services.geocoding import GeocodingError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/search", response_model=GeoSearchResponse)
@limiter.limit("60/minute")
async def geo_search(
    request: Request,
    q: str = Query(min_length=3, max_length=200, description="Free-text place / address query"),
    limit: int = Query(default=5, ge=1, le=10),
):
    """Forward-geocode `q` into a short list of place suggestions (lat/lng + label)."""
    query = q.strip()
    if len(query) < 3:
        return GeoSearchResponse(query=query, results=[])
    try:
        results = await geocoding.search(query, limit=limit)
    except Exception as exc:  # noqa: BLE001 - external provider failure should not 500
        logger.warning("Geocoding search failed for %r: %s", query, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Location search is unavailable right now",
        ) from None
    return GeoSearchResponse(
        query=query,
        results=[
            GeoSuggestion(
                label=r.display_name or f"{r.lat},{r.lng}",
                lat=r.lat,
                lng=r.lng,
                line1=r.line1,
                city=r.city,
                state=r.state,
                postal_code=r.postal_code,
            )
            for r in results
            if r.lat is not None and r.lng is not None
        ],
    )


@router.get("/reverse", response_model=GeoReverseResponse)
@limiter.limit("60/minute")
async def geo_reverse(
    request: Request,
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
):
    """Reverse-geocode a pin into a structured address for form auto-fill."""
    try:
        result = await geocoding.reverse(lat, lng)
    except GeocodingError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not resolve an address for this location",
        ) from None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Reverse geocoding failed for %s,%s: %s", lat, lng, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Reverse geocoding is unavailable right now",
        ) from None
    return GeoReverseResponse(
        lat=lat,
        lng=lng,
        label=result.display_name,
        line1=result.line1,
        city=result.city,
        state=result.state,
        postal_code=result.postal_code,
        country=result.country,
    )
