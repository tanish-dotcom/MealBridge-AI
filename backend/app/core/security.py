"""Password hashing and JWT token creation/validation."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "sub": subject,
        "jti": str(uuid.uuid4()),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        claims.update(extra)
    return jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, jti: str | None = None) -> tuple[str, str, datetime]:
    """Returns (token, jti, expires_at)."""
    now = datetime.now(timezone.utc)
    token_jti = jti or str(uuid.uuid4())
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    claims = {
        "sub": subject,
        "jti": token_jti,
        "type": "refresh",
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, token_jti, expires_at


def decode_token(token: str, expected_type: str | None = None) -> dict | None:
    try:
        claims = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if expected_type and claims.get("type") != expected_type:
            return None
        return claims
    except JWTError:
        return None
