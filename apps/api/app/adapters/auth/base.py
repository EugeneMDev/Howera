"""Authentication provider interfaces."""

from abc import ABC, abstractmethod

from app.schemas.auth import AuthPrincipal


class AuthVerificationError(Exception):
    """Raised when a token cannot be verified or normalized."""


class TokenVerifier(ABC):
    """Provider-neutral token verification interface."""

    @abstractmethod
    def verify_token(self, token: str) -> AuthPrincipal:
        """Verify token and return normalized principal."""


__all__ = ["AuthVerificationError", "TokenVerifier"]
