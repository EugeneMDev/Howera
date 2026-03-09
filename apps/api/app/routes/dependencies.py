"""Dependency wiring for routes."""

from __future__ import annotations

import logging
from secrets import compare_digest
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.adapters.auth import (
    AuthVerificationError,
    FirebaseTokenVerifier,
    MockTokenVerifier,
    TokenVerifier,
)
from app.core.config import Settings, get_settings
from app.core.logging_safety import safe_log_identifier
from app.errors import ApiError
from app.repositories.memory import InMemoryStore
from app.schemas.auth import AuthPrincipal
from app.services.instructions import InstructionService
from app.services.jobs import JobService
from app.services.internal_callbacks import InternalCallbackService
from app.services.projects import ProjectService

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="bearerAuth")
callback_secret_scheme = APIKeyHeader(
    name="X-Callback-Secret",
    auto_error=False,
    scheme_name="internalCallbackSecret",
)
logger = logging.getLogger(__name__)


def _auth_error(message: str) -> ApiError:
    return ApiError(status_code=401, code="UNAUTHORIZED", message=message)


def _request_correlation_id(request: Request) -> str:
    existing = getattr(request.state, "correlation_id", None)
    if isinstance(existing, str) and existing:
        return existing

    correlation_id = request.headers.get("X-Correlation-Id")
    if correlation_id:
        request.state.correlation_id = correlation_id
        return correlation_id

    generated = f"req-{uuid4()}"
    request.state.correlation_id = generated
    return generated


def get_request_correlation_id(request: Request) -> str:
    return _request_correlation_id(request)


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
    correlation_id = _request_correlation_id(request)
    safe_correlation_id = safe_log_identifier(correlation_id, prefix="cid")
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        logger.warning(
            "auth.rejected correlation_id=%s method=%s path=%s reason=invalid_or_missing_bearer",
            safe_correlation_id,
            request.method,
            request.url.path,
        )
        raise _auth_error("Invalid or missing bearer token")

    try:
        principal = verifier.verify_token(credentials.credentials)
    except AuthVerificationError as exc:
        logger.warning(
            "auth.rejected correlation_id=%s method=%s path=%s reason=token_verification_failed",
            safe_correlation_id,
            request.method,
            request.url.path,
        )
        raise _auth_error(str(exc) or "Invalid bearer token") from exc

    safe_principal_id = safe_log_identifier(principal.user_id, prefix="pid")
    logger.info(
        "auth.accepted correlation_id=%s method=%s path=%s principal_id=%s role=%s",
        safe_correlation_id,
        request.method,
        request.url.path,
        safe_principal_id,
        principal.role,
    )
    request.state.auth_principal = principal
    return principal


async def require_callback_secret(
    request: Request,
    callback_secret: Annotated[str | None, Security(callback_secret_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Validate callback secret for internal endpoints."""
    correlation_id = _request_correlation_id(request)
    safe_correlation_id = safe_log_identifier(correlation_id, prefix="cid")
    if callback_secret is None or not compare_digest(callback_secret, settings.callback_secret):
        logger.warning(
            "callback.auth_rejected correlation_id=%s method=%s path=%s reason=invalid_callback_secret",
            safe_correlation_id,
            request.method,
            request.url.path,
        )
        raise _auth_error("Invalid callback authentication")


def get_store(request: Request) -> InMemoryStore:
    return request.app.state.store


def get_project_service(store: Annotated[InMemoryStore, Depends(get_store)]) -> ProjectService:
    return ProjectService(store)


def get_job_service(store: Annotated[InMemoryStore, Depends(get_store)]) -> JobService:
    return JobService(store)


def get_instruction_service(store: Annotated[InMemoryStore, Depends(get_store)]) -> InstructionService:
    return InstructionService(store)


def get_internal_callback_service(
    store: Annotated[InMemoryStore, Depends(get_store)],
) -> InternalCallbackService:
    return InternalCallbackService(store)
