"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.errors import ApiError
from app.repositories.memory import InMemoryStore
from app.routes import internal_router, jobs_router, projects_router
from app.schemas.error import ErrorResponse


_OPENAPI_RESPONSE_CODES: dict[str, dict[str, set[str]]] = {
    "/api/v1/projects": {"post": {"201", "401"}, "get": {"200"}},
    "/api/v1/projects/{projectId}": {"get": {"200", "404"}},
    "/api/v1/projects/{projectId}/jobs": {"post": {"201", "404"}},
    "/api/v1/jobs/{jobId}": {"get": {"200", "404"}},
    "/api/v1/jobs/{jobId}/confirm-upload": {"post": {"200", "404", "409"}},
    "/api/v1/jobs/{jobId}/run": {"post": {"200", "202", "404", "409", "502"}},
    "/api/v1/internal/jobs/{jobId}/status": {"post": {"200", "204", "401", "404", "409"}},
}

_AUTH_VALIDATION_PATHS: set[tuple[str, str]] = {
    ("POST", "/api/v1/projects"),
    ("POST", "/api/v1/projects/{projectId}/jobs"),
}

_CALLBACK_VALIDATION_PATHS: set[tuple[str, str]] = {
    ("POST", "/api/v1/internal/jobs/{jobId}/status"),
}

_CONFIRM_UPLOAD_VALIDATION_PATHS: set[tuple[str, str]] = {
    ("POST", "/api/v1/jobs/{jobId}/confirm-upload"),
}

_INTERNAL_CALLBACK_409_ONEOF_REFS: list[str] = [
    "#/components/schemas/FsmTransitionError",
    "#/components/schemas/CallbackOrderingError",
    "#/components/schemas/EventIdPayloadMismatchError",
]

_CONFIRM_UPLOAD_409_ONEOF_REFS: list[str] = [
    "#/components/schemas/FsmTransitionError",
    "#/components/schemas/VideoUriConflictError",
]


def _apply_contract_response_codes(schema: dict) -> None:
    """Limit documented response codes to this story's contract scope."""
    for path, methods in _OPENAPI_RESPONSE_CODES.items():
        path_item = schema.get("paths", {}).get(path)
        if not path_item:
            continue

        for method, allowed_codes in methods.items():
            operation = path_item.get(method)
            if not operation:
                continue

            responses = operation.setdefault("responses", {})
            for status_code in list(responses.keys()):
                if status_code not in allowed_codes:
                    responses.pop(status_code, None)

            for status_code in sorted(allowed_codes):
                responses.setdefault(status_code, {"description": "See API contract"})


def _apply_internal_callback_conflict_schema(schema: dict) -> None:
    """Force callback 409 response schema to match contract oneOf references."""
    path_item = schema.get("paths", {}).get("/api/v1/internal/jobs/{jobId}/status")
    if not path_item:
        return

    operation = path_item.get("post")
    if not operation:
        return

    responses = operation.setdefault("responses", {})
    conflict = responses.setdefault("409", {"description": "See API contract"})
    content = conflict.setdefault("content", {}).setdefault("application/json", {})
    content["schema"] = {"oneOf": [{"$ref": ref} for ref in _INTERNAL_CALLBACK_409_ONEOF_REFS]}


def _apply_confirm_upload_conflict_schema(schema: dict) -> None:
    """Force confirm-upload 409 response schema to match contract oneOf references."""
    path_item = schema.get("paths", {}).get("/api/v1/jobs/{jobId}/confirm-upload")
    if not path_item:
        return

    operation = path_item.get("post")
    if not operation:
        return

    responses = operation.setdefault("responses", {})
    conflict = responses.setdefault("409", {"description": "See API contract"})
    content = conflict.setdefault("content", {}).setdefault("application/json", {})
    content["schema"] = {"oneOf": [{"$ref": ref} for ref in _CONFIRM_UPLOAD_409_ONEOF_REFS]}


def create_app() -> FastAPI:
    app = FastAPI(title="Howera API", version="1.1.0")
    app.state.store = InMemoryStore()

    @app.exception_handler(ApiError)
    async def handle_api_error(_, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.payload.model_dump(mode="json", exclude_none=True),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Keep protected endpoint status codes within the current contract scope.
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        route_key = (request.method.upper(), route_path)
        if route_key in _AUTH_VALIDATION_PATHS:
            payload = ErrorResponse(code="UNAUTHORIZED", message="Invalid request payload")
            return JSONResponse(status_code=401, content=payload.model_dump())
        if route_key in _CALLBACK_VALIDATION_PATHS:
            payload = ErrorResponse(code="VALIDATION_ERROR", message="Invalid callback payload")
            return JSONResponse(status_code=409, content=payload.model_dump())
        if route_key in _CONFIRM_UPLOAD_VALIDATION_PATHS:
            payload = ErrorResponse(code="VALIDATION_ERROR", message="Invalid confirm-upload payload")
            return JSONResponse(status_code=409, content=payload.model_dump())

        return await request_validation_exception_handler(request, exc)

    api_prefix = "/api/v1"
    app.include_router(projects_router, prefix=api_prefix)
    app.include_router(jobs_router, prefix=api_prefix)
    app.include_router(internal_router, prefix=api_prefix)

    def custom_openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        _apply_contract_response_codes(schema)
        _apply_internal_callback_conflict_schema(schema)
        _apply_confirm_upload_conflict_schema(schema)
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi

    return app


app = create_app()
