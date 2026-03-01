"""Job service layer."""

from datetime import UTC, datetime
import logging

from app.core.logging_safety import safe_log_identifier
from app.domain.job_fsm import allowed_next_statuses, ensure_transition
from app.errors import ApiError
from app.repositories.memory import InMemoryStore, JobRecord
from app.schemas.job import (
    ArtifactManifest,
    ConfirmUploadResponse,
    Job,
    JobStatus,
    RetryJobResponse,
    RunJobResponse,
    TranscriptPage,
    TranscriptSegment,
)

logger = logging.getLogger(__name__)

_ACTIVE_PIPELINE_STATUSES: set[JobStatus] = {
    JobStatus.AUDIO_EXTRACTING,
    JobStatus.TRANSCRIBING,
    JobStatus.GENERATING,
    JobStatus.REGENERATING,
    JobStatus.EXPORTING,
}
_RETRY_ATTEMPTED_STATUS = JobStatus.REGENERATING
_TRANSCRIPT_LIMIT_DEFAULT = 200
_TRANSCRIPT_LIMIT_MIN = 1
_TRANSCRIPT_LIMIT_MAX = 500
_TRANSCRIPT_READABLE_STATUSES: set[JobStatus] = {
    JobStatus.TRANSCRIPT_READY,
    JobStatus.GENERATING,
    JobStatus.DRAFT_READY,
    JobStatus.EDITING,
    JobStatus.EXPORTING,
    JobStatus.DONE,
    JobStatus.FAILED,
}


