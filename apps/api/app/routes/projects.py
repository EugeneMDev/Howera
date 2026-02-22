"""Project routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.routes.dependencies import get_authenticated_principal, get_project_service
from app.schemas.auth import AuthPrincipal
from app.schemas.error import ErrorResponse
from app.schemas.project import CreateProjectRequest, Project
from app.services.projects import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=Project,
    status_code=status.HTTP_201_CREATED,
    responses={401: {"model": ErrorResponse}},
)
async def create_project(
    payload: CreateProjectRequest,
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> Project:
    return service.create_project(owner_id=principal.user_id, name=payload.name)
