"""Utilities for safe structured logging fields."""

from __future__ import annotations

import hashlib
from typing import Any


def safe_log_identifier(value: Any, *, prefix: str) -> str:
    """Return a deterministic non-reversible token for log correlation fields."""
    text = str(value or "").strip()
    if not text:
        return f"{prefix}-missing"

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"

