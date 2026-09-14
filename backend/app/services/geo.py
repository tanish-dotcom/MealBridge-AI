"""Pure-Python geodesic helpers (Haversine + bounding-box prefilter)."""
from __future__ import annotations

import math
from dataclasses import dataclass

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in km between two (lat, lng) points."""
    if lat1 is None or lng1 is None or lat2 is None or lng2 is None:
        return float("inf")
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass
class BBox:
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float


def bounding_box(lat: float, lng: float, radius_km: float) -> BBox:
    """Axis-aligned bounding box around (lat, lng) for pre-filtering."""
    dlat = math.degrees(radius_km / EARTH_RADIUS_KM)
    # Approximate lng degree spacing shrinks with latitude.
    lng_deg = radius_km / (EARTH_RADIUS_KM * math.cos(math.radians(lat))) if abs(lat) < 89.9 else radius_km
    dlng = math.degrees(lng_deg)
    return BBox(lat - dlat, lat + dlat, lng - dlng, lng + dlng)


def midpoint_km(lat1: float, lng1: float, lat2: float, lng2: float) -> tuple[float, float]:
    """Approximate great-circle midpoint for straight-line route rendering."""
    lat = (math.radians(lat1) + math.radians(lat2)) / 2
    lng = (math.radians(lng1) + math.radians(lng2)) / 2
    return math.degrees(lat), math.degrees(lng)
