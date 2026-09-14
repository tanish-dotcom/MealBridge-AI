"""MatchRequest model for the offer/accept/reject lifecycle."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, uuid_pk


class MatchRequest(Base, TimestampMixin):
    __tablename__ = "match_requests"
    __table_args__ = (
        UniqueConstraint("donation_id", "ngo_id", name="uq_match_requests_donation_ngo"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    donation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("donations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ngo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ngo_profiles.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rank_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    match_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="offered", index=True)
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    donation: Mapped["Donation"] = relationship(back_populates="match_requests")
    ngo: Mapped["NGOProfile"] = relationship()


from app.models.donation import Donation  # noqa: E402
from app.models.profile import NGOProfile  # noqa: E402
