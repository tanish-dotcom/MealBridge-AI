"""User profile, password, and preferences routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.core.security import hash_password, verify_password
from app.models import DonorProfile, NGOProfile, User
from app.schemas.user import PasswordChange, PreferencesUpdate, UserOut, UserUpdate
from app.services import audit

router = APIRouter(prefix="/users", tags=["users"])


async def _load_user_with_profiles(db: AsyncSession, user: User) -> User:
    stmt = (
        select(User)
        .where(User.id == user.id)
        .options(
            selectinload(User.donor_profile).selectinload(DonorProfile.address),
            selectinload(User.ngo_profile).selectinload(NGOProfile.address),
        )
    )
    return (await db.execute(stmt)).scalar_one()


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _load_user_with_profiles(db, user)


@router.patch("/me", response_model=UserOut)
async def update_me(payload: UserUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if payload.email and payload.email != user.email:
        exists = (await db.execute(select(User.id).where(User.email == payload.email))).first()
        if exists:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
        user.email = payload.email
    if payload.phone and payload.phone != user.phone:
        exists = (await db.execute(select(User.id).where(User.phone == payload.phone))).first()
        if exists:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone already in use")
        user.phone = payload.phone
    for field in ("first_name", "last_name", "avatar_url"):
        value = getattr(payload, field)
        if value is not None:
            setattr(user, field, value)
    await audit.log_audit(db, "user.update", actor_user_id=str(user.id))
    await db.commit()
    return await _load_user_with_profiles(db, user)


@router.patch("/me/password")
async def change_password(
    payload: PasswordChange, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Current password is incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="New password too short")
    user.password_hash = hash_password(payload.new_password)
    # Revoke all refresh tokens on password change.
    from datetime import datetime, timezone

    from app.models import RefreshToken

    await db.execute(
        RefreshToken.__table__.update()
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await audit.log_audit(db, "user.password_change", actor_user_id=str(user.id))
    await db.commit()
    return {"message": "Password updated"}


@router.patch("/me/preferences")
async def update_preferences(
    payload: PreferencesUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs = dict(user.preferences or {})
    prefs["email_notifications"] = payload.email_notifications
    prefs["sms_alerts"] = payload.sms_alerts
    user.preferences = prefs
    await audit.log_audit(db, "user.preferences", actor_user_id=str(user.id))
    await db.commit()
    return {"preferences": prefs}
