"""Job service layer."""

from datetime import UTC, datetime
import logging

from app.core.logging_safety import safe_log_identifier
from app.domain.job_fsm import ensure_transition
from app.errors import ApiError
from app.repositories.memory import InMemoryStore, JobRecord
from app.schemas.job import ArtifactManifest, ConfirmUploadResponse, Job, JobStatus, RunJobResponse

logger = logging.getLogger(__name__)


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

        ensure_transition(record.status, JobStatus.UPLOADED)
        record.status = JobStatus.UPLOADED
        record.updated_at = datetime.now(UTC)
        existing_manifest = record.manifest or ArtifactManifest()
        record.manifest = ArtifactManifest(
            video_uri=video_uri,
            audio_uri=existing_manifest.audio_uri,
            transcript_uri=existing_manifest.transcript_uri,
            draft_uri=existing_manifest.draft_uri,
            exports=existing_manifest.exports,
        )
        self._store.job_write_count += 1

        return ConfirmUploadResponse(job=self._to_job(record), replayed=False)

    def run_job(self, *, owner_id: str, job_id: str) -> RunJobResponse:
        record = self._store.get_job_for_owner(owner_id=owner_id, job_id=job_id)
        if record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        safe_job_id = safe_log_identifier(record.id, prefix="jid")
        existing_dispatch = self._store.get_dispatch_for_job(record.id)
        if existing_dispatch is not None:
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
            raise ApiError(
                status_code=409,
                code="FSM_TRANSITION_INVALID",
                message="Invalid status transition",
                details={
                    "current_status": record.status,
                    "attempted_status": JobStatus.AUDIO_EXTRACTING,
                    "allowed_next_statuses": [],
                },
            )

        ensure_transition(record.status, JobStatus.AUDIO_EXTRACTING)

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
                    "allowed_next_statuses": [],
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

        record.status = JobStatus.AUDIO_EXTRACTING
        record.updated_at = datetime.now(UTC)
        self._store.job_write_count += 1

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
