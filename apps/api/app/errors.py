"""Application exception types."""

from app.schemas.error import ErrorResponse


class ApiError(Exception):
    """Structured API error that maps directly to contract error payloads."""

    def __init__(self, status_code: int, code: str, message: str, details: dict | None = None) -> None:
        self.status_code = status_code
        self.payload = ErrorResponse(code=code, message=message, details=details)
        super().__init__(message)


__all__ = ["ApiError"]
