"""Shared FastAPI dependencies: auth + RBAC + object-level guards."""
from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import decode_token
from app.models import Donation, DonorProfile, NGOProfile, User
from app.models.enums import Role

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    claims = decode_token(credentials.credentials, expected_type="access")
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    try:
        user_id = uuid.UUID(str(claims["sub"]))
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from None
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_role(*roles: Role):
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in {r.value for r in roles}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return dependency


async def get_donor_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DonorProfile:
    if user.role != Role.donor.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Donor access required")
    profile = (
        await db.execute(
            select(DonorProfile)
            .where(DonorProfile.user_id == user.id)
            .options(selectinload(DonorProfile.address))
        )
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donor profile not found")
    return profile


async def get_ngo_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NGOProfile:
    if user.role != Role.ngo.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NGO access required")
    profile = (
        await db.execute(
            select(NGOProfile)
            .where(NGOProfile.user_id == user.id)
            .options(selectinload(NGOProfile.address))
        )
    ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NGO profile not found")
    return profile


async def get_donation_for_donor(
    donation_id: uuid.UUID,
    donor: DonorProfile = Depends(get_donor_profile),
    db: AsyncSession = Depends(get_db),
) -> Donation:
    donation = await db.get(Donation, donation_id)
    if donation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
    if donation.donor_id != donor.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your donation")
    return donation
