"""API error response schemas."""

from typing import Any
from typing import Literal

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class NoLeakNotFoundError(BaseModel):
    code: Literal["RESOURCE_NOT_FOUND"]
    message: str
