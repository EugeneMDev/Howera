"""Dependency wiring for routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.adapters.auth import (
    AuthVerificationError,
    FirebaseTokenVerifier,
    MockTokenVerifier,
    TokenVerifier,
)
from app.core.config import Settings, get_settings
from app.errors import ApiError
from app.repositories.memory import InMemoryStore
from app.schemas.auth import AuthPrincipal
from app.services.jobs import JobService
from app.services.projects import ProjectService

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="bearerAuth")
callback_secret_scheme = APIKeyHeader(
    name="X-Callback-Secret",
    auto_error=False,
    scheme_name="internalCallbackSecret",
)


def _auth_error(message: str) -> ApiError:
    return ApiError(status_code=401, code="UNAUTHORIZED", message=message)


def get_token_verifier(settings: Annotated[Settings, Depends(get_settings)]) -> TokenVerifier:
    """Resolve provider adapter from configuration."""
    if settings.auth_provider == "firebase":
        return FirebaseTokenVerifier(
            project_id=settings.firebase_project_id,
            audience=settings.firebase_audience,
        )
    return MockTokenVerifier()


async def get_authenticated_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    verifier: Annotated[TokenVerifier, Depends(get_token_verifier)],
) -> AuthPrincipal:
    """Validate bearer token and attach normalized principal to request context."""
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise _auth_error("Invalid or missing bearer token")

    try:
        principal = verifier.verify_token(credentials.credentials)
    except AuthVerificationError as exc:
        raise _auth_error(str(exc) or "Invalid bearer token") from exc

    request.state.auth_principal = principal
    return principal


async def require_callback_secret(
    callback_secret: Annotated[str | None, Security(callback_secret_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Validate callback secret for internal endpoints."""
    if callback_secret != settings.callback_secret:
        raise _auth_error("Invalid callback authentication")


def get_store(request: Request) -> InMemoryStore:
    return request.app.state.store


def get_project_service(store: Annotated[InMemoryStore, Depends(get_store)]) -> ProjectService:
    return ProjectService(store)


def get_job_service(store: Annotated[InMemoryStore, Depends(get_store)]) -> JobService:
    return JobService(store)
