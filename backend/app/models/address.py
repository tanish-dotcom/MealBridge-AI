"""Address model."""
from __future__ import annotations

import uuid

from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, uuid_pk


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[uuid.UUID] = uuid_pk()
    line1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    line2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(120), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    # NOTE: the PostGIS geography column (`geog`) is intentionally NOT part of the
    # ORM model. It is created by the initial Alembic migration via raw SQL when
    # PostGIS is available, and used only through raw SQL in the ST_DWithin
    # candidate query. Keeping it out of the ORM makes the Haversine fallback work
    # on databases without PostGIS.
