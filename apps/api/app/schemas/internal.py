"""Internal callback schemas."""

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel

from app.schemas.job import JobStatus


class StatusCallbackRequest(BaseModel):
    event_id: str
    status: JobStatus
    occurred_at: datetime
    actor_type: Literal["orchestrator", "system"] | None = None
    artifact_updates: dict[str, Any] | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    failed_stage: str | None = None
    correlation_id: str


class StatusCallbackReplayResponse(BaseModel):
    job_id: str
    event_id: str
    replayed: bool
    current_status: JobStatus | None = None
    latest_applied_occurred_at: datetime | None = None
