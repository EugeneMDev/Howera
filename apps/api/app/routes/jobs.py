"""Job routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Response, status

from app.routes.dependencies import get_authenticated_principal, get_job_service
from app.schemas.auth import AuthPrincipal
from app.schemas.error import (
    ErrorResponse,
    FsmTransitionError,
    NoLeakNotFoundError,
    UpstreamDispatchError,
    VideoUriConflictError,
)
from app.schemas.job import ConfirmUploadRequest, ConfirmUploadResponse, Job, RunJobResponse
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
