"""Directions between two points: OSRM when available, straight-line fallback."""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.services.geo import midpoint_km
from app.schemas.match import DirectionsOut

logger = logging.getLogger(__name__)

MIN_INTERPOLATE_STEPS = 3


async def _osrm_route(orig: tuple[float, float], dest: tuple[float, float]) -> DirectionsOut | None:
    if settings.directions_provider != "osrm":
        return None
    url = (
        f"{settings.osrm_url}/driving/{orig[1]},{orig[0]};{dest[1]},{dest[0]}"
        "?overview=full&geometries=geojson&steps=true"
    )
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        if data.get("code") != "Ok" or not data.get("routes"):
            return None
        route = data["routes"][0]
        coords = route.get("geometry", {}).get("coordinates", [])
        steps = []
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                man = step.get("maneuver", {})
                steps.append(
                    f"{man.get('instruction') or step.get('name') or 'Continue'} "
                    f"({round((step.get('distance') or 0) / 1000, 2)} km)"
                )
        distance_km = round(route.get("distance", 0) / 1000.0, 2)
        duration_min = max(1, round(route.get("duration", 0) / 60))
        return DirectionsOut(
            distance_km=distance_km,
            duration_minutes=duration_min,
            polyline=[{"lat": c[1], "lng": c[0]} for c in coords] if coords else [],
            steps=steps,
            provider="osrm",
        )
    except Exception as exc:
        logger.warning("OSRM route failed (%s); using straight-line fallback", exc)
        return None


def _straight_line(orig: tuple[float, float], dest: tuple[float, float]) -> DirectionsOut:
    from app.services.geo import haversine_km

    distance_km = haversine_km(orig[0], orig[1], dest[0], dest[1])
    speed = max(settings.avg_city_speed_kmh, 1.0)
    duration_min = max(1, round(distance_km / speed * 60))
    mid = midpoint_km(orig[0], orig[1], dest[0], dest[1])
    polyline = [
        {"lat": orig[0], "lng": orig[1]},
        {"lat": mid[0], "lng": mid[1]},
        {"lat": dest[0], "lng": dest[1]},
    ]
    return DirectionsOut(
        distance_km=round(distance_km, 2),
        duration_minutes=duration_min,
        polyline=polyline,
        steps=[f"Drive from origin to destination ({round(distance_km, 2)} km)"],
        provider="straight_line",
    )


async def get_directions(
    origin: tuple[float, float], destination: tuple[float, float]
) -> DirectionsOut:
    route = await _osrm_route(origin, destination)
    if route:
        return route
    return _straight_line(origin, destination)
