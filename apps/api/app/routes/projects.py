"""Project routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.routes.dependencies import get_authenticated_principal, get_project_service
from app.schemas.auth import AuthPrincipal
from app.schemas.error import ErrorResponse, NoLeakNotFoundError
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


@router.get(
    "",
    response_model=list[Project],
    responses={401: {"model": ErrorResponse}},
)
async def list_projects(
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> list[Project]:
    return service.list_projects(owner_id=principal.user_id)


@router.get(
    "/{projectId}",
    response_model=Project,
    responses={401: {"model": ErrorResponse}, 404: {"model": NoLeakNotFoundError}},
)
async def get_project(
    project_id: Annotated[str, Path(alias="projectId")],
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[ProjectService, Depends(get_project_service)],
) -> Project:
    return service.get_project(owner_id=principal.user_id, project_id=project_id)
