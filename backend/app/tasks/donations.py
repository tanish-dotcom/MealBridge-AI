"""Scheduled donation/matching jobs (Celery beat)."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.core.config import settings
from app.core.database import async_session_factory
from app.models import Donation, MatchRequest
from app.models.enums import DonationStatus
from app.services import matching
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    """Run an async coroutine from a sync Celery task."""
    return asyncio.run(coro)


@celery_app.task(name="app.tasks.donations.expire_stale_match_requests")
def expire_stale_match_requests():
    async def _job():
        async with async_session_factory() as session:
            expired = await matching.expire_stale_requests(session)
            await session.commit()
            logger.info("Expired stale match requests; re-offered %s donations", expired)
            return expired

    return _run(_job())


@celery_app.task(name="app.tasks.donations.expire_stale_donations")
def expire_stale_donations():
    async def _job():
        async with async_session_factory() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.donation_expiry_hours)
            rows = (
                await session.execute(
                    select(Donation.id).where(
                        Donation.status.in_([DonationStatus.pending_match.value, DonationStatus.unmatched.value]),
                        Donation.created_at < cutoff,
                    )
                )
            ).scalars().all()
            if rows:
                await session.execute(
                    update(Donation)
                    .where(Donation.id.in_(rows))
                    .values(status=DonationStatus.expired.value)
                )
                await session.commit()
                logger.info("Expired %s stale donations", len(rows))
            return len(rows)

    return _run(_job())
