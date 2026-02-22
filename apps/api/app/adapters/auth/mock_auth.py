"""Mock auth verifier for local development and tests."""

from app.adapters.auth.base import AuthVerificationError, TokenVerifier
from app.schemas.auth import AuthPrincipal


class MockTokenVerifier(TokenVerifier):
    """Accepts deterministic test tokens only.

    Expected token format:
    - ``test:<user_id>``
    - ``test:<user_id>:<role>``
    """

    def verify_token(self, token: str) -> AuthPrincipal:
        parts = token.split(":")
        if len(parts) not in (2, 3) or parts[0] != "test":
            raise AuthVerificationError("Invalid bearer token")

        user_id = parts[1].strip()
        role = parts[2].strip() if len(parts) == 3 else "editor"

        if not user_id:
            raise AuthVerificationError("Bearer token missing user identity")
        if not role:
            raise AuthVerificationError("Bearer token missing role")

        return AuthPrincipal(user_id=user_id, role=role)


__all__ = ["MockTokenVerifier"]
