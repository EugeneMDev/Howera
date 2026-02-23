"""Internal callback routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.routes.dependencies import require_callback_secret
from app.schemas.error import ErrorResponse
from app.schemas.internal import StatusCallbackRequest, StatusCallbackReplayResponse

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.post(
    "/jobs/{jobId}/status",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        200: {"model": StatusCallbackReplayResponse},
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        204: {"description": "Status updated"},
    },
)
async def post_job_status_callback(
    _: StatusCallbackRequest,
    __: Annotated[None, Depends(require_callback_secret)],
) -> Response:
    # Story 1.1 keeps this path on callback-secret auth, not bearer auth.
    return Response(status_code=status.HTTP_204_NO_CONTENT)
