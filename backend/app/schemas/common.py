"""Shared response schemas."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Message(BaseModel):
    message: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
