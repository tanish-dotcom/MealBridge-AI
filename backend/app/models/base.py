"""SQLAlchemy declarative base with naming conventions."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, MetaData, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import CHAR, TypeDecorator

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UUIDType(TypeDecorator):
    """UUID stored as 32-char hex (SQLite-friendly).

    Accepts ``uuid.UUID`` or UUID strings at bind time so callers can pass
    either; returns ``uuid.UUID`` from results. Keeps the same on-disk format
    as SQLAlchemy's native ``Uuid`` on SQLite.
    """

    impl = CHAR(32)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value.hex
        try:
            return uuid.UUID(str(value)).hex
        except (TypeError, ValueError, AttributeError):
            return None

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(value) if isinstance(value, str) else value
        except (TypeError, ValueError):
            return None

    @property
    def python_type(self):
        return uuid.UUID


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUIDType(), primary_key=True, default=uuid.uuid4)


def str_pk() -> Mapped[str]:
    return mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))


def utcnow() -> datetime:
    """Timezone-aware current UTC time (prefer over datetime.utcnow())."""
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Store datetimes in UTC and always return timezone-aware UTC values.

    SQLite has no native timezone support: `DateTime(timezone=True)` writes the
    UTC wall-clock but reads it back naive, so JSON responses carry no offset and
    the browser misreads them as local time (the "wrong posted time" bug). This
    type normalizes to UTC on the way in and tags UTC on the way out, so every
    API timestamp serializes with an explicit offset and localizes correctly.
    """

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), server_default=func.now(), onupdate=func.now(), nullable=False
    )
