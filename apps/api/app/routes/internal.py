"""Internal callback routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse

from app.routes.dependencies import get_internal_callback_service, require_callback_secret
from app.schemas.error import (
    CallbackOrderingError,
    ErrorResponse,
    EventIdPayloadMismatchError,
    FsmTransitionError,
    NoLeakNotFoundError,
)
from app.schemas.internal import StatusCallbackRequest, StatusCallbackReplayResponse
from app.services.internal_callbacks import InternalCallbackService

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.post(
    "/jobs/{jobId}/status",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        200: {"model": StatusCallbackReplayResponse},
        401: {"model": ErrorResponse},
        404: {"model": NoLeakNotFoundError},
        409: {"model": FsmTransitionError | CallbackOrderingError | EventIdPayloadMismatchError},
        204: {"description": "Status updated"},
    },
)
async def post_job_status_callback(
    jobId: str,
    payload: StatusCallbackRequest,
    __: Annotated[None, Depends(require_callback_secret)],
    callback_service: Annotated[InternalCallbackService, Depends(get_internal_callback_service)],
) -> Response:
    result = callback_service.process_status_callback(job_id=jobId, payload=payload)
    if result.replayed:
        replay_payload = StatusCallbackReplayResponse(
            job_id=jobId,
            event_id=payload.event_id,
            replayed=True,
            current_status=result.current_status,
            latest_applied_occurred_at=result.latest_applied_occurred_at,
        )
        return JSONResponse(status_code=status.HTTP_200_OK, content=replay_payload.model_dump(mode="json"))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
