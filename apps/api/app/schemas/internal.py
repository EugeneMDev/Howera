"""Internal callback schemas."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.job import JobStatus


class StatusCallbackRequest(BaseModel):
    event_id: str
    status: JobStatus
    occurred_at: datetime
    correlation_id: str


class StatusCallbackReplayResponse(BaseModel):
    job_id: str
    event_id: str
    replayed: bool
    current_status: JobStatus | None = None
    latest_applied_occurred_at: datetime | None = None
