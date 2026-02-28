"""Internal callback service layer."""

from dataclasses import dataclass
from datetime import datetime
import logging

from app.core.logging_safety import safe_log_identifier
from app.errors import ApiError
from app.repositories.memory import CallbackEventRecord, InMemoryStore
from app.schemas.internal import StatusCallbackRequest
from app.schemas.job import JobStatus

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CallbackProcessResult:
    replayed: bool
    current_status: JobStatus
    latest_applied_occurred_at: datetime | None = None


class InternalCallbackService:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def process_status_callback(self, *, job_id: str, payload: StatusCallbackRequest) -> CallbackProcessResult:
        safe_correlation_id = safe_log_identifier(payload.correlation_id, prefix="cid")
        safe_event_id = safe_log_identifier(payload.event_id, prefix="eid")

        # Domain boundary: callbacks must target an existing job before state processing.
        job = self._store.get_job_for_internal_callback(job_id)
        if job is None:
            logger.warning(
                "callback.rejected correlation_id=%s job_id=%s event_id=%s code=RESOURCE_NOT_FOUND",
                safe_correlation_id,
                job_id,
                safe_event_id,
            )
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
                logger.warning(
                    "callback.rejected correlation_id=%s job_id=%s event_id=%s code=EVENT_ID_PAYLOAD_MISMATCH",
                    safe_correlation_id,
                    job_id,
                    safe_event_id,
                )
                raise ApiError(
                    status_code=409,
                    code="EVENT_ID_PAYLOAD_MISMATCH",
                    message="event_id replay payload differs from first accepted payload.",
                    details={"event_id": payload.event_id},
                )
            latest = self._store.latest_callback_at_by_job.get(job_id)
            logger.info(
                "callback.replayed correlation_id=%s job_id=%s event_id=%s current_status=%s",
                safe_correlation_id,
                job_id,
                safe_event_id,
                job.status,
            )
            return CallbackProcessResult(
                replayed=True,
                current_status=job.status,
                latest_applied_occurred_at=latest,
            )

        latest_applied = self._store.latest_callback_at_by_job.get(job_id)
        if latest_applied is not None and payload.occurred_at <= latest_applied:
            logger.warning(
                "callback.rejected correlation_id=%s job_id=%s event_id=%s code=CALLBACK_OUT_OF_ORDER "
                "latest_applied_occurred_at=%s current_status=%s attempted_status=%s",
                safe_correlation_id,
                job_id,
                safe_event_id,
                latest_applied.isoformat(),
                job.status,
                payload.status,
            )
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

        callback_event = CallbackEventRecord(
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
        previous_status = job.status
        try:
            self._store.apply_callback_mutation(
                job=job,
                callback_event=callback_event,
            )
        except ApiError as exc:
            logger.warning(
                "callback.rejected correlation_id=%s job_id=%s event_id=%s code=%s current_status=%s "
                "attempted_status=%s",
                safe_correlation_id,
                job_id,
                safe_event_id,
                exc.payload.code,
                previous_status,
                payload.status,
            )
            raise

        logger.info(
            "callback.applied correlation_id=%s job_id=%s event_id=%s prev_status=%s new_status=%s",
            safe_correlation_id,
            job_id,
            safe_event_id,
            previous_status,
            job.status,
        )

        return CallbackProcessResult(
            replayed=False,
            current_status=job.status,
            latest_applied_occurred_at=payload.occurred_at,
        )
