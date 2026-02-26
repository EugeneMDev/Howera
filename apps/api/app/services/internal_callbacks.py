"""Internal callback service layer."""

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.job_fsm import ensure_transition
from app.errors import ApiError
from app.repositories.memory import CallbackEventRecord, InMemoryStore
from app.schemas.internal import StatusCallbackRequest
from app.schemas.job import JobStatus


@dataclass(slots=True)
class CallbackProcessResult:
    replayed: bool
    current_status: JobStatus
    latest_applied_occurred_at: datetime | None = None


class InternalCallbackService:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def process_status_callback(self, *, job_id: str, payload: StatusCallbackRequest) -> CallbackProcessResult:
        # Domain boundary: callbacks must target an existing job before state processing.
        job = self._store.get_job_for_internal_callback(job_id)
        if job is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        callback_key = (job_id, payload.event_id)
        existing_event = self._store.callback_events.get(callback_key)
        payload_signature = (
            payload.status,
            payload.occurred_at,
            payload.actor_type,
            payload.artifact_updates,
            payload.failure_code,
            payload.failure_message,
            payload.failed_stage,
            payload.correlation_id,
        )

        if existing_event is not None:
            existing_signature = (
                existing_event.status,
                existing_event.occurred_at,
                existing_event.actor_type,
                existing_event.artifact_updates,
                existing_event.failure_code,
                existing_event.failure_message,
                existing_event.failed_stage,
                existing_event.correlation_id,
            )
            if existing_signature != payload_signature:
                raise ApiError(
                    status_code=409,
                    code="EVENT_ID_PAYLOAD_MISMATCH",
                    message="event_id replay payload differs from first accepted payload.",
                    details={"event_id": payload.event_id},
                )
            latest = self._store.latest_callback_at_by_job.get(job_id)
            return CallbackProcessResult(
                replayed=True,
                current_status=job.status,
                latest_applied_occurred_at=latest,
            )

        latest_applied = self._store.latest_callback_at_by_job.get(job_id)
        if latest_applied is not None and payload.occurred_at <= latest_applied:
            raise ApiError(
                status_code=409,
                code="CALLBACK_OUT_OF_ORDER",
                message="Callback occurred_at must be greater than latest accepted event.",
                details={
                    "latest_applied_occurred_at": latest_applied,
                    "current_status": job.status,
                    "attempted_status": payload.status,
                },
            )

        ensure_transition(job.status, payload.status)
        job.status = payload.status
        job.updated_at = datetime.now(UTC)
        self._store.job_write_count += 1

        self._store.callback_events[callback_key] = CallbackEventRecord(
            job_id=job_id,
            event_id=payload.event_id,
            status=payload.status,
            occurred_at=payload.occurred_at,
            actor_type=payload.actor_type,
            artifact_updates=payload.artifact_updates,
            failure_code=payload.failure_code,
            failure_message=payload.failure_message,
            failed_stage=payload.failed_stage,
            correlation_id=payload.correlation_id,
        )
        self._store.latest_callback_at_by_job[job_id] = payload.occurred_at

        return CallbackProcessResult(
            replayed=False,
            current_status=job.status,
            latest_applied_occurred_at=payload.occurred_at,
        )
