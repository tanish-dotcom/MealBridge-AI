"""Auth routes: donor/ngo signup, role-aware login, refresh rotation, logout."""

import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import Address, DonorProfile, NGOProfile, RefreshToken, User
from app.models.enums import Role
from app.schemas.auth import (
    AuthResponse,
    DonorSignupRequest,
    LoginRequest,
    LogoutRequest,
    NgoSignupRequest,
    RefreshRequest,
)
from app.schemas.common import TokenPair
from app.services import audit, geocoding
from app.services.geocoding import GeocodingError

router = APIRouter(prefix="/auth", tags=["auth"])


def _token_pair(user: User) -> TokenPair:
    access = create_access_token(str(user.id), extra={"role": user.role})
    return TokenPair(
        access_token=access,
        refresh_token="",
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def _issue_tokens(db: AsyncSession, user: User, request: Request) -> TokenPair:
    access = create_access_token(str(user.id), extra={"role": user.role})
    refresh, jti, expires = create_refresh_token(str(user.id))
    db.add(
        RefreshToken(
            jti=jti,
            user_id=user.id,
            token_hash=hashlib.sha256(refresh.encode()).hexdigest(),
            expires_at=expires,
            created_at=datetime.now(timezone.utc),
            user_agent=request.headers.get("user-agent")[:300] if request.headers.get("user-agent") else None,
            ip_address=request.client.host if request.client else None,
        )
    )
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=settings.access_token_expire_minutes * 60)


async def _create_address(db: AsyncSession, address_text: str, city: str) -> Address:
    address = Address(line1=address_text, city=city, country="India")
    try:
        geo = await geocoding.geocode(f"{address_text}, {city}, India")
        address.lat, address.lng = geo.lat, geo.lng
    except GeocodingError:
        address.lat, address.lng = None, None
    db.add(address)
    await db.flush()
    if address.lat is not None and address.lng is not None:
        await geocoding.sync_geography(db, str(address.id), address.lat, address.lng)
    return address


async def _check_email_or_phone_unique(db: AsyncSession, email: str, phone: str | None) -> None:
    exists = (
        await db.execute(select(User.id).where((User.email == email) | (User.phone == phone)))
    ).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or phone already registered")


@router.post("/signup/donor", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def signup_donor(request: Request, payload: DonorSignupRequest, db: AsyncSession = Depends(get_db)):
    await _check_email_or_phone_unique(db, payload.email, payload.phone)
    user = User(
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=Role.donor.value,
        first_name=payload.owner_name,
        preferences={"email_notifications": True, "sms_alerts": False},
    )
    db.add(user)
    await db.flush()
    address = await _create_address(db, payload.address, payload.city)
    db.add(
        DonorProfile(
            user_id=user.id,
            restaurant_name=payload.restaurant_name,
            owner_name=payload.owner_name,
            donor_type="restaurant",
            address_id=address.id,
        )
    )
    await audit.log_audit(db, "donor.signup", actor_user_id=str(user.id), target_type="user", target_id=str(user.id))
    await db.flush()
    tokens = await _issue_tokens(db, user, request)
    await db.commit()
    return AuthResponse(
        token_pair=tokens, user_id=user.id, email=user.email, role=user.role
    )


@router.post("/signup/ngo", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def signup_ngo(request: Request, payload: NgoSignupRequest, db: AsyncSession = Depends(get_db)):
    await _check_email_or_phone_unique(db, payload.email, payload.phone)
    user = User(
        email=payload.email,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=Role.ngo.value,
        first_name=payload.contact_person,
        preferences={"email_notifications": True, "sms_alerts": False},
    )
    db.add(user)
    await db.flush()
    address = await _create_address(db, payload.address, payload.city)
    db.add(
        NGOProfile(
            user_id=user.id,
            org_name=payload.org_name,
            registration_number=payload.registration_number,
            contact_person=payload.contact_person,
            verification_status="pending",
            capacity_meals_per_day=payload.capacity_meals_per_day,
            food_requirements=payload.food_requirements,
            address_id=address.id,
        )
    )
    await audit.log_audit(
        db, "ngo.signup", actor_user_id=str(user.id), target_type="user", target_id=str(user.id)
    )
    await db.flush()
    tokens = await _issue_tokens(db, user, request)
    await db.commit()
    return AuthResponse(
        token_pair=tokens,
        user_id=user.id,
        email=user.email,
        role=user.role,
        profile_status="pending",
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit("20/minute")
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(select(User).where(User.email == payload.email))
    ).scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive")

    profile_status = None
    if user.role == Role.ngo.value:
        profile = (
            await db.execute(select(NGOProfile).where(NGOProfile.user_id == user.id))
        ).scalar_one_or_none()
        profile_status = profile.verification_status if profile else None

    tokens = await _issue_tokens(db, user, request)
    await audit.log_audit(db, "auth.login", actor_user_id=str(user.id), ip_address=request.client.host if request.client else None)
    await db.commit()
    return AuthResponse(
        token_pair=tokens,
        user_id=user.id,
        email=user.email,
        role=user.role,
        profile_status=profile_status,
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    claims = decode_token(payload.refresh_token, expected_type="refresh")
    if not claims:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    row = (
        await db.execute(select(RefreshToken).where(RefreshToken.jti == claims["jti"]))
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
    presented_hash = hashlib.sha256(payload.refresh_token.encode()).hexdigest()
    if row.token_hash != presented_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token mismatch")

    now = datetime.now(timezone.utc)
    if row.expires_at.tzinfo is None:
        row.expires_at = row.expires_at.replace(tzinfo=timezone.utc)
    if row.expires_at < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired")

    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    # Rotate: revoke the old token, issue a fresh one.
    row.revoked_at = now
    new_refresh, new_jti, new_expires = create_refresh_token(str(user.id))
    row.replaced_by = new_jti
    db.add(
        RefreshToken(
            jti=new_jti,
            user_id=user.id,
            token_hash=hashlib.sha256(new_refresh.encode()).hexdigest(),
            expires_at=new_expires,
            created_at=now,
            user_agent=request.headers.get("user-agent")[:300] if request.headers.get("user-agent") else None,
            ip_address=request.client.host if request.client else None,
        )
    )
    access = create_access_token(str(user.id), extra={"role": user.role})
    await db.commit()
    return TokenPair(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout")
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_db)):
    claims = decode_token(payload.refresh_token, expected_type="refresh")
    if claims:
        row = (
            await db.execute(select(RefreshToken).where(RefreshToken.jti == claims["jti"]))
        ).scalar_one_or_none()
        if row is not None and row.revoked_at is None:
            row.revoked_at = datetime.now(timezone.utc)
            await db.commit()
    return {"message": "Logged out"}


@router.get("/me", response_model=None)
async def me(user: User = Depends(get_current_user)):
    return {"id": str(user.id), "email": user.email, "role": user.role}
