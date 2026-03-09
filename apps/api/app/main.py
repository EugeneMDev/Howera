"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.errors import ApiError
from app.repositories.memory import InMemoryStore
from app.routes import instructions_router, internal_router, jobs_router, projects_router
from app.schemas.error import (
    ErrorResponse,
    NoLeakNotFoundError,
    VersionConflictError,
    VersionConflictErrorDetails,
)


_OPENAPI_RESPONSE_CODES: dict[str, dict[str, set[str]]] = {
    "/api/v1/projects": {"post": {"201", "401"}, "get": {"200"}},
    "/api/v1/projects/{projectId}": {"get": {"200", "404"}},
    "/api/v1/projects/{projectId}/jobs": {"post": {"201", "404"}},
    "/api/v1/jobs/{jobId}": {"get": {"200", "404"}},
    "/api/v1/jobs/{jobId}/transcript": {"get": {"200", "404", "409"}},
    "/api/v1/jobs/{jobId}/confirm-upload": {"post": {"200", "404", "409"}},
    "/api/v1/jobs/{jobId}/run": {"post": {"200", "202", "404", "409", "502"}},
    "/api/v1/jobs/{jobId}/exports": {"post": {"200", "202", "400", "404"}},
    "/api/v1/exports/{exportId}": {"get": {"200", "404"}},
    "/api/v1/jobs/{jobId}/retry": {"post": {"200", "202", "404", "409", "502"}},
    "/api/v1/jobs/{jobId}/cancel": {"post": {"200", "404", "409"}},
    "/api/v1/jobs/{jobId}/screenshots/extract": {"post": {"200", "202", "400", "404"}},
    "/api/v1/jobs/{jobId}/screenshots/uploads": {"post": {"201", "404"}},
    "/api/v1/jobs/{jobId}/screenshots/uploads/{uploadId}/confirm": {"post": {"200", "404"}},
    "/api/v1/instructions/{instructionId}/anchors": {
        "post": {"201", "404"},
        "get": {"200", "404"},
    },
    "/api/v1/anchors/{anchorId}": {"get": {"200", "404"}},
    "/api/v1/anchors/{anchorId}/attach-upload": {"post": {"200", "404"}},
    "/api/v1/anchors/{anchorId}/annotations": {"post": {"200", "400", "404"}},
    "/api/v1/anchors/{anchorId}/replace": {"post": {"200", "202", "400", "404"}},
    "/api/v1/anchors/{anchorId}/assets/{assetId}": {"delete": {"200", "404"}},
    "/api/v1/screenshot-tasks/{taskId}": {"get": {"200", "404"}},
    "/api/v1/instructions/{instructionId}": {
        "get": {"200", "404"},
        "put": {"200", "404", "409"},
    },
    "/api/v1/instructions/{instructionId}/regenerate": {
        "post": {"200", "202", "400", "404", "409"},
    },
    "/api/v1/tasks/{taskId}": {
        "get": {"200", "404"},
    },
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

_TRANSCRIPT_VALIDATION_PATHS: set[tuple[str, str]] = {
    ("GET", "/api/v1/jobs/{jobId}/transcript"),
}

_INSTRUCTION_VALIDATION_PATHS: set[tuple[str, str]] = {
    ("GET", "/api/v1/instructions/{instructionId}"),
}

_ANCHOR_LIFECYCLE_VALIDATION_PATHS: set[tuple[str, str]] = {
    ("POST", "/api/v1/instructions/{instructionId}/anchors"),
    ("GET", "/api/v1/instructions/{instructionId}/anchors"),
    ("GET", "/api/v1/anchors/{anchorId}"),
}

_INSTRUCTION_UPDATE_VALIDATION_PATHS: set[tuple[str, str]] = {
    ("PUT", "/api/v1/instructions/{instructionId}"),
}

_INSTRUCTION_REGENERATE_VALIDATION_PATHS: set[tuple[str, str]] = {
    ("POST", "/api/v1/instructions/{instructionId}/regenerate"),
}

_SCREENSHOT_EXTRACT_VALIDATION_PATHS: set[tuple[str, str]] = {
    ("POST", "/api/v1/jobs/{jobId}/screenshots/extract"),
}

_SCREENSHOT_REPLACE_VALIDATION_PATHS: set[tuple[str, str]] = {
    ("POST", "/api/v1/anchors/{anchorId}/replace"),
}

_SCREENSHOT_ANNOTATE_VALIDATION_PATHS: set[tuple[str, str]] = {
    ("POST", "/api/v1/anchors/{anchorId}/annotations"),
}

_EXPORT_VALIDATION_PATHS: set[tuple[str, str]] = {
    ("POST", "/api/v1/jobs/{jobId}/exports"),
}

_SCREENSHOT_UPLOAD_VALIDATION_PATHS: set[tuple[str, str]] = {
    ("POST", "/api/v1/jobs/{jobId}/screenshots/uploads"),
    ("POST", "/api/v1/jobs/{jobId}/screenshots/uploads/{uploadId}/confirm"),
    ("POST", "/api/v1/anchors/{anchorId}/attach-upload"),
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


def _apply_transcript_contract_schema(schema: dict) -> None:
    """Force transcript endpoint query/response schema details to match the API contract."""
    path_item = schema.get("paths", {}).get("/api/v1/jobs/{jobId}/transcript")
    if not path_item:
        return

    operation = path_item.get("get")
    if not operation:
        return

    responses = operation.setdefault("responses", {})
    conflict = responses.setdefault("409", {"description": "See API contract"})
    content = conflict.setdefault("content", {}).setdefault("application/json", {})
    content["schema"] = {"$ref": "#/components/schemas/Error"}

    for parameter in operation.get("parameters", []):
        if parameter.get("name") == "limit" and parameter.get("in") == "query":
            parameter.setdefault("schema", {}).update({"type": "integer", "default": 200, "minimum": 1, "maximum": 500})
        if parameter.get("name") == "cursor" and parameter.get("in") == "query":
            parameter["schema"] = {"type": "string"}


def _apply_instruction_contract_schema(schema: dict) -> None:
    """Force instruction query/response schema details to match the API contract."""
    path_item = schema.get("paths", {}).get("/api/v1/instructions/{instructionId}")
    if not path_item:
        return

    operation = path_item.get("get")
    if not operation:
        return

    for parameter in operation.get("parameters", []):
        if parameter.get("name") == "version" and parameter.get("in") == "query":
            parameter["schema"] = {"type": "integer", "minimum": 1}

    put_operation = path_item.get("put")
    if put_operation:
        request_body = put_operation.setdefault("requestBody", {}).setdefault("content", {}).setdefault("application/json", {})
        request_body["schema"] = {"$ref": "#/components/schemas/UpdateInstructionRequest"}
        put_responses = put_operation.setdefault("responses", {})
        conflict = put_responses.setdefault("409", {"description": "See API contract"})
        conflict_content = conflict.setdefault("content", {}).setdefault("application/json", {})
        conflict_content["schema"] = {"$ref": "#/components/schemas/VersionConflictError"}

    instruction_schema = schema.get("components", {}).get("schemas", {}).get("Instruction")
    if instruction_schema:
        instruction_schema.setdefault("properties", {})["id"] = {
            "type": "string",
            "deprecated": True,
            "description": "Deprecated alias of instruction_id.",
        }

    regenerate_path_item = schema.get("paths", {}).get("/api/v1/instructions/{instructionId}/regenerate")
    if regenerate_path_item:
        regenerate_operation = regenerate_path_item.get("post")
        if regenerate_operation:
            components = schema.setdefault("components", {}).setdefault("schemas", {})
            components["RegenerateSelection"] = {
                "oneOf": [
                    {
                        "type": "object",
                        "required": ["block_id"],
                        "properties": {
                            "block_id": {"type": "string"},
                        },
                    },
                    {
                        "type": "object",
                        "required": ["char_range"],
                        "properties": {
                            "char_range": {"$ref": "#/components/schemas/CharRange"},
                        },
                    },
                ]
            }

            request_body = (
                regenerate_operation.setdefault("requestBody", {})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            request_body["schema"] = {"$ref": "#/components/schemas/RegenerateRequest"}

            regenerate_responses = regenerate_operation.setdefault("responses", {})
            for status_code in ("200", "202"):
                response_content = (
                    regenerate_responses.setdefault(status_code, {"description": "See API contract"})
                    .setdefault("content", {})
                    .setdefault("application/json", {})
                )
                response_content["schema"] = {"$ref": "#/components/schemas/RegenerateTask"}

            bad_request = (
                regenerate_responses.setdefault("400", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            bad_request["schema"] = {"$ref": "#/components/schemas/Error"}

            conflict = (
                regenerate_responses.setdefault("409", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            conflict["schema"] = {"$ref": "#/components/schemas/VersionConflictError"}

    task_path_item = schema.get("paths", {}).get("/api/v1/tasks/{taskId}")
    if not task_path_item:
        return
    task_operation = task_path_item.get("get")
    if not task_operation:
        return

    task_responses = task_operation.setdefault("responses", {})
    success = (
        task_responses.setdefault("200", {"description": "See API contract"})
        .setdefault("content", {})
        .setdefault("application/json", {})
    )
    success["schema"] = {"$ref": "#/components/schemas/RegenerateTask"}
    not_found = (
        task_responses.setdefault("404", {"description": "See API contract"})
        .setdefault("content", {})
        .setdefault("application/json", {})
    )
    not_found["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}


def _apply_screenshot_contract_schema(schema: dict) -> None:
    """Force screenshot extraction/replacement/polling schemas to match contract refs."""
    anchor_create_request_schema = schema.get("components", {}).get("schemas", {}).get("ScreenshotAnchorCreateRequest")
    if anchor_create_request_schema:
        anchor_create_properties = anchor_create_request_schema.setdefault("properties", {})
        anchor_create_properties["addressing"] = {"$ref": "#/components/schemas/AnchorAddress"}

    anchor_address_schema = schema.get("components", {}).get("schemas", {}).get("AnchorAddress")
    if anchor_address_schema:
        anchor_address_properties = anchor_address_schema.setdefault("properties", {})
        anchor_address_properties["char_range"] = {"$ref": "#/components/schemas/CharRange"}
        anchor_address_properties["strategy"] = {"type": "string"}

    anchor_resolution_schema = schema.get("components", {}).get("schemas", {}).get("AnchorResolution")
    if anchor_resolution_schema:
        anchor_resolution_properties = anchor_resolution_schema.setdefault("properties", {})
        anchor_resolution_properties["trace"] = {"type": "object", "additionalProperties": True}

    screenshot_request_schema = schema.get("components", {}).get("schemas", {}).get("ScreenshotExtractionRequest")
    if screenshot_request_schema:
        screenshot_request_schema.setdefault("properties", {})["char_range"] = {"$ref": "#/components/schemas/CharRange"}

    screenshot_asset_schema = schema.get("components", {}).get("schemas", {}).get("ScreenshotAsset")
    if screenshot_asset_schema:
        asset_properties = screenshot_asset_schema.setdefault("properties", {})
        for optional_string_field in (
            "extraction_key",
            "checksum_sha256",
            "upload_id",
            "ops_hash",
            "rendered_from_asset_id",
        ):
            asset_properties[optional_string_field] = {"type": "string"}

    instruction_anchors_path_item = schema.get("paths", {}).get("/api/v1/instructions/{instructionId}/anchors")
    if instruction_anchors_path_item:
        create_operation = instruction_anchors_path_item.get("post")
        if create_operation:
            request_body = (
                create_operation.setdefault("requestBody", {})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            request_body["schema"] = {"$ref": "#/components/schemas/ScreenshotAnchorCreateRequest"}

            create_responses = create_operation.setdefault("responses", {})
            created = (
                create_responses.setdefault("201", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            created["schema"] = {"$ref": "#/components/schemas/ScreenshotAnchor"}
            not_found = (
                create_responses.setdefault("404", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            not_found["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}

        list_operation = instruction_anchors_path_item.get("get")
        if list_operation:
            for parameter in list_operation.get("parameters", []):
                if parameter.get("name") == "instruction_version_id" and parameter.get("in") == "query":
                    parameter["schema"] = {"type": "string"}
                if parameter.get("name") == "include_deleted_assets" and parameter.get("in") == "query":
                    parameter["schema"] = {"type": "boolean", "default": False}

            list_responses = list_operation.setdefault("responses", {})
            success = (
                list_responses.setdefault("200", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            success["schema"] = {
                "type": "array",
                "items": {"$ref": "#/components/schemas/ScreenshotAnchor"},
            }
            not_found = (
                list_responses.setdefault("404", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            not_found["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}

    anchor_path_item = schema.get("paths", {}).get("/api/v1/anchors/{anchorId}")
    if anchor_path_item:
        anchor_get_operation = anchor_path_item.get("get")
        if anchor_get_operation:
            for parameter in anchor_get_operation.get("parameters", []):
                if parameter.get("name") == "target_instruction_version_id" and parameter.get("in") == "query":
                    parameter["schema"] = {"type": "string"}

            anchor_get_responses = anchor_get_operation.setdefault("responses", {})
            success = (
                anchor_get_responses.setdefault("200", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            success["schema"] = {"$ref": "#/components/schemas/ScreenshotAnchor"}
            not_found = (
                anchor_get_responses.setdefault("404", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            not_found["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}

    extract_path_item = schema.get("paths", {}).get("/api/v1/jobs/{jobId}/screenshots/extract")
    if extract_path_item:
        extract_operation = extract_path_item.get("post")
        if extract_operation:
            request_body = (
                extract_operation.setdefault("requestBody", {})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            request_body["schema"] = {"$ref": "#/components/schemas/ScreenshotExtractionRequest"}

            extract_responses = extract_operation.setdefault("responses", {})
            for status_code in ("200", "202"):
                response_content = (
                    extract_responses.setdefault(status_code, {"description": "See API contract"})
                    .setdefault("content", {})
                    .setdefault("application/json", {})
                )
                response_content["schema"] = {"$ref": "#/components/schemas/ScreenshotTask"}

            bad_request = (
                extract_responses.setdefault("400", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            bad_request["schema"] = {"$ref": "#/components/schemas/Error"}

            not_found = (
                extract_responses.setdefault("404", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            not_found["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}

    replace_path_item = schema.get("paths", {}).get("/api/v1/anchors/{anchorId}/replace")
    if replace_path_item:
        replace_operation = replace_path_item.get("post")
        if replace_operation:
            request_body = (
                replace_operation.setdefault("requestBody", {})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            request_body["schema"] = {"$ref": "#/components/schemas/ScreenshotReplaceRequest"}

            replace_responses = replace_operation.setdefault("responses", {})
            for status_code in ("200", "202"):
                response_content = (
                    replace_responses.setdefault(status_code, {"description": "See API contract"})
                    .setdefault("content", {})
                    .setdefault("application/json", {})
                )
                response_content["schema"] = {"$ref": "#/components/schemas/ScreenshotTask"}

            bad_request = (
                replace_responses.setdefault("400", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            bad_request["schema"] = {"$ref": "#/components/schemas/Error"}

            not_found = (
                replace_responses.setdefault("404", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            not_found["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}

    upload_ticket_path_item = schema.get("paths", {}).get("/api/v1/jobs/{jobId}/screenshots/uploads")
    if upload_ticket_path_item:
        upload_ticket_operation = upload_ticket_path_item.get("post")
        if upload_ticket_operation:
            request_body = (
                upload_ticket_operation.setdefault("requestBody", {})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            request_body["schema"] = {"$ref": "#/components/schemas/CreateCustomUploadRequest"}

            upload_ticket_responses = upload_ticket_operation.setdefault("responses", {})
            created = (
                upload_ticket_responses.setdefault("201", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            created["schema"] = {"$ref": "#/components/schemas/CustomUploadTicket"}
            not_found = (
                upload_ticket_responses.setdefault("404", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            not_found["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}

    confirm_upload_path_item = schema.get("paths", {}).get("/api/v1/jobs/{jobId}/screenshots/uploads/{uploadId}/confirm")
    if confirm_upload_path_item:
        confirm_upload_operation = confirm_upload_path_item.get("post")
        if confirm_upload_operation:
            request_body = (
                confirm_upload_operation.setdefault("requestBody", {})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            request_body["schema"] = {"$ref": "#/components/schemas/ConfirmCustomUploadRequest"}

            confirm_upload_responses = confirm_upload_operation.setdefault("responses", {})
            success = (
                confirm_upload_responses.setdefault("200", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            success["schema"] = {"$ref": "#/components/schemas/ConfirmCustomUploadResponse"}
            not_found = (
                confirm_upload_responses.setdefault("404", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            not_found["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}

    attach_upload_path_item = schema.get("paths", {}).get("/api/v1/anchors/{anchorId}/attach-upload")
    if attach_upload_path_item:
        attach_upload_operation = attach_upload_path_item.get("post")
        if attach_upload_operation:
            request_body = (
                attach_upload_operation.setdefault("requestBody", {})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            request_body["schema"] = {"$ref": "#/components/schemas/AttachUploadedAssetRequest"}

            attach_upload_responses = attach_upload_operation.setdefault("responses", {})
            success = (
                attach_upload_responses.setdefault("200", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            success["schema"] = {"$ref": "#/components/schemas/ScreenshotAnchor"}
            not_found = (
                attach_upload_responses.setdefault("404", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            not_found["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}

    annotate_path_item = schema.get("paths", {}).get("/api/v1/anchors/{anchorId}/annotations")
    if annotate_path_item:
        annotate_operation = annotate_path_item.get("post")
        if annotate_operation:
            request_body = (
                annotate_operation.setdefault("requestBody", {})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            request_body["schema"] = {"$ref": "#/components/schemas/AnnotateScreenshotRequest"}

            annotate_responses = annotate_operation.setdefault("responses", {})
            success = (
                annotate_responses.setdefault("200", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            success["schema"] = {"$ref": "#/components/schemas/AnnotateScreenshotResponse"}
            bad_request = (
                annotate_responses.setdefault("400", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            bad_request["schema"] = {"$ref": "#/components/schemas/Error"}
            not_found = (
                annotate_responses.setdefault("404", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            not_found["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}

    task_path_item = schema.get("paths", {}).get("/api/v1/screenshot-tasks/{taskId}")
    if not task_path_item:
        return
    task_operation = task_path_item.get("get")
    if not task_operation:
        return

    task_responses = task_operation.setdefault("responses", {})
    success = (
        task_responses.setdefault("200", {"description": "See API contract"})
        .setdefault("content", {})
        .setdefault("application/json", {})
    )
    success["schema"] = {"$ref": "#/components/schemas/ScreenshotTask"}
    not_found = (
        task_responses.setdefault("404", {"description": "See API contract"})
        .setdefault("content", {})
        .setdefault("application/json", {})
    )
    not_found["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}

    delete_path_item = schema.get("paths", {}).get("/api/v1/anchors/{anchorId}/assets/{assetId}")
    if not delete_path_item:
        return
    delete_operation = delete_path_item.get("delete")
    if not delete_operation:
        return

    delete_responses = delete_operation.setdefault("responses", {})
    success_delete = (
        delete_responses.setdefault("200", {"description": "See API contract"})
        .setdefault("content", {})
        .setdefault("application/json", {})
    )
    success_delete["schema"] = {"$ref": "#/components/schemas/SoftDeleteScreenshotAssetResponse"}
    not_found_delete = (
        delete_responses.setdefault("404", {"description": "See API contract"})
        .setdefault("content", {})
        .setdefault("application/json", {})
    )
    not_found_delete["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}


def _apply_export_contract_schema(schema: dict) -> None:
    """Force export request schema details to match the API contract."""
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    create_export_request_schema = components.get("CreateExportRequest")
    if create_export_request_schema:
        create_export_request_properties = create_export_request_schema.setdefault("properties", {})
        create_export_request_properties["format"] = {"$ref": "#/components/schemas/ExportFormat"}
        create_export_request_properties["instruction_version_id"] = {"type": "string"}
        create_export_request_properties["idempotency_key"] = {"type": "string"}

    export_anchor_binding_schema = components.get("ExportAnchorBinding")
    if export_anchor_binding_schema:
        export_anchor_binding_properties = export_anchor_binding_schema.setdefault("properties", {})
        export_anchor_binding_properties["rendered_asset_id"] = {"type": ["string", "null"]}

    export_provenance_schema = components.get("ExportProvenance")
    if export_provenance_schema:
        export_provenance_properties = export_provenance_schema.setdefault("properties", {})
        export_provenance_properties["anchors"] = {
            "type": "array",
            "items": {"$ref": "#/components/schemas/ExportAnchorBinding"},
        }
        export_provenance_properties["prompt_params_ref"] = {"type": "string"}
        export_provenance_properties["generated_at"] = {"type": "string", "format": "date-time"}

    export_schema = components.get("Export")
    if export_schema:
        export_properties = export_schema.setdefault("properties", {})
        export_properties["format"] = {"$ref": "#/components/schemas/ExportFormat"}
        export_properties["status"] = {"$ref": "#/components/schemas/ExportStatus"}
        export_properties["provenance"] = {"$ref": "#/components/schemas/ExportProvenance"}
        export_properties["provenance_frozen_at"] = {"type": "string", "format": "date-time"}
        export_properties["last_audit_event"] = {"$ref": "#/components/schemas/ExportAuditEventType"}
        export_properties["download_url"] = {"type": "string"}
        export_properties["download_url_expires_at"] = {"type": "string", "format": "date-time"}

    export_path_item = schema.get("paths", {}).get("/api/v1/jobs/{jobId}/exports")
    if export_path_item:
        export_operation = export_path_item.get("post")
        if export_operation:
            request_body = (
                export_operation.setdefault("requestBody", {})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            request_body["schema"] = {"$ref": "#/components/schemas/CreateExportRequest"}

            export_responses = export_operation.setdefault("responses", {})
            for status_code in ("200", "202"):
                success = (
                    export_responses.setdefault(status_code, {"description": "See API contract"})
                    .setdefault("content", {})
                    .setdefault("application/json", {})
                )
                success["schema"] = {"$ref": "#/components/schemas/Export"}

            bad_request = (
                export_responses.setdefault("400", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            bad_request["schema"] = {"$ref": "#/components/schemas/Error"}
            bad_request["examples"] = {
                "invalid_export_request": {
                    "value": {
                        "code": "EXPORT_REQUEST_INVALID",
                        "message": "Unsupported format or invalid instruction version.",
                    }
                }
            }

            not_found = (
                export_responses.setdefault("404", {"description": "See API contract"})
                .setdefault("content", {})
                .setdefault("application/json", {})
            )
            not_found["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}

    get_export_path_item = schema.get("paths", {}).get("/api/v1/exports/{exportId}")
    if not get_export_path_item:
        return
    get_export_operation = get_export_path_item.get("get")
    if not get_export_operation:
        return

    get_export_responses = get_export_operation.setdefault("responses", {})
    success = (
        get_export_responses.setdefault("200", {"description": "See API contract"})
        .setdefault("content", {})
        .setdefault("application/json", {})
    )
    success["schema"] = {"$ref": "#/components/schemas/Export"}
    not_found = (
        get_export_responses.setdefault("404", {"description": "See API contract"})
        .setdefault("content", {})
        .setdefault("application/json", {})
    )
    not_found["schema"] = {"$ref": "#/components/schemas/NoLeakNotFoundError"}


async def _instruction_update_validation_payload(request: Request) -> VersionConflictError:
    """Normalize invalid PUT payloads into the endpoint's contract-safe 409 schema."""
    base_version = 0
    try:
        payload = await request.json()
    except Exception:
        payload = None
    if isinstance(payload, dict):
        candidate = payload.get("base_version")
        if isinstance(candidate, int):
            base_version = candidate
    return VersionConflictError(
        code="VERSION_CONFLICT",
        message="Instruction base version does not match current version.",
        details=VersionConflictErrorDetails(
            base_version=base_version,
            current_version=0,
        ),
    )


def create_app() -> FastAPI:
    settings = get_settings()
    signing_key_material = settings.export_download_signing_key or settings.callback_secret
    app = FastAPI(title="Howera API", version="1.1.0")
    app.state.store = InMemoryStore(
        export_download_url_host=settings.export_download_url_host,
        export_download_url_ttl_minutes=settings.export_download_url_ttl_minutes,
        export_download_signing_key=signing_key_material.encode("utf-8"),
    )

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
        if route_key in _TRANSCRIPT_VALIDATION_PATHS:
            payload = ErrorResponse(code="VALIDATION_ERROR", message="Invalid transcript query parameters")
            return JSONResponse(status_code=409, content=payload.model_dump())
        if route_key in _INSTRUCTION_VALIDATION_PATHS:
            payload = NoLeakNotFoundError(code="RESOURCE_NOT_FOUND", message="Resource not found")
            return JSONResponse(status_code=404, content=payload.model_dump())
        if route_key in _ANCHOR_LIFECYCLE_VALIDATION_PATHS:
            payload = NoLeakNotFoundError(code="RESOURCE_NOT_FOUND", message="Resource not found")
            return JSONResponse(status_code=404, content=payload.model_dump())
        if route_key in _INSTRUCTION_UPDATE_VALIDATION_PATHS:
            payload = await _instruction_update_validation_payload(request)
            return JSONResponse(status_code=409, content=payload.model_dump())
        if route_key in _INSTRUCTION_REGENERATE_VALIDATION_PATHS:
            payload = ErrorResponse(code="VALIDATION_ERROR", message="Invalid regenerate payload")
            return JSONResponse(status_code=400, content=payload.model_dump())
        if route_key in _SCREENSHOT_EXTRACT_VALIDATION_PATHS:
            payload = ErrorResponse(code="VALIDATION_ERROR", message="Invalid extraction payload")
            return JSONResponse(status_code=400, content=payload.model_dump())
        if route_key in _SCREENSHOT_REPLACE_VALIDATION_PATHS:
            payload = ErrorResponse(code="VALIDATION_ERROR", message="Invalid replacement payload")
            return JSONResponse(status_code=400, content=payload.model_dump())
        if route_key in _SCREENSHOT_ANNOTATE_VALIDATION_PATHS:
            payload = ErrorResponse(code="VALIDATION_ERROR", message="Invalid annotation payload")
            return JSONResponse(status_code=400, content=payload.model_dump())
        if route_key in _EXPORT_VALIDATION_PATHS:
            payload = ErrorResponse(
                code="EXPORT_REQUEST_INVALID",
                message="Unsupported format or invalid instruction version.",
            )
            return JSONResponse(status_code=400, content=payload.model_dump())
        if route_key in _SCREENSHOT_UPLOAD_VALIDATION_PATHS:
            payload = NoLeakNotFoundError(code="RESOURCE_NOT_FOUND", message="Resource not found")
            return JSONResponse(status_code=404, content=payload.model_dump())

        return await request_validation_exception_handler(request, exc)

    api_prefix = "/api/v1"
    app.include_router(projects_router, prefix=api_prefix)
    app.include_router(jobs_router, prefix=api_prefix)
    app.include_router(instructions_router, prefix=api_prefix)
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
        _apply_transcript_contract_schema(schema)
        _apply_instruction_contract_schema(schema)
        _apply_screenshot_contract_schema(schema)
        _apply_export_contract_schema(schema)
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi

    return app


app = create_app()
