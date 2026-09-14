"""Analytics: donor/NGO stat cards, admin dashboard, and impact report.

All food-quantity conversions use a consistent CASE expression so meal-equivalents
and food weight are computed identically everywhere.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import bindparam, case, extract, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Donation, DonorProfile, MatchRequest, NGOProfile, User
from app.models.enums import DonationStatus
from app.schemas.admin import (
    AdminDashboardOverview,
    AdminOverviewStats,
    GoalProgress,
    ImpactReport,
    ImpactStats,
    RecentActivityItem,
    SeriesPoint,
    TopContributor,
)
from app.schemas.donation import DonationStats
from app.schemas.match import NgoStats

MEALS_SQL = (
    "CASE WHEN d.quantity_unit = 'kg' THEN d.quantity_value / :avg_meal "
    "WHEN d.quantity_unit = 'packets' THEN d.quantity_value ELSE d.quantity_value END"
)
WEIGHT_SQL = (
    "CASE WHEN d.quantity_unit = 'kg' THEN d.quantity_value "
    "ELSE d.quantity_value * :avg_meal END"
)
ACTIVE_STATUSES = ("pending_match", "awaiting_response", "matched", "picked_up")


async def _meals_sum(session: AsyncSession, statuses: tuple[str, ...]) -> float:
    row = (
        await session.execute(
            text(
                f"SELECT COALESCE(SUM({MEALS_SQL}), 0) AS m FROM donations d "
                f"WHERE d.status IN :statuses"
            ).bindparams(bindparam("statuses", expanding=True)),
            {"avg_meal": settings.avg_meal_weight_kg, "statuses": statuses},
        )
    ).one()
    return float(row.m)


async def donor_stats(session: AsyncSession, donor_user_id: str) -> DonationStats:
    from sqlalchemy import func, select

    uid = uuid.UUID(donor_user_id)
    active = (
        await session.execute(
            select(func.count(Donation.id)).where(
                Donation.donor_id == uid, Donation.status.in_(ACTIVE_STATUSES)
            )
        )
    ).scalar_one()
    completed = (
        await session.execute(
            select(func.count(Donation.id)).where(
                Donation.donor_id == uid, Donation.status == DonationStatus.completed.value
            )
        )
    ).scalar_one()
    meals = await _meals_sum(session, (DonationStatus.completed.value,))
    # meals from this donor only
    donor_meals = (
        await session.execute(
            text(
                f"SELECT COALESCE(SUM({MEALS_SQL}),0) FROM donations d "
                "WHERE d.donor_id = :uid AND d.status = 'completed'"
            ),
            {"avg_meal": settings.avg_meal_weight_kg, "uid": uid.hex},
        )
    ).scalar_one()
    meals = float(donor_meals or 0)
    return DonationStats(
        active_donations=active,
        completed_donations=completed,
        meals_donated=round(meals),
        people_helped=round(meals * settings.people_per_meal),
    )


async def ngo_stats(session: AsyncSession, ngo_profile_id: str) -> NgoStats:
    from sqlalchemy import func, select

    uid = uuid.UUID(ngo_profile_id)
    available = (
        await session.execute(
            select(func.count(MatchRequest.id)).where(
                MatchRequest.ngo_id == uid,
                MatchRequest.status == "offered",
            )
        )
    ).scalar_one()
    accepted = (
        await session.execute(
            select(func.count(MatchRequest.id)).where(
                MatchRequest.ngo_id == uid,
                MatchRequest.status == "accepted",
            )
        )
    ).scalar_one()
    received_meals = (
        await session.execute(
            text(
                f"SELECT COALESCE(SUM({MEALS_SQL}),0) FROM donations d "
                "WHERE d.matched_ngo_id = :ngo_id AND d.status = 'completed'"
            ),
            {"avg_meal": settings.avg_meal_weight_kg, "ngo_id": uid.hex},
        )
    ).scalar_one()
    meals = float(received_meals or 0)
    return NgoStats(
        available_donations=available,
        accepted_donations=accepted,
        meals_received=round(meals),
        people_served=round(meals * settings.people_per_meal),
    )


async def admin_overview(session: AsyncSession) -> AdminDashboardOverview:
    from sqlalchemy import func, select

    total_restaurants = (
        await session.execute(select(func.count(DonorProfile.id)))
    ).scalar_one()
    verified_ngos = (
        await session.execute(
            select(func.count(NGOProfile.id)).where(NGOProfile.verification_status == "verified")
        )
    ).scalar_one()
    pending_ngos = (
        await session.execute(
            select(func.count(NGOProfile.id)).where(NGOProfile.verification_status == "pending")
        )
    ).scalar_one()
    total_donations = (
        await session.execute(select(func.count(Donation.id)))
    ).scalar_one()
    meals_redistributed = await _meals_sum(session, (DonationStatus.completed.value,))

    # Donation volume over last 6 months (count per month, oldest first)
    since = (datetime.now(timezone.utc) - timedelta(days=180)).replace(day=1)
    rows = (
        await session.execute(
            select(
                extract("year", Donation.created_at).label("y"),
                extract("month", Donation.created_at).label("m"),
                func.count(Donation.id).label("c"),
            )
            .where(Donation.created_at >= since)
            .group_by("y", "m")
            .order_by("y", "m")
        )
    ).all()
    volume_map = {f"{int(r.y):04d}-{int(r.m):02d}": int(r.c) for r in rows}
    volume: list[SeriesPoint] = []
    cursor = since
    while cursor <= datetime.now(timezone.utc):
        key = cursor.strftime("%Y-%m")
        volume.append(SeriesPoint(label=key, value=volume_map.get(key, 0)))
        cursor = (cursor.replace(day=28) + timedelta(days=7)).replace(day=1)

    # Food categories breakdown
    cats = (
        await session.execute(
            text(
                "SELECT food_category AS c, count(*) AS n FROM donations GROUP BY food_category ORDER BY n DESC"
            )
        )
    ).all()
    food_categories = [SeriesPoint(label=r.c, value=r.n) for r in cats]

    # Recent activity: last pending verifications + recent donations
    activity: list[RecentActivityItem] = []
    pending_ngos_rows = (
        await session.execute(
            text(
                "SELECT n.id, u.email, n.org_name, n.verification_status, n.created_at "
                "FROM ngo_profiles n JOIN users u ON u.id = n.user_id "
                "WHERE n.verification_status = 'pending' ORDER BY n.created_at DESC LIMIT 8"
            )
        )
    ).all()
    for r in pending_ngos_rows:
        activity.append(
            RecentActivityItem(
                id=r.id,
                type="ngo_verification",
                actor=r.org_name,
                subject="NGO verification request",
                status=r.verification_status,
                created_at=r.created_at,
            )
        )
    recent_donations = (
        await session.execute(
            text(
                "SELECT d.id, d.food_name, d.status, d.created_at, u.email AS donor_email, d.donor_id "
                "FROM donations d JOIN users u ON u.id = d.donor_id "
                "ORDER BY d.created_at DESC LIMIT 10"
            )
        )
    ).all()
    for r in recent_donations:
        activity.append(
            RecentActivityItem(
                id=r.id,
                type="donation",
                actor=r.donor_email,
                subject=r.food_name,
                status=r.status,
                created_at=r.created_at,
            )
        )
    activity.sort(key=lambda a: a.created_at, reverse=True)

    return AdminDashboardOverview(
        stats=AdminOverviewStats(
            total_restaurants=total_restaurants,
            verified_ngos=verified_ngos,
            pending_ngos=pending_ngos,
            total_donations=total_donations,
            meals_redistributed=round(meals_redistributed),
        ),
        donation_volume=volume,
        food_categories=food_categories,
        recent_activity=activity[:15],
    )


async def impact_report(session: AsyncSession, months: int = 12) -> ImpactReport:
    completed = (DonationStatus.completed.value,)
    meals = await _meals_sum(session, completed)
    food_kg_row = (
        await session.execute(
            text(
                f"SELECT COALESCE(SUM({WEIGHT_SQL}), 0) AS w FROM donations d "
                "WHERE d.status = 'completed'"
            ),
            {"avg_meal": settings.avg_meal_weight_kg},
        )
    ).scalar_one()
    food_kg = float(food_kg_row or 0)
    people_served = meals * settings.people_per_meal
    co2 = food_kg * settings.co2_factor_kg_per_kg

    # Monthly redistribution (sum of meals per month), last N months
    since = (datetime.now(timezone.utc) - timedelta(days=31 * months)).replace(day=1)
    meals_expr = case(
        (Donation.quantity_unit == "kg", Donation.quantity_value / settings.avg_meal_weight_kg),
        else_=Donation.quantity_value,
    )
    rows = (
        await session.execute(
            select(
                extract("year", Donation.created_at).label("y"),
                extract("month", Donation.created_at).label("m"),
                func.sum(meals_expr).label("s"),
            )
            .where(
                Donation.status == DonationStatus.completed.value,
                Donation.created_at >= since,
            )
            .group_by("y", "m")
            .order_by("y", "m")
        )
    ).all()
    month_map = {f"{int(r.y):04d}-{int(r.m):02d}": float(r.s or 0) for r in rows}
    monthly: list[SeriesPoint] = []
    cursor = since
    while cursor <= datetime.now(timezone.utc):
        key = cursor.strftime("%Y-%m")
        monthly.append(SeriesPoint(label=key, value=month_map.get(key, 0)))
        cursor = (cursor.replace(day=28) + timedelta(days=7)).replace(day=1)

    # Food categories % share of completed meals
    cats = (
        await session.execute(
            text(
                f"SELECT d.food_category AS c, SUM({MEALS_SQL}) AS s FROM donations d "
                "WHERE d.status = 'completed' GROUP BY c ORDER BY s DESC"
            ),
            {"avg_meal": settings.avg_meal_weight_kg},
        )
    ).all()
    total_cat = sum(float(r.s or 0) for r in cats) or 1.0
    food_categories = [
        SeriesPoint(label=r.c, value=round(float(r.s or 0) / total_cat * 100, 1)) for r in cats
    ]

    # Top contributors
    contributors = (
        await session.execute(
            text(
                f"SELECT u.email AS name, d.donor_id, SUM({MEALS_SQL}) AS meals, SUM({WEIGHT_SQL}) AS kg "
                "FROM donations d JOIN users u ON u.id = d.donor_id "
                "WHERE d.status = 'completed' GROUP BY u.email, d.donor_id "
                "ORDER BY meals DESC LIMIT 5"
            ),
            {"avg_meal": settings.avg_meal_weight_kg},
        )
    ).all()
    top_contributors = [
        TopContributor(name=r.name, meals=round(float(r.meals or 0)), food_kg=round(float(r.kg or 0), 1))
        for r in contributors
    ]

    # Goals (configurable targets; demo values)
    month_start = datetime.now(timezone.utc).replace(day=1)
    this_month_meals = (
        await session.execute(
            text(
                f"SELECT COALESCE(SUM({MEALS_SQL}), 0) FROM donations d "
                "WHERE d.status = 'completed' AND d.created_at >= :since"
            ),
            {"avg_meal": settings.avg_meal_weight_kg, "since": month_start},
        )
    ).scalar_one()
    this_month_verified = (
        await session.execute(
            text(
                "SELECT count(*) FROM ngo_profiles WHERE verification_status = 'verified' "
                "AND created_at >= :since"
            ),
            {"since": month_start},
        )
    ).scalar_one()
    goals = [
        _goal("monthly_rescue", "Monthly Rescue Goal", float(this_month_meals or 0), 50000),
        _goal("new_partners", "New Partner Onboarding", float(this_month_verified or 0), 10),
        _goal("people_served", "People Served", float(people_served), 100000),
    ]

    return ImpactReport(
        stats=ImpactStats(
            meals_redistributed=round(meals),
            food_saved_kg=round(food_kg, 1),
            people_served=round(people_served),
            co2_reduced_kg=round(co2, 1),
            co2_is_estimate=True,
        ),
        monthly_redistribution=monthly,
        food_categories=food_categories,
        top_contributors=top_contributors,
        goals=goals,
    )


def _goal(key: str, label: str, current: float, target: float) -> GoalProgress:
    pct = min(100, max(0, round(current / target * 100))) if target else 0
    return GoalProgress(key=key, label=label, current=round(current), target=round(target), percent=pct)
