"""Review routes (post-completion ratings)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import Donation, Review, User
from app.models.enums import DonationStatus
from app.schemas.notification import ReviewCreate

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_review(payload: ReviewCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if payload.reviewer_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only review on your own behalf")
    if payload.reviewee_user_id == user.id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Cannot review yourself")

    donation = await db.get(Donation, payload.donation_id)
    if donation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Donation not found")
    if donation.status != DonationStatus.completed.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only completed donations can be reviewed")
    participants = {donation.donor_id, donation.matched_ngo_id}
    if user.id not in participants:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a participant in this donation")

    duplicate = (
        await db.execute(
            select(Review.id).where(
                Review.donation_id == payload.donation_id,
                Review.reviewer_user_id == user.id,
                Review.reviewee_user_id == payload.reviewee_user_id,
            )
        )
    ).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review already submitted")

    review = Review(
        donation_id=payload.donation_id,
        reviewer_user_id=user.id,
        reviewee_user_id=payload.reviewee_user_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    db.add(review)
    await db.commit()
    return {"message": "Review submitted", "id": str(review.id)}
