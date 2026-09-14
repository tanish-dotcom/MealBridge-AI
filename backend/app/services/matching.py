"""AI matching engine: candidate selection, ranking, match-percent, and the
offer/accept/reject/expire lifecycle with automatic radius expansion.

Scoring (configurable weights, see .env MATCH_W_*):
    raw = w_dist * distance_score + w_cap * capacity_headroom + w_rel * reliability
    distance_score  = 1 / (1 + distance_km)
    capacity_headroom = available / capacity  (1.0 when capacity unset / unlimited)
    reliability     = ngo.reliability_score normalized to [0, 1] (assumed /5 scale)
    match_percent   = raw / ideal_raw * 100  where ideal_raw = w_dist + w_cap + w_rel
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Address, Donation, MatchRequest, NGOProfile
from app.services.geo import bounding_box, haversine_km

logger = logging.getLogger(__name__)

# Restriction keywords that can appear in an NGO's food_requirements. If any of
# these appear in a donation's food_name/category/notes, the NGO is treated as
# incompatible unless it explicitly allows that tag. Heuristic, documented.
RESTRICTION_KEYWORDS = {
    "no nuts": ("nut", "peanut", "almond", "cashew"),
    "nuts": ("nut", "peanut", "almond", "cashew"),
    "no nuts (any)": ("nut", "peanut", "almond", "cashew"),
    "vegan": ("non-veg", "meat", "chicken", "egg", "fish", "dairy", "milk", "ghee", "paneer"),
    "vegetarian": ("meat", "chicken", "fish", "egg"),
    "no pork": ("pork", "ham", "bacon"),
    "halal": ("pork", "ham", "bacon"),
    "jain": ("non-veg", "meat", "chicken", "fish", "egg", "onion", "garlic", "root vegetable"),
    "gluten-free": ("wheat", "bread", "pasta", "naan", "roti"),
    "no dairy": ("dairy", "milk", "ghee", "paneer", "cheese", "butter"),
    "non-veg": ("vegetarian", "veg", "paneer", "vegetable"),
}


async def _candidates_postgis(
    session: AsyncSession, lat: float, lng: float, radius_km: float
) -> list[tuple[str, float]]:
    """ST_DWithin query over verified NGOs' geography points. Returns (ngo_id, distance_km)."""
    sql = text(
        """
        SELECT n.id AS ngo_id,
               ST_Distance(a.geog, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography) / 1000.0 AS dist_km
        FROM ngo_profiles n
        JOIN addresses a ON a.id = n.address_id
        WHERE n.verification_status = 'verified'
          AND a.geog IS NOT NULL
          AND ST_DWithin(a.geog, ST_SetSRID(ST_MakePoint(:lng, :lat), 4326)::geography, :radius_m)
        ORDER BY dist_km
        """
    )
    result = await session.execute(
        sql, {"lng": lng, "lat": lat, "radius_m": radius_km * 1000.0}
    )
    return [(row.ngo_id, float(row.dist_km)) for row in result]


async def _candidates_haversine(
    session: AsyncSession, lat: float, lng: float, radius_km: float
) -> list[tuple[str, float]]:
    """Bounding-box prefilter + exact Haversine in Python (no-PostGIS fallback)."""
    bbox = bounding_box(lat, lng, radius_km)
    from sqlalchemy.orm import selectinload

    stmt = (
        select(NGOProfile)
        .options(selectinload(NGOProfile.address))
        .join(NGOProfile.address)
        .where(NGOProfile.verification_status == "verified")
        .where(Address.lat >= bbox.min_lat, Address.lat <= bbox.max_lat)
        .where(Address.lng >= bbox.min_lng, Address.lng <= bbox.max_lng)
    )
    ngos = (await session.execute(stmt)).scalars().all()
    out: list[tuple[str, float]] = []
    for ngo in ngos:
        a = ngo.address
        if a and a.lat is not None and a.lng is not None:
            d = haversine_km(lat, lng, a.lat, a.lng)
            if d <= radius_km:
                out.append((str(ngo.id), d))
    out.sort(key=lambda t: t[1])
    return out


