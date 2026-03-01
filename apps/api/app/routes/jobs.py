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
    ConfirmUploadRequest,
    ConfirmUploadResponse,
    Job,
    RetryJobRequest,
    RetryJobResponse,
    RunJobResponse,
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
