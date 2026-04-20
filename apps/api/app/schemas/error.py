"""API error response schemas."""

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel

from app.schemas.job import JobStatus


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class Error(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class TransitionErrorDetails(BaseModel):
    current_status: JobStatus
    attempted_status: JobStatus
    allowed_next_statuses: list[JobStatus] | None = None


class FsmTransitionError(BaseModel):
    code: Literal["FSM_TRANSITION_INVALID", "FSM_TERMINAL_IMMUTABLE"]
    message: str
    details: TransitionErrorDetails


class VideoUriConflictErrorDetails(BaseModel):
    current_video_uri: str
    submitted_video_uri: str


class VideoUriConflictError(BaseModel):
    code: Literal["VIDEO_URI_CONFLICT"]
    message: str
    details: VideoUriConflictErrorDetails


class VersionConflictErrorDetails(BaseModel):
    base_version: int
    current_version: int


class VersionConflictError(BaseModel):
    code: Literal["VERSION_CONFLICT"]
    message: str
    details: VersionConflictErrorDetails


class CallbackOrderingErrorDetails(BaseModel):
    latest_applied_occurred_at: datetime
    current_status: JobStatus
    attempted_status: JobStatus


class CallbackOrderingError(BaseModel):
    code: Literal["CALLBACK_OUT_OF_ORDER"]
    message: str
    details: CallbackOrderingErrorDetails


class EventIdPayloadMismatchErrorDetails(BaseModel):
    event_id: str


class EventIdPayloadMismatchError(BaseModel):
    code: Literal["EVENT_ID_PAYLOAD_MISMATCH"]
    message: str
    details: EventIdPayloadMismatchErrorDetails


class NoLeakNotFoundError(BaseModel):
    code: Literal["RESOURCE_NOT_FOUND"]
    message: str


class UpstreamDispatchError(BaseModel):
    code: Literal["ORCHESTRATOR_DISPATCH_FAILED"]
    message: str
    details: dict[str, Any] | None = None


class RetryStateConflictErrorDetails(BaseModel):
    current_status: JobStatus
    attempted_status: JobStatus | None = None


class RetryStateConflictError(BaseModel):
    code: Literal["RETRY_NOT_ALLOWED_STATE", "JOB_ALREADY_RUNNING"]
    message: str
    details: RetryStateConflictErrorDetails