class JobService:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def create_job(self, *, owner_id: str, project_id: str) -> Job:
        project = self._store.get_project_for_owner(owner_id=owner_id, project_id=project_id)
        if project is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        record = self._store.create_job(owner_id=owner_id, project_id=project_id)
        return self._to_job(record)

    def get_job(self, *, owner_id: str, job_id: str) -> Job:
        record = self._store.get_job_for_owner(owner_id=owner_id, job_id=job_id)
        if record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        return self._to_job(record)

    def confirm_upload(self, *, owner_id: str, job_id: str, video_uri: str) -> ConfirmUploadResponse:
        record = self._store.get_job_for_owner(owner_id=owner_id, job_id=job_id)
        if record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        current_video_uri = record.manifest.video_uri if record.manifest else None
        if current_video_uri is not None:
            if current_video_uri == video_uri:
                return ConfirmUploadResponse(job=self._to_job(record), replayed=True)
            raise ApiError(
                status_code=409,
                code="VIDEO_URI_CONFLICT",
                message="A different video_uri is already confirmed for this job.",
                details={
                    "current_video_uri": current_video_uri,
                    "submitted_video_uri": video_uri,
                },
            )

        self._store.transition_job_status(job=record, new_status=JobStatus.UPLOADED)
        existing_manifest = record.manifest or ArtifactManifest()
        record.manifest = ArtifactManifest(
            video_uri=video_uri,
            audio_uri=existing_manifest.audio_uri,
            transcript_uri=existing_manifest.transcript_uri,
            draft_uri=existing_manifest.draft_uri,
            exports=existing_manifest.exports,
        )

        return ConfirmUploadResponse(job=self._to_job(record), replayed=False)

    def run_job(self, *, owner_id: str, job_id: str) -> RunJobResponse:
        record = self._store.get_job_for_owner(owner_id=owner_id, job_id=job_id)
        if record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        safe_job_id = safe_log_identifier(record.id, prefix="jid")
        existing_dispatch = self._store.get_dispatch_for_job(record.id)
        if existing_dispatch is not None and existing_dispatch.dispatch_type == "run":
            safe_dispatch_id = safe_log_identifier(existing_dispatch.dispatch_id, prefix="did")
            logger.info(
                "run.replayed job_id=%s dispatch_id=%s status=%s",
                safe_job_id,
                safe_dispatch_id,
                record.status,
            )
            return RunJobResponse(
                job_id=record.id,
                status=record.status,
                dispatch_id=existing_dispatch.dispatch_id,
                replayed=True,
            )

        # Run start is explicitly gated to UPLOADED; in-progress states are replay-only via dispatch record.
        if record.status is not JobStatus.UPLOADED:
            # Route through canonical FSM validation so terminal states return FSM_TERMINAL_IMMUTABLE.
            ensure_transition(record.status, JobStatus.AUDIO_EXTRACTING)
            # If ensure_transition returns here, this is the equal-state case (AUDIO_EXTRACTING -> AUDIO_EXTRACTING),
            # which run treats as invalid unless backed by an existing dispatch replay record.
            raise ApiError(
                status_code=409,
                code="FSM_TRANSITION_INVALID",
                message="Invalid status transition",
                details={
                    "current_status": record.status,
                    "attempted_status": JobStatus.AUDIO_EXTRACTING,
                    "allowed_next_statuses": allowed_next_statuses(record.status),
                },
            )

        manifest = record.manifest or ArtifactManifest()
        video_uri = (manifest.video_uri or "").strip()
        if not video_uri:
            raise ApiError(
                status_code=409,
                code="FSM_TRANSITION_INVALID",
                message="Invalid status transition",
                details={
                    "current_status": record.status,
                    "attempted_status": JobStatus.AUDIO_EXTRACTING,
                    "allowed_next_statuses": allowed_next_statuses(record.status),
                },
            )

        payload = {
            "job_id": record.id,
            "project_id": record.project_id,
            "video_uri": video_uri,
            "callback_url": f"/api/v1/internal/jobs/{record.id}/status",
        }

        try:
            dispatch = self._store.create_dispatch_for_job(job_id=record.id, payload=payload)
        except RuntimeError as exc:
            logger.warning(
                "run.dispatch_failed job_id=%s code=ORCHESTRATOR_DISPATCH_FAILED reason=%s",
                safe_job_id,
                type(exc).__name__,
            )
            raise ApiError(
                status_code=502,
                code="ORCHESTRATOR_DISPATCH_FAILED",
                message="Failed to dispatch workflow execution",
            ) from exc

        self._store.transition_job_status(job=record, new_status=JobStatus.AUDIO_EXTRACTING)

        safe_dispatch_id = safe_log_identifier(dispatch.dispatch_id, prefix="did")
        logger.info(
            "run.dispatched job_id=%s dispatch_id=%s status=%s",
            safe_job_id,
            safe_dispatch_id,
            record.status,
        )

        return RunJobResponse(
            job_id=record.id,
            status=record.status,
            dispatch_id=dispatch.dispatch_id,
            replayed=False,
        )

    def retry_job(
        self,
        *,
        owner_id: str,
        job_id: str,
        model_profile: str,
        client_request_id: str,
    ) -> RetryJobResponse:
        record = self._store.get_job_for_owner(owner_id=owner_id, job_id=job_id)
        if record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        safe_job_id = safe_log_identifier(record.id, prefix="jid")
        normalized_model_profile = self._normalize_model_profile(model_profile=model_profile, current_status=record.status)

        existing_retry_request = self._store.get_retry_request(
            job_id=record.id,
            client_request_id=client_request_id,
        )
        if existing_retry_request is not None:
            replay_signature = self._build_retry_payload_signature(
                model_profile=normalized_model_profile,
                resume_from_status=existing_retry_request.resume_from_status,
                checkpoint_ref=existing_retry_request.checkpoint_ref,
            )
            if existing_retry_request.payload_signature == replay_signature:
                safe_dispatch_id = safe_log_identifier(existing_retry_request.dispatch_id, prefix="did")
                logger.info(
                    "retry.replayed job_id=%s dispatch_id=%s status=%s",
                    safe_job_id,
                    safe_dispatch_id,
                    record.status,
                )
                return RetryJobResponse(
                    job_id=record.id,
                    status=record.status,
                    resume_from_status=existing_retry_request.resume_from_status,
                    checkpoint_ref=existing_retry_request.checkpoint_ref,
                    model_profile=existing_retry_request.model_profile,
                    dispatch_id=existing_retry_request.dispatch_id,
                    replayed=True,
                )
            self._raise_job_already_running(record.status)

        existing_dispatch = self._store.get_dispatch_for_job(record.id)
        if record.status in _ACTIVE_PIPELINE_STATUSES:
            self._raise_job_already_running(record.status)
        if existing_dispatch is not None and record.status is JobStatus.FAILED and existing_dispatch.dispatch_type == "retry":
            self._raise_job_already_running(record.status)

        if record.status is not JobStatus.FAILED:
            self._raise_retry_not_allowed(record.status)

        resume_from_status, checkpoint_ref = self._resolve_retry_checkpoint(record=record)
        payload_signature = self._build_retry_payload_signature(
            model_profile=normalized_model_profile,
            resume_from_status=resume_from_status,
            checkpoint_ref=checkpoint_ref,
        )

        manifest = record.manifest or ArtifactManifest()
        video_uri = (manifest.video_uri or "").strip()
        if not video_uri:
            self._raise_retry_not_allowed(record.status)

        payload = {
            "job_id": record.id,
            "project_id": record.project_id,
            "video_uri": video_uri,
            "callback_url": f"/api/v1/internal/jobs/{record.id}/status",
            "resume_from_status": resume_from_status.value,
            "checkpoint_ref": checkpoint_ref,
            "model_profile": normalized_model_profile,
        }

        try:
            dispatch = self._store.create_dispatch_for_job(
                job_id=record.id,
                payload=payload,
                dispatch_type="retry",
            )
        except RuntimeError as exc:
            logger.warning(
                "retry.dispatch_failed job_id=%s code=ORCHESTRATOR_DISPATCH_FAILED reason=%s",
                safe_job_id,
                type(exc).__name__,
            )
            raise ApiError(
                status_code=502,
                code="ORCHESTRATOR_DISPATCH_FAILED",
                message="Failed to dispatch workflow execution",
            ) from exc

        self._store.persist_retry_metadata(
            job=record,
            client_request_id=client_request_id,
            payload_signature=payload_signature,
            resume_from_status=resume_from_status,
            checkpoint_ref=checkpoint_ref,
            model_profile=normalized_model_profile,
            dispatch_id=dispatch.dispatch_id,
        )

        safe_dispatch_id = safe_log_identifier(dispatch.dispatch_id, prefix="did")
        logger.info(
            "retry.dispatched job_id=%s dispatch_id=%s status=%s resume_from_status=%s model_profile=%s",
            safe_job_id,
            safe_dispatch_id,
            record.status,
            resume_from_status,
            normalized_model_profile,
        )

        return RetryJobResponse(
            job_id=record.id,
            status=record.status,
            resume_from_status=resume_from_status,
            checkpoint_ref=checkpoint_ref,
            model_profile=normalized_model_profile,
            dispatch_id=dispatch.dispatch_id,
            replayed=False,
        )

    def cancel_job(self, *, owner_id: str, job_id: str, correlation_id: str) -> Job:
        record = self._store.get_job_for_owner(owner_id=owner_id, job_id=job_id)
        if record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        safe_job_id = safe_log_identifier(record.id, prefix="jid")
        safe_correlation_id = safe_log_identifier(correlation_id, prefix="cid")
        previous_status = record.status
        occurred_at = datetime.now(UTC)
        try:
            self._store.transition_job_status_with_audit(
                job=record,
                new_status=JobStatus.CANCELLED,
                actor_type="editor",
                occurred_at=occurred_at,
                correlation_id=correlation_id,
            )
        except ApiError as exc:
            logger.warning(
                "cancel.rejected correlation_id=%s job_id=%s code=%s current_status=%s attempted_status=%s",
                safe_correlation_id,
                safe_job_id,
                exc.payload.code,
                previous_status,
                JobStatus.CANCELLED,
            )
            raise

        logger.info(
            "cancel.applied correlation_id=%s job_id=%s prev_status=%s new_status=%s",
            safe_correlation_id,
            safe_job_id,
            previous_status,
            record.status,
        )
        self._store.delete_dispatch_for_job(record.id)
        return self._to_job(record)

    def get_transcript(
        self,
        *,
        owner_id: str,
        job_id: str,
        limit: int,
        cursor: str | None,
    ) -> TranscriptPage:
        record = self._store.get_job_for_owner(owner_id=owner_id, job_id=job_id)
        if record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        if record.status not in _TRANSCRIPT_READABLE_STATUSES:
            raise ApiError(
                status_code=409,
                code="TRANSCRIPT_NOT_READY",
                message="Transcript is not available for this job state.",
                details={"current_status": record.status},
            )
        if limit < _TRANSCRIPT_LIMIT_MIN or limit > _TRANSCRIPT_LIMIT_MAX:
            raise ApiError(
                status_code=409,
                code="VALIDATION_ERROR",
                message="Invalid transcript query parameters",
                details={
                    "limit": limit,
                    "min_limit": _TRANSCRIPT_LIMIT_MIN,
                    "max_limit": _TRANSCRIPT_LIMIT_MAX,
                },
            )

        ordered_segments = sorted(
            self._store.list_transcript_segments_for_job(job_id=record.id),
            key=lambda segment: (segment.start_ms, segment.end_ms, segment.text),
        )
        cursor_index = self._parse_transcript_cursor(cursor=cursor, total=len(ordered_segments))
        items, next_cursor = self._paginate_transcript_segments(
            segments=ordered_segments,
            limit=limit,
            cursor_index=cursor_index,
        )
        return TranscriptPage(items=items, limit=limit, next_cursor=next_cursor)

    @staticmethod
    def _build_retry_payload_signature(
        *,
        model_profile: str,
        resume_from_status: JobStatus,
        checkpoint_ref: str,
    ) -> str:
        return "|".join((model_profile, resume_from_status.value, checkpoint_ref))

    @staticmethod
    def _normalize_model_profile(*, model_profile: str, current_status: JobStatus) -> str:
        normalized = model_profile.strip()
        if normalized:
            return normalized
        raise ApiError(
            status_code=409,
            code="RETRY_NOT_ALLOWED_STATE",
            message="Retry request rejected by model profile policy.",
            details={
                "current_status": current_status,
                "attempted_status": _RETRY_ATTEMPTED_STATUS,
            },
        )

    @staticmethod
    def _resolve_retry_checkpoint(*, record: JobRecord) -> tuple[JobStatus, str]:
        manifest = record.manifest or ArtifactManifest()
        if manifest.draft_uri:
            return JobStatus.DRAFT_READY, manifest.draft_uri
        if manifest.transcript_uri:
            return JobStatus.TRANSCRIPT_READY, manifest.transcript_uri
        if manifest.audio_uri:
            return JobStatus.AUDIO_READY, manifest.audio_uri
        video_uri = (manifest.video_uri or "").strip()
        if video_uri:
            return JobStatus.UPLOADED, video_uri
        raise ApiError(
            status_code=409,
            code="RETRY_NOT_ALLOWED_STATE",
            message="Retry requires a persisted checkpoint artifact.",
            details={
                "current_status": record.status,
                "attempted_status": _RETRY_ATTEMPTED_STATUS,
            },
        )

    @staticmethod
    def _raise_retry_not_allowed(current_status: JobStatus) -> None:
        raise ApiError(
            status_code=409,
            code="RETRY_NOT_ALLOWED_STATE",
            message="Retry is allowed only from FAILED.",
            details={
                "current_status": current_status,
                "attempted_status": _RETRY_ATTEMPTED_STATUS,
            },
        )

    @staticmethod
    def _raise_job_already_running(current_status: JobStatus) -> None:
        raise ApiError(
            status_code=409,
            code="JOB_ALREADY_RUNNING",
            message="Job already has an active dispatch.",
            details={"current_status": current_status},
        )

    @staticmethod
    def _parse_transcript_cursor(*, cursor: str | None, total: int) -> int:
        if cursor is None:
            return 0
        normalized = cursor.strip()
        if not normalized:
            return 0
        if not normalized.isdigit():
            return 0
        parsed = int(normalized)
        if parsed < 0:
            return 0
        if parsed > total:
            return total
        return parsed

    @staticmethod
    def _paginate_transcript_segments(
        *,
        segments: list[TranscriptSegment],
        limit: int,
        cursor_index: int,
    ) -> tuple[list[TranscriptSegment], str | None]:
        start = max(0, cursor_index)
        end = min(start + limit, len(segments))
        items = segments[start:end]
        next_cursor = str(end) if end < len(segments) else None
        return items, next_cursor

    @staticmethod
    def _to_job(record: JobRecord) -> Job:
        return Job(
            id=record.id,
            project_id=record.project_id,
            status=record.status,
            manifest=record.manifest,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
