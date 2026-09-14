"""Audit logging helper."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


def _coerce_uuid(value: str | uuid.UUID | None) -> uuid.UUID | None:
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None


async def log_audit(
    session: AsyncSession,
    action: str,
    actor_user_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_user_id=_coerce_uuid(actor_user_id),
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata_=metadata,
            ip_address=ip_address,
            created_at=datetime.now(timezone.utc),
        )
    )
