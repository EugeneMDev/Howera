"""Job routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.routes.dependencies import get_authenticated_principal, get_job_service
from app.schemas.auth import AuthPrincipal
from app.schemas.error import ErrorResponse
from app.schemas.job import Job
from app.services.jobs import JobService

router = APIRouter(prefix="/projects", tags=["Jobs"])


@router.post(
    "/{projectId}/jobs",
    response_model=Job,
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def create_job(
    project_id: Annotated[str, Path(alias="projectId")],
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[JobService, Depends(get_job_service)],
) -> Job:
    return service.create_job(owner_id=principal.user_id, project_id=project_id)
