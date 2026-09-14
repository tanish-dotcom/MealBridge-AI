"""Notification delivery: in-app rows (always) + email/SMS adapters (configurable)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import aiosmtplib
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Notification, User
from app.models.enums import NotificationType

logger = logging.getLogger(__name__)

SMS_ENABLED_TYPES = {NotificationType.request_received, NotificationType.request_accepted}


async def create_notification(
    session: AsyncSession,
    user_id: str,
    ntype: NotificationType,
    title: str,
    body: str | None = None,
    payload: dict | None = None,
) -> Notification:
    n = Notification(
        user_id=user_id,
        type=ntype.value,
        title=title,
        body=body,
        payload=payload,
        created_at=datetime.now(timezone.utc),
    )
    session.add(n)
    return n


async def _send_email(to: str, subject: str, text_body: str) -> None:
    if settings.email_provider != "smtp":
        logger.info("[email:console] to=%s subject=%s\n%s", to, subject, text_body)
        return
    message = aiosmtplib.SMTPMessage(
        sender=settings.smtp_from,
        recipients=[to],
        subject=subject,
        text=text_body,
    )
    await aiosmtplib.send(
        message,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=True,
    )


async def _send_sms(to: str, text_body: str) -> None:
    if settings.sms_provider != "twilio":
        logger.info("[sms:console] to=%s %s", to, text_body)
        return
    if not settings.twilio_account_sid or not settings.twilio_auth_token:
        logger.warning("Twilio configured but credentials missing; skipping SMS")
        return
    url = (
        f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    )
    data = {"To": to, "From": settings.twilio_from_number, "Body": text_body}
    async with httpx.AsyncClient(timeout=15) as client:
        await client.post(
            url,
            data=data,
            auth=(settings.twilio_account_sid, settings.twilio_auth_token),
        )


async def notify(
    session: AsyncSession,
    user: User,
    ntype: NotificationType,
    title: str,
    body: str | None = None,
    payload: dict | None = None,
    send_email: bool = True,
    send_sms: bool = False,
) -> Notification:
    n = await create_notification(session, str(user.id), ntype, title, body, payload)

    prefs = user.preferences or {}
    if send_email and prefs.get("email_notifications", True) and user.email:
        try:
            await _send_email(user.email, title, body or title)
        except Exception as exc:  # pragma: no cover
            logger.warning("Email send failed for %s: %s", user.email, exc)
    if send_sms and prefs.get("sms_alerts", False) and user.phone:
        try:
            await _send_sms(user.phone, body or title)
        except Exception as exc:  # pragma: no cover
            logger.warning("SMS send failed for %s: %s", user.phone, exc)
    return n