async def _load_per_ngo(
    session: AsyncSession, ngo_ids: list[str]
) -> dict[str, float]:
    """Meal-equivalent load of matched-but-not-completed donations per NGO (today)."""
    if not ngo_ids:
        return {}
    avg_meal = settings.avg_meal_weight_kg
    meals_expr = case(
        (Donation.quantity_unit == "meals", Donation.quantity_value),
        (Donation.quantity_unit == "kg", Donation.quantity_value / avg_meal),
        else_=Donation.quantity_value,
    )
    day_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    ids = [i if isinstance(i, uuid.UUID) else uuid.UUID(str(i)) for i in ngo_ids]
    stmt = (
        select(
            Donation.matched_ngo_id.label("ngo_id"),
            func.sum(meals_expr).label("load_meals"),
        )
        .where(
            Donation.matched_ngo_id.in_(ids),
            Donation.status.in_(("matched", "picked_up")),
            Donation.created_at >= day_start,
        )
        .group_by(Donation.matched_ngo_id)
    )
    result = (await session.execute(stmt)).all()
    return {str(row.ngo_id): float(row.load_meals) for row in result}


def _food_compatible(requirements: list[str] | None, donation: Donation) -> bool:
    """Keyword-based food compatibility heuristic between an NGO's declared
    requirements/restrictions and a donation's metadata."""
    if not requirements:
        return True
    donation_text = " ".join(
        filter(None, [donation.food_name, donation.food_category, donation.notes or ""])
    ).lower()
    for requirement in requirements:
        req = requirement.lower().strip()
        for keyword, banned in RESTRICTION_KEYWORDS.items():
            if req == keyword or keyword in req:
                if any(b in donation_text for b in banned):
                    return False
    return True


def _reliability_norm(score: float) -> float:
    if score is None:
        return 0.0
    if score > 1.0:
        return min(score / 5.0, 1.0)
    return max(0.0, min(score, 1.0))


def _rank_candidates(
    candidates: list[tuple[str, float]],
    loads: dict[str, float],
    ngos: dict[str, NGOProfile],
    donation: Donation,
) -> list[tuple[NGOProfile, float, float, float, float]]:
    """Rank (distance_km, capacity_headroom, reliability_norm, raw_score) per NGO."""
    w_d, w_c, w_rel = settings.match_w_distance, settings.match_w_capacity, settings.match_w_reliability
    ranked: list[tuple[NGOProfile, float, float, float, float]] = []
    for ngo_id, dist in candidates:
        ngo = ngos.get(ngo_id)
        if not ngo:
            continue
        if not _food_compatible(ngo.food_requirements, donation):
            continue
        capacity = ngo.capacity_meals_per_day
        if capacity:
            load = loads.get(ngo_id, 0.0)
            headroom = max(0.0, (capacity - load) / capacity)
            if headroom <= 0.0:
                continue
        else:
            headroom = 1.0
        distance_score = 1.0 / (1.0 + dist)
        rel = _reliability_norm(ngo.reliability_score)
        raw = w_d * distance_score + w_c * headroom + w_rel * rel
        ranked.append((ngo, dist, headroom, rel, raw))
    ranked.sort(key=lambda t: t[4], reverse=True)
    return ranked


