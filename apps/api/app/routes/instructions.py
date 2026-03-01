"""Instruction routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.routes.dependencies import get_authenticated_principal, get_instruction_service
from app.schemas.auth import AuthPrincipal
from app.schemas.error import NoLeakNotFoundError, VersionConflictError
from app.schemas.instruction import Instruction, UpdateInstructionRequest
from app.services.instructions import InstructionService

router = APIRouter(tags=["Instructions"])


@router.get(
    "/instructions/{instructionId}",
    response_model=Instruction,
    responses={404: {"model": NoLeakNotFoundError}},
)
async def get_instruction(
    instruction_id: Annotated[str, Path(alias="instructionId")],
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[InstructionService, Depends(get_instruction_service)],
    version: Annotated[int | None, Query(ge=1)] = None,
) -> Instruction:
    return service.get_instruction(
        owner_id=principal.user_id,
        instruction_id=instruction_id,
        version=version,
    )


@router.put(
    "/instructions/{instructionId}",
    response_model=Instruction,
    responses={
        404: {"model": NoLeakNotFoundError},
        409: {"model": VersionConflictError},
    },
)
async def update_instruction(
    instruction_id: Annotated[str, Path(alias="instructionId")],
    payload: UpdateInstructionRequest,
    principal: Annotated[AuthPrincipal, Depends(get_authenticated_principal)],
    service: Annotated[InstructionService, Depends(get_instruction_service)],
) -> Instruction:
    return service.update_instruction(
        owner_id=principal.user_id,
        instruction_id=instruction_id,
        base_version=payload.base_version,
        markdown=payload.markdown,
    )
