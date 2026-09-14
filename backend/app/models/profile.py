"""Donor and NGO profile models."""
from __future__ import annotations

import uuid

from sqlalchemy import Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk


class DonorProfile(Base, TimestampMixin):
    __tablename__ = "donor_profiles"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    restaurant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_name: Mapped[str] = mapped_column(String(255), nullable=False)
    donor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="restaurant")
    address_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("addresses.id"), nullable=True)
    is_verified: Mapped[bool] = mapped_column(nullable=False, default=False)

    user: Mapped["User"] = relationship(back_populates="donor_profile")
    address: Mapped["Address"] = relationship()


class NGOProfile(Base, TimestampMixin):
    __tablename__ = "ngo_profiles"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    org_name: Mapped[str] = mapped_column(String(255), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_person: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    verification_doc_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    capacity_meals_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    food_requirements: Mapped[list | None] = mapped_column(JSON, nullable=True)
    address_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("addresses.id"), nullable=True)
    reliability_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    user: Mapped["User"] = relationship(back_populates="ngo_profile")
    address: Mapped["Address"] = relationship()


from app.models.user import User  # noqa: E402
