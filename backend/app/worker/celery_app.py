"""Celery application and beat schedule."""
from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "mealbridge",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.donations"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "expire-stale-match-requests": {
            "task": "app.tasks.donations.expire_stale_match_requests",
            "schedule": 300.0,  # every 5 minutes
        },
        "expire-stale-donations": {
            "task": "app.tasks.donations.expire_stale_donations",
            "schedule": 1800.0,  # every 30 minutes
        },
    },
)
