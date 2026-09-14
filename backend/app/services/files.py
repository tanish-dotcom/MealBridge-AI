"""Object-storage abstraction (local disk for dev, S3-compatible for prod) with
server-side upload validation (MIME sniff + size + Pillow content check)."""
from __future__ import annotations

import io
import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path

import boto3
from anyio import to_thread
from PIL import Image

from app.core.config import settings

ALLOWED_IMAGES = {"image/jpeg": {".jpg", ".jpeg"}, "image/png": {".png"}, "image/webp": {".webp"}}
ALLOWED_DOCS = {"application/pdf": {".pdf"}}

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_DOC_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_AVATAR_BYTES = 2 * 1024 * 1024  # 2 MB


class UploadValidationError(Exception):
    pass


@dataclass
class SavedFile:
    url: str
    key: str


def _detect_mime(data: bytes, declared: str) -> str | None:
    """Sniff the real content type rather than trusting the client hint."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:3] in (b"\xff\xd8\xff",):
        return "image/jpeg"
    if data[:12] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:5] == b"%PDF-":
        return "application/pdf"
    return None


def _validate(data: bytes, declared: str, filename: str, category: str) -> str:
    """Server-side validation. Returns the canonical MIME type."""
    if category == "avatar":
        allowed = ALLOWED_IMAGES
        limit = MAX_AVATAR_BYTES
    elif category in ("verification_doc", "verification"):
        allowed = ALLOWED_DOCS
        limit = MAX_DOC_BYTES
    else:  # food photo
        allowed = ALLOWED_IMAGES
        limit = MAX_IMAGE_BYTES

    if len(data) > limit:
        raise UploadValidationError(
            f"File too large: {len(data)} bytes (limit {limit} bytes)"
        )
    mime = _detect_mime(data, declared)
    if mime not in allowed:
        raise UploadValidationError(f"File type not allowed: {declared or 'unknown'}")

    if mime in ALLOWED_IMAGES:
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
        except Exception as exc:
            raise UploadValidationError("Uploaded file is not a valid image") from exc

    if category not in ("avatar",) and ".pdf" not in filename.lower() and mime != "application/pdf":
        pass  # extensions are advisory; the sniffed MIME is authoritative
    return mime


def _local_save(data: bytes, key: str) -> str:
    base = Path(settings.local_storage_dir)
    dest = base / key
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return f"/media/{key}"


def _s3_save(data: bytes, key: str) -> str:
    if not settings.s3_bucket:
        raise UploadValidationError("S3 storage configured but no S3_BUCKET set")
    client = boto3.client(
        "s3",
        region_name=settings.s3_region or None,
        endpoint_url=settings.s3_endpoint_url or None,
        aws_access_key_id=settings.s3_access_key or None,
        aws_secret_access_key=settings.s3_secret_key or None,
    )
    client.put_object(Bucket=settings.s3_bucket, Key=key, Body=data)
    if settings.s3_public_base_url:
        return f"{settings.s3_public_base_url.rstrip('/')}/{key}"
    return f"https://{settings.s3_bucket}.s3.{settings.s3_region or 'us-east-1'}.amazonaws.com/{key}"


async def save_file(data: bytes, declared_mime: str, filename: str, category: str = "food_photo") -> SavedFile:
    """Validate then persist to the configured storage backend."""
    mime = await to_thread.run_sync(_validate, data, declared_mime, filename, category)
    ext = ".pdf" if mime == "application/pdf" else mimetypes.guess_extension(mime) or ".bin"
    key = f"{category}/{uuid.uuid4().hex}{ext}"
    if settings.storage_provider == "s3":
        url = await to_thread.run_sync(_s3_save, data, key)
    else:
        url = await to_thread.run_sync(_local_save, data, key)
    return SavedFile(url=url, key=key)
