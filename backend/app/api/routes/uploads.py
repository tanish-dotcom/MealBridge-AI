"""File upload routes with server-side validation."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, get_ngo_profile
from app.models import Donation, DonationPhoto, NGOProfile, User
from app.models.enums import Role
from app.services import files
from app.services.files import UploadValidationError

router = APIRouter(tags=["uploads"])


@router.post("/uploads/food-photo/{donation_id}")
async def upload_food_photo(
    donation_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != Role.donor.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Donor access required")
    donation = await db.get(Donation, donation_id)
    if donation is None or donation.donor_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
    data = await file.read()
    try:
        saved = await files.save_file(data, file.content_type or "", file.filename or "", "food_photo")
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    photo = DonationPhoto(donation_id=donation.id, url=saved.url)
    db.add(photo)
    await db.commit()
    return {"url": saved.url}


@router.post("/uploads/verification-doc")
async def upload_verification_doc(
    file: UploadFile = File(...),
    profile: NGOProfile = Depends(get_ngo_profile),
    db: AsyncSession = Depends(get_db),
):
    data = await file.read()
    try:
        saved = await files.save_file(data, file.content_type or "", file.filename or "", "verification")
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    profile.verification_doc_url = saved.url
    await db.commit()
    return {"url": saved.url}


@router.post("/uploads/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await file.read()
    try:
        saved = await files.save_file(data, file.content_type or "", file.filename or "", "avatar")
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    user.avatar_url = saved.url
    await db.commit()
    return {"url": saved.url}
