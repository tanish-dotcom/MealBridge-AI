"""NGO-facing routes: available feed, accept/reject, accepted list, stats."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, get_ngo_profile
from app.models import Donation, MatchRequest, NGOProfile, User
from app.models.enums import DonationStatus, MatchRequestStatus, NotificationType, Role, VerificationStatus
from app.schemas.match import MatchRespondRequest, NgoStats
from app.services import audit, matching, notifications
from app.services.geo import haversine_km

router = APIRouter(prefix="/ngo", tags=["ngo"])


def _verified_required(profile: NGOProfile) -> None:
    if profile.verification_status != VerificationStatus.verified.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your NGO must be verified before you can view or accept donations",
        )


@router.get("/dashboard/stats", response_model=NgoStats)
async def ngo_dashboard_stats(
    profile: NGOProfile = Depends(get_ngo_profile), db: AsyncSession = Depends(get_db)
):
    from app.services.analytics import ngo_stats

    return await ngo_stats(db, str(profile.id))


@router.get("/available-donations")
async def available_donations(
    profile: NGOProfile = Depends(get_ngo_profile), db: AsyncSession = Depends(get_db)
):
    _verified_required(profile)
    rows = (
        await db.execute(
            select(MatchRequest)
            .where(MatchRequest.ngo_id == profile.id, MatchRequest.status == MatchRequestStatus.offered.value)
            .order_by(MatchRequest.offered_at.desc())
        )
    ).scalars().all()

    items = []
    for mr in rows:
        donation = await db.get(Donation, mr.donation_id)
        if donation is None or donation.status != DonationStatus.awaiting_response.value:
            continue
        donor = await db.get(User, donation.donor_id)
        distance_km = mr.distance_km
        if donation.pickup_lat is not None and profile.address and profile.address.lat is not None:
            distance_km = haversine_km(
                donation.pickup_lat, donation.pickup_lng, profile.address.lat, profile.address.lng
            )
        minutes = int((datetime.now(timezone.utc) - donation.created_at).total_seconds() / 60)
        items.append(
            {
                "match_request_id": str(mr.id),
                "donation_id": str(donation.id),
                "food_name": donation.food_name,
                "food_category": donation.food_category,
                "quantity_value": float(donation.quantity_value),
                "quantity_unit": donation.quantity_unit,
                "quantity_in_meals": donation.quantity_in_meals,
                "donor_name": donor.display_name() if donor else None,
                "distance_km": round(distance_km, 2),
                "time_since_posted_minutes": max(0, minutes),
                "match_percent": mr.match_percent,
                "notes": donation.notes,
                "created_at": donation.created_at.isoformat(),
            }
        )
    return items


@router.get("/accepted-donations")
async def accepted_donations(
    profile: NGOProfile = Depends(get_ngo_profile), db: AsyncSession = Depends(get_db)
):
    _verified_required(profile)
    rows = (
        await db.execute(
            select(Donation)
            .where(Donation.matched_ngo_id == profile.id)
            .order_by(Donation.updated_at.desc())
            .limit(100)
        )
    ).scalars().all()
    items = []
    for d in rows:
        donor = await db.get(User, d.donor_id)
        items.append(
            {
                "donation_id": str(d.id),
                "food_name": d.food_name,
                "food_category": d.food_category,
                "quantity_value": float(d.quantity_value),
                "quantity_unit": d.quantity_unit,
                "status": d.status,
                "donor_name": donor.display_name() if donor else None,
                "best_before": d.best_before.isoformat() if d.best_before else None,
                "created_at": d.created_at.isoformat(),
                "completed_by_donor": d.completed_by_donor,
                "completed_by_ngo": d.completed_by_ngo,
            }
        )
    return items


@router.post("/matches/{match_request_id}/respond")
async def respond_to_match(
    match_request_id: uuid.UUID,
    payload: MatchRespondRequest,
    request: Request,
    profile: NGOProfile = Depends(get_ngo_profile),
    db: AsyncSession = Depends(get_db),
):
    _verified_required(profile)
    mr = await db.get(MatchRequest, match_request_id)
    if mr is None or mr.ngo_id != profile.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match request not found")
    if mr.status != MatchRequestStatus.offered.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Match request is no longer active")

    donation = await db.get(Donation, mr.donation_id)
    if donation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
    if donation.status not in (DonationStatus.awaiting_response.value, DonationStatus.matched.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Donation is not awaiting a response")
    from app.models import Address

    if donation.address_id:
        donation.address = await db.get(Address, donation.address_id)

    donor = await db.get(User, donation.donor_id)
    now = datetime.now(timezone.utc)
    mr.responded_at = now

    if payload.action == "accept":
        mr.status = MatchRequestStatus.accepted.value
        donation.status = DonationStatus.matched.value
        donation.matched_ngo_id = profile.id
        # Expire all other offered requests for this donation.
        await db.execute(
            update(MatchRequest)
            .where(
                MatchRequest.donation_id == donation.id,
                MatchRequest.id != mr.id,
                MatchRequest.status == MatchRequestStatus.offered.value,
            )
            .values(status=MatchRequestStatus.expired.value, responded_at=now)
        )
        if donor:
            await notifications.notify(
                db,
                donor,
                NotificationType.request_accepted,
                "Donation request accepted",
                f"{profile.org_name} accepted your donation of {donation.food_name}. "
                f"Pickup at: {donation.address.line1 if donation.address else 'the pickup address'}.",
                payload={"donation_id": str(donation.id), "ngo_id": str(profile.id)},
            )
        await audit.log_audit(
            db, "match.accept", actor_user_id=str(profile.user_id), target_type="donation",
            target_id=str(donation.id), ip_address=request.client.host if request.client else None,
        )
        await db.commit()
        return {"message": "Donation accepted", "donation_id": str(donation.id), "status": donation.status}

    # reject
    mr.status = MatchRequestStatus.rejected.value
    await db.commit()
    await audit.log_audit(
        db, "match.reject", actor_user_id=str(profile.user_id), target_type="donation",
        target_id=str(donation.id), ip_address=request.client.host if request.client else None,
    )
    if donor:
        await notifications.create_notification(
            db, str(donor.id), NotificationType.request_rejected, "Donation request declined",
            f"{profile.org_name} declined your donation of {donation.food_name}.",
            payload={"donation_id": str(donation.id)},
        )
    # Offer to the next-ranked NGO immediately.
    await matching.offer_next(db, donation)
    await db.commit()
    return {"message": "Donation rejected", "donation_id": str(donation.id), "status": donation.status}
