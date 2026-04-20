"""Job routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response, status

from app.routes.dependencies import get_authenticated_principal, get_job_service, get_request_correlation_id
from app.schemas.auth import AuthPrincipal
from app.schemas.error import (
    Error,
    ErrorResponse,
    FsmTransitionError,
    NoLeakNotFoundError,
    RetryStateConflictError,
    UpstreamDispatchError,
    VideoUriConflictError,
)
from app.schemas.job import (
    AnnotateScreenshotRequest,
    AnnotateScreenshotResponse,
    AttachUploadedAssetRequest,
    ConfirmCustomUploadRequest,
    ConfirmCustomUploadResponse,
    CreateCustomUploadRequest,
    CreateExportRequest,
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    CustomUploadTicket,
    Export,
    Job,
    RetryJobRequest,
    RetryJobResponse,
    RunJobResponse,
    ScreenshotAnchor,
    ScreenshotAnchorCreateRequest,
    SoftDeleteScreenshotAssetResponse,
    ScreenshotExtractionRequest,
    ScreenshotReplaceRequest,
    ScreenshotTask,
    TranscriptPage,
)
from app.services.jobs import JobService

router = APIRouter(tags=["Jobs"])


@router.post(
    "/projects/{projectId}/jobs",
    response_model=Job,
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": ErrorResponse}, 404: {"model": NoLeakNotFoundError}},
)
async def create_job(
    project_id: Annotated[str, Path(alias="projectId")],
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> Job:
    return service.create_job(owner_id=principal.user_id, project_id=project_id)


@router.get(
    "/jobs/{jobId}",
    response_model=Job,
    responses={404: {"model": NoLeakNotFoundError}},
)
async def get_job(
    job_id: Annotated[str, Path(alias="jobId")],
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> Job:
    return service.get_job(owner_id=principal.user_id, job_id=job_id)


@router.get(
    "/jobs/{jobId}/transcript",
    response_model=TranscriptPage,
    responses={
        404: {"model": NoLeakNotFoundError},
        409: {"model": Error},
    },
)
async def get_transcript(
    job_id: Annotated[str, Path(alias="jobId")],
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
    limit: Annotated[int, Query()] = 200,
    cursor: str | None = None,
) -> TranscriptPage:
    return service.get_transcript(
        owner_id=principal.user_id,
        job_id=job_id,
        limit=limit,
        cursor=cursor,
    )


@router.post(
    "/jobs/{jobId}/confirm-upload",
    response_model=ConfirmUploadResponse,
    responses={
        404: {"model": NoLeakNotFoundError},
        409: {"model": FsmTransitionError | VideoUriConflictError},
    },
)
async def confirm_upload(
    job_id: Annotated[str, Path(alias="jobId")],
    payload: ConfirmUploadRequest,
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> ConfirmUploadResponse:
    return service.confirm_upload(owner_id=principal.user_id, job_id=job_id, video_uri=payload.video_uri)


@router.post(
    "/jobs/{jobId}/run",
    response_model=RunJobResponse,
    responses={
        202: {"model": RunJobResponse},
        404: {"model": NoLeakNotFoundError},
        409: {"model": FsmTransitionError},
        502: {"model": UpstreamDispatchError},
    },
)
async def run_job(
    job_id: Annotated[str, Path(alias="jobId")],
    response: Response,
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> RunJobResponse:
    run_result = service.run_job(owner_id=principal.user_id, job_id=job_id)
    response.status_code = status.HTTP_200_OK if run_result.replayed else status.HTTP_202_ACCEPTED
    return run_result


@router.post(
    "/jobs/{jobId}/exports",
    response_model=Export,
    response_model_exclude_none=True,
    responses={
        200: {"model": Export},
        202: {"model": Export},
        400: {"model": Error},
        404: {"model": NoLeakNotFoundError},
    },
)
async def create_export_request(
    job_id: Annotated[str, Path(alias="jobId")],
    payload: CreateExportRequest,
    response: Response,
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> Export:
    result = service.create_export_request(
        owner_id=principal.user_id,
        job_id=job_id,
        payload=payload,
    )
    response.status_code = status.HTTP_200_OK if result.replayed else status.HTTP_202_ACCEPTED
    return result.export


@router.get(
    "/exports/{exportId}",
    response_model=Export,
    response_model_exclude_none=True,
    responses={404: {"model": NoLeakNotFoundError}},
)
async def get_export(
    export_id: Annotated[str, Path(alias="exportId")],
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> Export:
    return service.get_export(owner_id=principal.user_id, export_id=export_id)


@router.post(
    "/jobs/{jobId}/retry",
    response_model=RetryJobResponse,
    responses={
        200: {"model": RetryJobResponse},
        202: {"model": RetryJobResponse},
        404: {"model": NoLeakNotFoundError},
        409: {"model": RetryStateConflictError},
        502: {"model": UpstreamDispatchError},
    },
)
async def retry_job(
    job_id: Annotated[str, Path(alias="jobId")],
    payload: RetryJobRequest,
    response: Response,
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> RetryJobResponse:
    retry_result = service.retry_job(
        owner_id=principal.user_id,
        job_id=job_id,
        model_profile=payload.model_profile,
        client_request_id=payload.client_request_id,
    )
    response.status_code = status.HTTP_200_OK if retry_result.replayed else status.HTTP_202_ACCEPTED
    return retry_result


@router.post(
    "/jobs/{jobId}/cancel",
    response_model=Job,
    responses={
        404: {"model": NoLeakNotFoundError},
        409: {"model": FsmTransitionError},
    },
)
async def cancel_job(
    job_id: Annotated[str, Path(alias="jobId")],
    correlation_id: Annotated[str, Depends(get_request_correlation_id)],
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> Job:
    return service.cancel_job(owner_id=principal.user_id, job_id=job_id, correlation_id=correlation_id)


@router.post(
    "/jobs/{jobId}/screenshots/extract",
    response_model=ScreenshotTask,
    response_model_exclude_none=True,
    responses={
        200: {"model": ScreenshotTask},
        202: {"model": ScreenshotTask},
        400: {"model": Error},
        404: {"model": NoLeakNotFoundError},
    },
)
async def request_screenshot_extraction(
    job_id: Annotated[str, Path(alias="jobId")],
    payload: ScreenshotExtractionRequest,
    response: Response,
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> ScreenshotTask:
    result = service.request_screenshot_extraction(
        owner_id=principal.user_id,
        job_id=job_id,
        payload=payload,
    )
    response.status_code = status.HTTP_200_OK if result.replayed else status.HTTP_202_ACCEPTED
    return result.task


@router.post(
    "/jobs/{jobId}/screenshots/uploads",
    response_model=CustomUploadTicket,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": NoLeakNotFoundError}},
)
async def create_custom_upload_ticket(
    job_id: Annotated[str, Path(alias="jobId")],
    payload: CreateCustomUploadRequest,
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> CustomUploadTicket:
    return service.create_custom_upload_ticket(
        owner_id=principal.user_id,
        job_id=job_id,
        payload=payload,
    )


@router.post(
    "/jobs/{jobId}/screenshots/uploads/{uploadId}/confirm",
    response_model=ConfirmCustomUploadResponse,
    response_model_exclude_none=True,
    responses={404: {"model": NoLeakNotFoundError}},
)
async def confirm_custom_upload(
    job_id: Annotated[str, Path(alias="jobId")],
    upload_id: Annotated[str, Path(alias="uploadId")],
    payload: ConfirmCustomUploadRequest,
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> ConfirmCustomUploadResponse:
    return service.confirm_custom_upload(
        owner_id=principal.user_id,
        job_id=job_id,
        upload_id=upload_id,
        payload=payload,
    )


@router.post(
    "/instructions/{instructionId}/anchors",
    response_model=ScreenshotAnchor,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": NoLeakNotFoundError}},
)
async def create_screenshot_anchor(
    instruction_id: Annotated[str, Path(alias="instructionId")],
    payload: ScreenshotAnchorCreateRequest,
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> ScreenshotAnchor:
    return service.create_screenshot_anchor(
        owner_id=principal.user_id,
        instruction_id=instruction_id,
        payload=payload,
    )


@router.get(
    "/instructions/{instructionId}/anchors",
    response_model=list[ScreenshotAnchor],
    responses={404: {"model": NoLeakNotFoundError}},
)
async def list_screenshot_anchors(
    instruction_id: Annotated[str, Path(alias="instructionId")],
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
    instruction_version_id: str | None = Query(default=None),
    include_deleted_assets: bool = Query(default=False),
) -> list[ScreenshotAnchor]:
    return service.list_screenshot_anchors(
        owner_id=principal.user_id,
        instruction_id=instruction_id,
        instruction_version_id=instruction_version_id,
        include_deleted_assets=include_deleted_assets,
    )


@router.get(
    "/anchors/{anchorId}",
    response_model=ScreenshotAnchor,
    responses={404: {"model": NoLeakNotFoundError}},
)
async def get_screenshot_anchor(
    anchor_id: Annotated[str, Path(alias="anchorId")],
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
    target_instruction_version_id: str | None = Query(default=None),
) -> ScreenshotAnchor:
    return service.get_screenshot_anchor(
        owner_id=principal.user_id,
        anchor_id=anchor_id,
        target_instruction_version_id=target_instruction_version_id,
    )


@router.post(
    "/anchors/{anchorId}/attach-upload",
    response_model=ScreenshotAnchor,
    response_model_exclude_none=True,
    responses={404: {"model": NoLeakNotFoundError}},
)
async def attach_uploaded_asset(
    anchor_id: Annotated[str, Path(alias="anchorId")],
    payload: AttachUploadedAssetRequest,
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> ScreenshotAnchor:
    return service.attach_uploaded_asset(
        owner_id=principal.user_id,
        anchor_id=anchor_id,
        payload=payload,
    )


@router.post(
    "/anchors/{anchorId}/annotations",
    response_model=AnnotateScreenshotResponse,
    responses={
        400: {"model": Error},
        404: {"model": NoLeakNotFoundError},
    },
)
async def annotate_screenshot(
    anchor_id: Annotated[str, Path(alias="anchorId")],
    payload: AnnotateScreenshotRequest,
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> AnnotateScreenshotResponse:
    return service.annotate_screenshot(
        owner_id=principal.user_id,
        anchor_id=anchor_id,
        payload=payload,
    )


@router.post(
    "/anchors/{anchorId}/replace",
    response_model=ScreenshotTask,
    response_model_exclude_none=True,
    responses={
        200: {"model": ScreenshotTask},
        202: {"model": ScreenshotTask},
        400: {"model": Error},
        404: {"model": NoLeakNotFoundError},
    },
)
async def request_screenshot_replace(
    anchor_id: Annotated[str, Path(alias="anchorId")],
    payload: ScreenshotReplaceRequest,
    response: Response,
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> ScreenshotTask:
    result = service.request_screenshot_replacement(
        owner_id=principal.user_id,
        anchor_id=anchor_id,
        payload=payload,
    )
    response.status_code = status.HTTP_200_OK if result.replayed else status.HTTP_202_ACCEPTED
    return result.task


@router.delete(
    "/anchors/{anchorId}/assets/{assetId}",
    response_model=SoftDeleteScreenshotAssetResponse,
    responses={404: {"model": NoLeakNotFoundError}},
)
async def soft_delete_screenshot_asset(
    anchor_id: Annotated[str, Path(alias="anchorId")],
    asset_id: Annotated[str, Path(alias="assetId")],
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> SoftDeleteScreenshotAssetResponse:
    return service.soft_delete_screenshot_asset(
        owner_id=principal.user_id,
        anchor_id=anchor_id,
        asset_id=asset_id,
    )


@router.get(
    "/screenshot-tasks/{taskId}",
    response_model=ScreenshotTask,
    response_model_exclude_none=True,
    responses={404: {"model": NoLeakNotFoundError}},
)
async def get_screenshot_task(
    task_id: Annotated[str, Path(alias="taskId")],
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> ScreenshotTask:
    return service.get_screenshot_task(
        owner_id=principal.user_id,
        task_id=task_id,
    )
