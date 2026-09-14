"""Donation routes: create (geocode + match), list, detail, cancel, matches,
directions, and two-sided pickup confirmation."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db, get_donation_for_donor, get_donor_profile, get_ngo_profile
from app.core.config import settings
from app.models import Donation, DonationPhoto, MatchRequest, NGOProfile, User
from app.models.enums import DonationStatus, Role
from app.schemas.donation import DonationCreate, DonationOut, DonationStats
from app.schemas.match import DirectionsOut, MatchCandidate, MatchResult
from app.services import audit, directions as directions_service, geocoding, matching, notifications
from app.services.geocoding import GeocodingError
from app.models.enums import NotificationType

router = APIRouter(prefix="/donations", tags=["donations"])


async def _serialize_donation(db: AsyncSession, donation: Donation, actor_user: User) -> dict:
    from app.models import Address

    donor = (
        await db.execute(
            select(User).where(User.id == donation.donor_id).options(selectinload(User.donor_profile))
        )
    ).scalar_one_or_none()
    if donation.address_id:
        donation.address = await db.get(Address, donation.address_id)
    photos = (
        await db.execute(select(DonationPhoto).where(DonationPhoto.donation_id == donation.id))
    ).scalars().all()
    data = DonationOut.model_validate(donation).model_dump(mode="json")
    data["donor_name"] = donor.display_name() if donor else None
    data["donor_email"] = donor.email if donor else None
    data["donor_type"] = donor.donor_profile.donor_type if donor and donor.donor_profile else None
    data["photos"] = [{"id": str(p.id), "url": p.url} for p in photos]
    data["quantity_in_meals"] = donation.quantity_in_meals
    return data


async def _geocode_pickup(db: AsyncSession, address_text: str, city: str) -> tuple[float, float, uuid.UUID | None]:
    from app.models import Address

    address = Address(line1=address_text, city=city, country="India")
    db.add(address)
    await db.flush()
    try:
        geo = await geocoding.geocode(f"{address_text}, {city}, India")
        address.lat, address.lng = geo.lat, geo.lng
    except GeocodingError:
        address.lat, address.lng = None, None
    await db.flush()
    if address.lat is not None and address.lng is not None:
        await geocoding.sync_geography(db, str(address.id), address.lat, address.lng)
    return address.lat, address.lng, address.id


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_donation(
    payload: DonationCreate,
    request: Request,
    donor_profile=Depends(get_donor_profile),
    db: AsyncSession = Depends(get_db),
):
    lat, lng, address_id = await _geocode_pickup(db, payload.address, payload.city)
    donation = Donation(
        donor_id=donor_profile.user_id,
        address_id=address_id,
        food_name=payload.food_name,
        food_category=payload.food_category.value,
        quantity_value=payload.quantity_value,
        quantity_unit=payload.quantity_unit.value,
        preparation_time=payload.preparation_time,
        best_before=payload.best_before,
        notes=payload.notes,
        status=DonationStatus.pending_match.value,
        pickup_lat=lat,
        pickup_lng=lng,
    )
    db.add(donation)
    await db.flush()
    await audit.log_audit(
        db, "donation.create", actor_user_id=str(donor_profile.user_id), target_type="donation",
        target_id=str(donation.id), ip_address=request.client.host if request.client else None,
    )
    await notifications.create_notification(
        db,
        str(donor_profile.user_id),
        NotificationType.donation_posted,
        "Donation posted",
        f"{payload.food_name} ({payload.quantity_value} {payload.quantity_unit.value}) is now live.",
        payload={"donation_id": str(donation.id)},
    )
    await db.flush()

    ranked, _ = await matching.run_matching(db, donation)
    await matching.create_offers(db, donation, ranked)
    await db.commit()
    return {"donation_id": str(donation.id), "status": donation.status}


@router.get("/mine", response_model=DonationStats)
async def my_stats(donor_profile=Depends(get_donor_profile), db: AsyncSession = Depends(get_db)):
    from app.services.analytics import donor_stats

    return await donor_stats(db, str(donor_profile.user_id))


@router.get("/mine/list")
async def my_donations(donor_profile=Depends(get_donor_profile), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Donation)
            .where(Donation.donor_id == donor_profile.user_id)
            .order_by(Donation.created_at.desc())
            .limit(100)
        )
    ).scalars().all()
    donor = await db.get(User, donor_profile.user_id)
    return [await _serialize_donation(db, d, donor) for d in rows]


@router.get("/{donation_id}", response_model=dict)
async def get_donation(
    donation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    donation = await db.get(Donation, donation_id)
    if donation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
    if user.role == Role.donor.value and donation.donor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your donation")
    if user.role == Role.ngo.value:
        ngo = (
            await db.execute(select(NGOProfile).where(NGOProfile.user_id == user.id))
        ).scalar_one_or_none()
        if ngo is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NGO profile required")
        has_request = (
            await db.execute(
                select(MatchRequest.id).where(
                    MatchRequest.donation_id == donation.id, MatchRequest.ngo_id == ngo.id
                )
            )
        ).first()
        if not has_request:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this donation")
    return await _serialize_donation(db, donation, user)


@router.patch("/{donation_id}/cancel")
async def cancel_donation(
    donation_id: uuid.UUID,
    donation: Donation = Depends(get_donation_for_donor),
    db: AsyncSession = Depends(get_db),
):
    if donation.status not in (DonationStatus.pending_match.value, DonationStatus.awaiting_response.value, DonationStatus.unmatched.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Donation cannot be cancelled in current state")
    donation.status = DonationStatus.cancelled.value
    from app.models import MatchRequest

    await db.execute(
        MatchRequest.__table__.update()
        .where(MatchRequest.donation_id == donation.id, MatchRequest.status == "offered")
        .values(status="expired")
    )
    await audit.log_audit(db, "donation.cancel", actor_user_id=str(donation.donor_id), target_type="donation", target_id=str(donation.id))
    await db.commit()
    return {"message": "Donation cancelled"}


@router.get("/{donation_id}/matches", response_model=MatchResult)
async def donation_matches(
    donation_id: uuid.UUID,
    donation: Donation = Depends(get_donation_for_donor),
    db: AsyncSession = Depends(get_db),
):
    requests = (
        await db.execute(
            select(MatchRequest)
            .where(MatchRequest.donation_id == donation.id)
            .order_by(MatchRequest.match_percent.desc())
        )
    ).scalars().all()
    if not requests and donation.status in ("pending_match", "unmatched", "awaiting_response"):
        ranked, _ = await matching.run_matching(db, donation)
        await matching.create_offers(db, donation, ranked)
        await db.commit()
        requests = (
            await db.execute(
                select(MatchRequest)
                .where(MatchRequest.donation_id == donation.id)
                .order_by(MatchRequest.match_percent.desc())
            )
        ).scalars().all()

    active = [r for r in requests if r.status in ("offered", "accepted")]
    if not active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active matches for this donation")

    candidates: list[MatchCandidate] = []
    if active:
        loads = await matching._load_per_ngo(db, [str(r.ngo_id) for r in active])
    for mr in active:
        from app.models import Address

        ngo = await db.get(NGOProfile, mr.ngo_id)
        if ngo is None:
            continue
        if ngo.address_id:
            ngo.address = await db.get(Address, ngo.address_id)
        eta = matching.estimated_pickup_minutes(mr.distance_km)
        if ngo.capacity_meals_per_day:
            headroom = max(0.0, (ngo.capacity_meals_per_day - loads.get(str(ngo.id), 0.0)) / ngo.capacity_meals_per_day)
        else:
            headroom = 1.0
        candidates.append(
            MatchCandidate(
                match_request_id=mr.id,
                ngo_id=ngo.id,
                ngo_name=ngo.org_name,
                contact_person=ngo.contact_person,
                distance_km=round(mr.distance_km, 2),
                match_percent=mr.match_percent,
                estimated_pickup_minutes=eta,
                capacity_headroom_ratio=round(headroom, 2),
                reliability_score=ngo.reliability_score,
                quality_tags=matching.quality_tags(mr.distance_km, headroom, ngo.reliability_score, eta),
                lat=ngo.address.lat if ngo.address else None,
                lng=ngo.address.lng if ngo.address else None,
            )
        )
    if not candidates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No candidate NGOs found")

    candidates.sort(key=lambda c: c.match_percent, reverse=True)
    return MatchResult(donation_id=donation.id, top_match=candidates[0], alternatives=candidates[1:])


@router.get("/{donation_id}/directions", response_model=DirectionsOut)
async def donation_directions(
    donation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    donation = await db.get(Donation, donation_id)
    if donation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    ngo: NGOProfile | None = None
    if user.role == Role.donor.value:
        if donation.donor_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your donation")
        if donation.matched_ngo_id:
            from app.models import Address

            ngo = await db.get(NGOProfile, donation.matched_ngo_id)
            if ngo and ngo.address_id:
                ngo.address = await db.get(Address, ngo.address_id)
    elif user.role == Role.ngo.value:
        profile = (
            await db.execute(select(NGOProfile).where(NGOProfile.user_id == user.id))
        ).scalar_one_or_none()
        if profile is None or profile.id != donation.matched_ngo_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Directions only available to the matched NGO")
        ngo = profile
        if ngo.address_id:
            from app.models import Address

            ngo.address = await db.get(Address, ngo.address_id)
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admins cannot request directions")

    if ngo is None or donation.pickup_lat is None or donation.pickup_lng is None or ngo.address is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Directions unavailable for this donation")

    origin = (donation.pickup_lat, donation.pickup_lng)
    dest = (ngo.address.lat, ngo.address.lng)
    return await directions_service.get_directions(origin, dest)


@router.post("/{donation_id}/confirm-pickup")
async def confirm_pickup(
    donation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    donation = await db.get(Donation, donation_id)
    if donation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")

    if donation.status not in (DonationStatus.matched.value, DonationStatus.picked_up.value):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Donation is not in a pickable state")

    side = None
    if user.role == Role.donor.value and donation.donor_id == user.id:
        donation.completed_by_donor = True
        side = "donor"
    elif user.role == Role.ngo.value:
        profile = (
            await db.execute(select(NGOProfile).where(NGOProfile.user_id == user.id))
        ).scalar_one_or_none()
        if profile is None or donation.matched_ngo_id != profile.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not the matched NGO")
        donation.completed_by_ngo = True
        side = "ngo"
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot confirm pickup")

    if donation.status == DonationStatus.matched.value:
        donation.status = DonationStatus.picked_up.value
    if donation.completed_by_donor and donation.completed_by_ngo:
        donation.status = DonationStatus.completed.value
        donor = await db.get(User, donation.donor_id)
        ngo_user = profile.user if side == "ngo" else None
        if ngo_user is None and donation.matched_ngo_id:
            ngo = await db.get(NGOProfile, donation.matched_ngo_id)
            ngo_user = await db.get(User, ngo.user_id) if ngo else None
        if donor:
            await notifications.create_notification(
                db, str(donor.id), NotificationType.pickup_confirmed, "Pickup confirmed",
                f"{donation.food_name} has been fully completed.", payload={"donation_id": str(donation.id)},
            )
        if ngo_user:
            await notifications.create_notification(
                db, str(ngo_user.id), NotificationType.pickup_confirmed, "Pickup confirmed",
                f"{donation.food_name} has been fully completed.", payload={"donation_id": str(donation.id)},
            )

    await audit.log_audit(
        db, "donation.confirm_pickup", actor_user_id=str(user.id), target_type="donation", target_id=str(donation.id),
        metadata={"side": side},
    )
    await db.commit()
    return {"message": "Pickup confirmed", "status": donation.status, "side": side}