async def run_matching(
    session: AsyncSession, donation: Donation, exclude_ngo_ids: set[str] | None = None
) -> tuple[list[tuple[NGOProfile, float, float, float, float]], str | None]:
    """Run the candidate query with radius expansion and return ranked NGOs.

    Returns (ranked_list, radius_used). Creates nothing; the caller persists
    MatchRequest rows via create_offers()."""
    if donation.pickup_lat is None or donation.pickup_lng is None:
        logger.warning("Donation %s has no geocoded pickup coords", donation.id)
        return [], None

    lat, lng = donation.pickup_lat, donation.pickup_lng
    radius = settings.match_initial_radius_km
    ranked: list[tuple[NGOProfile, float, float, float, float]] = []
    radius_used = None
    while radius <= settings.match_max_radius_km:
        if settings.use_postgis:
            raw_candidates = await _candidates_postgis(session, lat, lng, radius)
        else:
            raw_candidates = await _candidates_haversine(session, lat, lng, radius)
        if exclude_ngo_ids:
            raw_candidates = [(i, d) for i, d in raw_candidates if i not in exclude_ngo_ids]
        if raw_candidates:
            ngo_ids = [i if isinstance(i, uuid.UUID) else uuid.UUID(str(i)) for i, _ in raw_candidates]
            loads = await _load_per_ngo(session, ngo_ids)
            stmt = select(NGOProfile).where(NGOProfile.id.in_(ngo_ids))
            ngos = {str(n.id): n for n in (await session.execute(stmt)).scalars().all()}
            ranked = _rank_candidates(raw_candidates, loads, ngos, donation)
            radius_used = radius
            if len(ranked) >= settings.match_min_candidates:
                break
        radius += settings.match_radius_step_km
        logger.info("Expanding match radius for donation %s to %skm", donation.id, radius)
    return ranked, radius_used


async def create_offers(
    session: AsyncSession, donation: Donation, ranked: list[tuple[NGOProfile, float, float, float, float]]
) -> list[MatchRequest]:
    """Create 'offered' MatchRequest rows for the top match + alternatives."""
    requests: list[MatchRequest] = []
    if not ranked:
        return requests
    now = datetime.now(timezone.utc)
    top_count = 1 + settings.match_max_alternatives
    for ngo, dist, headroom, rel, raw in ranked[:top_count]:
        percent = max(1, min(100, round(raw * 100)))
        mr = MatchRequest(
            donation_id=donation.id,
            ngo_id=ngo.id,
            rank_score=raw,
            match_percent=percent,
            distance_km=dist,
            status="offered",
            offered_at=now,
        )
        session.add(mr)
        requests.append(mr)
    donation.status = "awaiting_response"
    return requests


def quality_tags(
    dist_km: float, headroom: float, rel: float, eta_minutes: int
) -> list[str]:
    tags: list[str] = []
    if dist_km < 3.0:
        tags.append("Nearby")
    if eta_minutes <= 30:
        tags.append("Fast Pickup")
    if rel >= 0.8:
        tags.append("Great Quality")
    if headroom >= 0.5:
        tags.append("High Capacity")
    return tags


def estimated_pickup_minutes(dist_km: float) -> int:
    speed = max(settings.avg_city_speed_kmh, 1.0)
    return max(1, round(dist_km / speed * 60))


async def offer_next(session: AsyncSession, donation: Donation) -> None:
    """After a rejection/expiry, offer the donation to the next-ranked NGO that has
    not already been offered. Marks donation unmatched when no candidates remain."""
    existing = (
        await session.execute(select(MatchRequest.ngo_id).where(MatchRequest.donation_id == donation.id))
    ).scalars().all()
    exclude = {str(n) for n in existing}
    ranked, _ = await run_matching(session, donation, exclude_ngo_ids=exclude)
    if not ranked:
        if donation.status not in ("matched", "picked_up", "completed", "cancelled", "expired"):
            donation.status = "unmatched"
        return
    await create_offers(session, donation, ranked)


async def expire_stale_requests(session: AsyncSession) -> int:
    """Job: expire 'offered' requests past the response window and re-offer next
    ranked NGOs. Returns number of donations that were re-offered."""
    window = timedelta(minutes=settings.ngo_response_window_minutes)
    cutoff = datetime.now(timezone.utc) - window
    stale = (
        await session.execute(
            select(MatchRequest)
            .where(MatchRequest.status == "offered", MatchRequest.offered_at < cutoff)
            .options()  # avoid extra load
        )
    ).scalars().all()
    reoffered = 0
    seen: set[str] = set()
    for mr in stale:
        if mr.donation_id in seen:
            continue
        seen.add(str(mr.donation_id))
        mr.status = "expired"
        mr.responded_at = datetime.now(timezone.utc)
        donation = (
            await session.execute(select(Donation).where(Donation.id == mr.donation_id))
        ).scalar_one_or_none()
        if donation and donation.status == "awaiting_response":
            await offer_next(session, donation)
            reoffered += 1
    return reoffered
