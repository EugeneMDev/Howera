"""Firebase Auth token verifier adapter."""

from __future__ import annotations

from app.adapters.auth.base import AuthVerificationError, TokenVerifier
from app.schemas.auth import AuthPrincipal


class FirebaseTokenVerifier(TokenVerifier):
    """Verifies Firebase JWTs and normalizes principal data."""

    def __init__(self, project_id: str | None, audience: str | None) -> None:
        self._project_id = project_id
        self._audience = audience

    def verify_token(self, token: str) -> AuthPrincipal:
        try:
            import firebase_admin
            from firebase_admin import auth as firebase_auth
        except ImportError as exc:  # pragma: no cover - depends on optional package
            raise AuthVerificationError("Firebase auth verifier is unavailable") from exc

        if not firebase_admin._apps:
            firebase_admin.initialize_app()

        try:
            decoded = firebase_auth.verify_id_token(token, check_revoked=True)
        except Exception as exc:  # pragma: no cover - provider exception surface
            raise AuthVerificationError("Invalid bearer token") from exc

        if self._audience and decoded.get("aud") != self._audience:
            raise AuthVerificationError("Invalid bearer token audience")

        if self._project_id:
            issuer = str(decoded.get("iss", ""))
            audience = str(decoded.get("aud", ""))
            if self._project_id not in issuer and audience != self._project_id:
                raise AuthVerificationError("Invalid bearer token issuer")

        user_id = str(decoded.get("uid") or decoded.get("sub") or "").strip()
        role = str(decoded.get("role") or "editor").strip()
        if not user_id:
            raise AuthVerificationError("Bearer token missing user identity")

        return AuthPrincipal(user_id=user_id, role=role)


__all__ = ["FirebaseTokenVerifier"]
