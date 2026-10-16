
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models import Donation
from app.models.enums import Role
from app.schemas.ml import MatchRequest, MatchResponse, TopNgoResponse
from app.services.ml_service import (
    ModelUnavailableError,
    get_recommendations,
    model_available,
    recommend_top_ngos_for_donation,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/recommendations",
    response_model=MatchResponse,
)
def recommend_ngos(payload: MatchRequest):
    try:
        donation = payload.donation.model_dump()
        ngos = [
            ngo.model_dump()
            for ngo in payload.ngos
        ]

        recommendations = get_recommendations(
            donation=donation,
            ngos=ngos,
        )

        return {
            "recommendations": recommendations
        }

    except Exception:
        logger.exception("MealBridge ML prediction failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to generate recommendations",
        )


@router.get(
    "/donations/{donation_id}/top-ngos",
    response_model=TopNgoResponse,
)
async def top_ngo_suggestions(
    donation_id: uuid.UUID,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ML pipeline: when a restaurant posts a donation, rank the eligible
    nearby NGOs and return the top 5 by predicted acceptance probability."""
    donation = await db.get(Donation, donation_id)
    if donation is None:
        raise HTTPException(status_code=404, detail="Donation not found")

    is_owner = user.role == Role.donor.value and donation.donor_id == user.id
    if not is_owner and user.role != Role.admin.value:
        raise HTTPException(status_code=403, detail="Not your donation")

    if not model_available():
        raise HTTPException(
            status_code=503,
            detail="ML model is unavailable right now",
        )

    try:
        recommendations = await recommend_top_ngos_for_donation(
            session=db,
            donation=donation,
            limit=5,
        )
    except ModelUnavailableError:
        logger.exception("ML model unavailable for donation %s", donation_id)
        raise HTTPException(
            status_code=503,
            detail="ML model is unavailable right now",
        ) from None
    except Exception:
        logger.exception("MealBridge ML pipeline failed for donation %s", donation_id)
        raise HTTPException(
            status_code=500,
            detail="Unable to generate recommendations",
        ) from None

    return {
        "donation_id": donation.id,
        "model_name": "mealbridge_random_forest.pkl",
        "recommendations": recommendations,
    }
