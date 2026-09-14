"""Admin routes: verification workflow, dashboard overview, analytics impact."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, require_role
from app.models import Donation, DonorProfile, NGOProfile, User
from app.models.enums import NotificationType, Role, VerificationStatus
from app.schemas.admin import AdminDashboardOverview, ImpactReport
from app.services import analytics, audit, notifications

router = APIRouter(prefix="/admin", tags=["admin"])

admin_only = require_role(Role.admin)


@router.get("/verifications/pending")
async def pending_verifications(_: User = Depends(admin_only), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(NGOProfile)
            .where(NGOProfile.verification_status == VerificationStatus.pending.value)
            .options(selectinload(NGOProfile.user), selectinload(NGOProfile.address))
            .order_by(NGOProfile.created_at.desc())
        )
    ).scalars().all()
    return [
        {
            "id": str(n.id),
            "org_name": n.org_name,
            "registration_number": n.registration_number,
            "contact_person": n.contact_person,
            "email": n.user.email,
            "phone": n.user.phone,
            "capacity_meals_per_day": n.capacity_meals_per_day,
            "food_requirements": n.food_requirements or [],
            "verification_doc_url": n.verification_doc_url,
            "created_at": n.created_at.isoformat(),
            "address": {
                "line1": n.address.line1 if n.address else None,
                "city": n.address.city if n.address else None,
            },
        }
        for n in rows
    ]


async def _set_verification(
    ngo_profile_id: uuid.UUID, status_value: str, action: str, request: Request, db: AsyncSession
) -> dict:
    ngo = (
        await db.execute(
            select(NGOProfile)
            .where(NGOProfile.id == ngo_profile_id)
            .options(selectinload(NGOProfile.address), selectinload(NGOProfile.user))
        )
    ).scalar_one_or_none()
    if ngo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NGO not found")
    ngo.verification_status = status_value
    user = ngo.user
    await audit.log_audit(
        db, action, actor_user_id=str(request.state.current_user_id if hasattr(request.state, "current_user_id") else None),
        target_type="ngo_profile", target_id=str(ngo.id),
        ip_address=request.client.host if request.client else None,
    )
    await notifications.notify(
        db,
        user,
        NotificationType.verification_status,
        "NGO verification update",
        f"Your NGO '{ngo.org_name}' has been {status_value}.",
        payload={"verification_status": status_value},
    )
    await db.commit()
    return {"message": f"NGO {status_value}", "id": str(ngo.id), "verification_status": status_value}


@router.post("/verifications/{ngo_profile_id}/approve")
async def approve_ngo(
    ngo_profile_id: uuid.UUID,
    request: Request,
    _: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    return await _set_verification(ngo_profile_id, VerificationStatus.verified.value, "admin.verify.approve", request, db)


@router.post("/verifications/{ngo_profile_id}/reject")
async def reject_ngo(
    ngo_profile_id: uuid.UUID,
    request: Request,
    _: User = Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    return await _set_verification(ngo_profile_id, VerificationStatus.rejected.value, "admin.verify.reject", request, db)


@router.get("/dashboard/overview", response_model=AdminDashboardOverview)
async def dashboard_overview(_: User = Depends(admin_only), db: AsyncSession = Depends(get_db)):
    return await analytics.admin_overview(db)


@router.get("/analytics/impact", response_model=ImpactReport)
async def impact(_: User = Depends(admin_only), db: AsyncSession = Depends(get_db)):
    return await analytics.impact_report(db)


@router.get("/restaurants")
async def list_restaurants(_: User = Depends(admin_only), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(DonorProfile)
            .options(selectinload(DonorProfile.user), selectinload(DonorProfile.address))
            .order_by(DonorProfile.created_at.desc())
            .limit(200)
        )
    ).scalars().all()
    return [
        {
            "id": str(d.id),
            "restaurant_name": d.restaurant_name,
            "owner_name": d.owner_name,
            "email": d.user.email,
            "phone": d.user.phone,
            "city": d.address.city if d.address else None,
            "is_verified": d.is_verified,
            "created_at": d.created_at.isoformat(),
        }
        for d in rows
    ]


@router.get("/ngos")
async def list_ngos(_: User = Depends(admin_only), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(NGOProfile)
            .options(selectinload(NGOProfile.user), selectinload(NGOProfile.address))
            .order_by(NGOProfile.created_at.desc())
            .limit(200)
        )
    ).scalars().all()
    return [
        {
            "id": str(n.id),
            "org_name": n.org_name,
            "registration_number": n.registration_number,
            "contact_person": n.contact_person,
            "email": n.user.email,
            "verification_status": n.verification_status,
            "capacity_meals_per_day": n.capacity_meals_per_day,
            "reliability_score": n.reliability_score,
            "city": n.address.city if n.address else None,
            "created_at": n.created_at.isoformat(),
        }
        for n in rows
    ]


@router.get("/donations")
async def list_all_donations(_: User = Depends(admin_only), db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(select(Donation).options(selectinload(Donation.address)).order_by(Donation.created_at.desc()).limit(200))
    ).scalars().all()
    items = []
    for d in rows:
        donor = await db.get(User, d.donor_id)
        items.append(
            {
                "id": str(d.id),
                "food_name": d.food_name,
                "food_category": d.food_category,
                "quantity_value": float(d.quantity_value),
                "quantity_unit": d.quantity_unit,
                "status": d.status,
                "donor": donor.display_name() if donor else None,
                "city": d.address.city if d.address else None,
                "created_at": d.created_at.isoformat(),
            }
        )
    return items
