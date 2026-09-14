"""API v1 router aggregation."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import admin, auth, donations, health, ngo, notifications, reviews, uploads, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(donations.router)
api_router.include_router(ngo.router)
api_router.include_router(admin.router)
api_router.include_router(notifications.router)
api_router.include_router(reviews.router)
api_router.include_router(uploads.router)
