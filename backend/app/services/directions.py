"""Directions between two points: OSRM when available, straight-line fallback."""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.services.geo import midpoint_km
from app.schemas.match import DirectionsOut

logger = logging.getLogger(__name__)

MIN_INTERPOLATE_STEPS = 3

# Public OSRM instances cap the number of coordinates per table request.
OSRM_TABLE_MAX_COORDS = 99


def _osrm_base_url() -> str:
    """OSRM root URL (without the `/route/v1` suffix) so we can build `/table/v1`."""
    base = settings.osrm_url.rstrip("/")
    suffix = "/route/v1"
    if base.endswith(suffix):
        return base[: -len(suffix)]
    return base


async def driving_distances(
    origin: tuple[float, float],
    destinations: list[tuple[float, float]],
) -> list[float | None]:
    """Road distances in km from `origin` to each destination in one OSRM table
    request. Returns `None` for any pair OSRM cannot resolve (or when a non-OSRM
    provider is configured) so the caller can fall back to straight-line."""
    if not destinations:
        return []
    if settings.directions_provider != "osrm":
        return [None] * len(destinations)

    capped = destinations[:OSRM_TABLE_MAX_COORDS]
    coords = ";".join(
        [f"{origin[1]},{origin[0]}"] + [f"{lng},{lat}" for lat, lng in capped]
    )
    url = f"{_osrm_base_url()}/table/v1/driving/{coords}?sources=0&annotations=distance"

    distances: list[float | None] = [None] * len(destinations)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        if data.get("code") != "Ok" or not data.get("distances"):
            return distances
        row = data["distances"][0]
        for i, meters in enumerate(row[1 : len(capped) + 1]):
            if meters is not None:
                distances[i] = round(meters / 1000.0, 3)
    except Exception as exc:  # noqa: BLE001 - fall back to straight-line
        logger.warning("OSRM table request failed (%s); using straight-line distances", exc)
    return distances


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
