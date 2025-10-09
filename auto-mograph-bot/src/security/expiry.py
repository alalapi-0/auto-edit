"""Utility helpers for handling secret expiry information."""
from __future__ import annotations

from datetime import datetime


def days_left(created_at: datetime, ttl_days: int) -> int:
    """Return remaining days before expiry, clamping to zero."""

    delta = datetime.now() - created_at
    remaining = ttl_days - delta.days
    return max(0, remaining)


def is_expired(created_at: datetime, ttl_days: int) -> bool:
    """Return ``True`` if the secret has passed its validity window."""

    return (datetime.now() - created_at).days >= ttl_days


__all__ = ["days_left", "is_expired"]
