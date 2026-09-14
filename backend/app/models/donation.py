"""Donation and photo models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk


class Donation(Base, TimestampMixin):
    __tablename__ = "donations"

    id: Mapped[uuid.UUID] = uuid_pk()
    donor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    address_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("addresses.id"), nullable=True)

    food_name: Mapped[str] = mapped_column(String(255), nullable=False)
    food_category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    quantity_value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    quantity_unit: Mapped[str] = mapped_column(String(16), nullable=False, default="meals")
    preparation_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    best_before: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_match", index=True)
    # Geocoded pickup location cached on the donation row (fast candidate queries).
    pickup_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    pickup_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Set once a match is accepted (post-match directions).
    matched_ngo_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ngo_profiles.id"), nullable=True)
    completed_by_donor: Mapped[bool] = mapped_column(nullable=False, default=False)
    completed_by_ngo: Mapped[bool] = mapped_column(nullable=False, default=False)

    donor: Mapped["User"] = relationship(foreign_keys=[donor_id])
    address: Mapped["Address"] = relationship()
    photos: Mapped[list["DonationPhoto"]] = relationship(back_populates="donation", cascade="all, delete-orphan")
    match_requests: Mapped[list["MatchRequest"]] = relationship(back_populates="donation")

    @property
    def quantity_in_meals(self) -> float:
        """Convert quantity to meal-equivalents for capacity/impact math."""
        from app.core.config import settings

        if self.quantity_unit == "meals":
            return float(self.quantity_value)
        if self.quantity_unit == "kg":
            return float(self.quantity_value) / settings.avg_meal_weight_kg
        # packets -> assume one meal-equivalent per packet
        return float(self.quantity_value)


class DonationPhoto(Base):
    __tablename__ = "donation_photos"

    id: Mapped[uuid.UUID] = uuid_pk()
    donation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("donations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)

    donation: Mapped["Donation"] = relationship(back_populates="photos")


from app.models.match import MatchRequest  # noqa: E402
from app.models.profile import NGOProfile  # noqa: E402
from app.models.user import User  # noqa: E402
