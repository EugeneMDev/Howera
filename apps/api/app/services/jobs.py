"""Job service layer."""

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
import re

from app.core.logging_safety import safe_log_identifier
from app.domain.job_fsm import allowed_next_statuses, ensure_transition
from app.errors import ApiError
from app.repositories.memory import (
    CustomUploadRecord,
    ExportRecord,
    InMemoryStore,
    JobRecord,
    ScreenshotAnnotationResultRecord,
    ScreenshotAnchorRecord,
    ScreenshotAssetRecord,
    ScreenshotTaskRecord,
)
from app.schemas.instruction import CharRange
from app.schemas.job import (
    AnchorAddress,
    AnchorAddressType,
    AnchorResolution,
    AnchorResolutionState,
    AnnotateScreenshotRequest,
    AnnotateScreenshotResponse,
    AttachUploadedAssetRequest,
    ArtifactManifest,
    ConfirmCustomUploadRequest,
    ConfirmCustomUploadResponse,
    CreateCustomUploadRequest,
    CreateExportRequest,
    ConfirmUploadResponse,
    CustomUploadTicket,
    Export,
    ExportAnchorBinding,
    ExportStatus,
    ExportProvenance,
    Job,
    JobStatus,
    RetryJobResponse,
    RunJobResponse,
    ScreenshotAnchor,
    ScreenshotAnchorCreateRequest,
    ScreenshotAsset,
    ScreenshotAssetKind,
    SoftDeleteScreenshotAssetResponse,
    ScreenshotExtractionRequest,
    ScreenshotMimeType,
    ScreenshotReplaceRequest,
    ScreenshotTask,
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
_BLOCK_ID_PATTERN = re.compile(r"\{#([A-Za-z0-9._:-]+)\}")


@dataclass(slots=True)
class ScreenshotExtractionResult:
    task: ScreenshotTask
    replayed: bool


@dataclass(slots=True)
class ExportRequestResult:
    export: Export
    replayed: bool


@dataclass(slots=True)
class ExportExecutionResult:
    export: Export
    replayed: bool


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

    def create_export_request(
        self,
        *,
        owner_id: str,
        job_id: str,
        payload: CreateExportRequest,
    ) -> ExportRequestResult:
        job_record = self._store.get_job_for_owner(owner_id=owner_id, job_id=job_id)
        if job_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        instruction_version = self._resolve_instruction_version_id(payload.instruction_version_id)
        if instruction_version is None:
            self._raise_invalid_export_request()

        instruction_record = self._store.get_instruction_for_owner_job_version(
            owner_id=owner_id,
            job_id=job_record.id,
            version=instruction_version,
        )
        if instruction_record is None:
            self._raise_invalid_export_request()

        normalized_instruction_version_id = str(instruction_record.version)
        anchor_bindings = self._store.list_export_anchor_bindings(
            owner_id=owner_id,
            job_id=job_record.id,
            instruction_id=instruction_record.instruction_id,
            instruction_version_id=normalized_instruction_version_id,
        )
        screenshot_set_hash = self._store.build_export_screenshot_set_hash(bindings=anchor_bindings)
        identity_key = self._store.build_export_identity_key(
            instruction_version_id=normalized_instruction_version_id,
            export_format=payload.format,
            screenshot_set_hash=screenshot_set_hash,
        )
        instruction_snapshot_id = f"{instruction_record.instruction_id}:v{normalized_instruction_version_id}"
        model_profile_id = instruction_record.model_profile_id or f"{instruction_snapshot_id}:model-profile"
        prompt_template_id = instruction_record.prompt_template_id or f"{instruction_snapshot_id}:prompt-template"

        provenance = ExportProvenance(
            instruction_version_id=normalized_instruction_version_id,
            screenshot_set_hash=screenshot_set_hash,
            anchors=[
                ExportAnchorBinding(
                    anchor_id=binding.anchor_id,
                    active_asset_id=binding.active_asset_id,
                    rendered_asset_id=binding.rendered_asset_id,
                )
                for binding in anchor_bindings
            ],
            instruction_snapshot_id=instruction_snapshot_id,
            model_profile_id=model_profile_id,
            prompt_template_id=prompt_template_id,
            prompt_params_ref=instruction_record.prompt_params_ref,
            generated_at=datetime.now(UTC),
        )
        export_record, replayed = self._store.create_export_request(
            owner_id=owner_id,
            job_id=job_record.id,
            export_format=payload.format,
            instruction_version_id=normalized_instruction_version_id,
            identity_key=identity_key,
            screenshot_set_hash=screenshot_set_hash,
            provenance=provenance,
        )
        return ExportRequestResult(export=self._to_export(export_record), replayed=replayed)

    def get_export(
        self,
        *,
        owner_id: str,
        export_id: str,
    ) -> Export:
        export_record = self._store.get_export_for_owner(owner_id=owner_id, export_id=export_id)
        if export_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        export = self._to_export(export_record)
        if export.status is not ExportStatus.SUCCEEDED:
            return export.model_copy(
                update={
                    "download_url": None,
                    "download_url_expires_at": None,
                }
            )
        download_url, download_url_expires_at = self._store.issue_export_download_url(
            owner_id=owner_id,
            export_id=export_record.export_id,
        )
        return export.model_copy(
            update={
                "download_url": download_url,
                "download_url_expires_at": download_url_expires_at,
            }
        )

    def start_export_execution(
        self,
        *,
        owner_id: str,
        export_id: str,
    ) -> ExportExecutionResult:
        export_record, replayed = self._store.start_export_execution(owner_id=owner_id, export_id=export_id)
        return ExportExecutionResult(export=self._to_export(export_record), replayed=replayed)

    def complete_export_success(
        self,
        *,
        owner_id: str,
        export_id: str,
    ) -> ExportExecutionResult:
        export_record, replayed = self._store.complete_export_success(owner_id=owner_id, export_id=export_id)
        return ExportExecutionResult(export=self._to_export(export_record), replayed=replayed)

    def complete_export_failure(
        self,
        *,
        owner_id: str,
        export_id: str,
    ) -> ExportExecutionResult:
        export_record, replayed = self._store.complete_export_failure(owner_id=owner_id, export_id=export_id)
        return ExportExecutionResult(export=self._to_export(export_record), replayed=replayed)

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

    def request_screenshot_extraction(
        self,
        *,
        owner_id: str,
        job_id: str,
        payload: ScreenshotExtractionRequest,
    ) -> ScreenshotExtractionResult:
        job_record = self._store.get_job_for_owner(owner_id=owner_id, job_id=job_id)
        if job_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        instruction_version = self._resolve_instruction_version_id(payload.instruction_version_id)
        if instruction_version is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        instruction_record = self._store.get_instruction_for_owner(
            owner_id=owner_id,
            instruction_id=payload.instruction_id,
            version=instruction_version,
        )
        if instruction_record is None or instruction_record.job_id != job_record.id:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        normalized_payload = payload.model_copy(update={"instruction_version_id": str(instruction_record.version)})
        try:
            task_record, replayed = self._store.create_screenshot_extraction_task(
                owner_id=owner_id,
                job_id=job_record.id,
                payload=normalized_payload,
            )
        except ValueError as exc:
            message = str(exc)
            if "idempotency_key" in message:
                raise ApiError(
                    status_code=400,
                    code="VALIDATION_ERROR",
                    message="Duplicate idempotency_key payload differs from first accepted request.",
                ) from exc
            raise ApiError(
                status_code=400,
                code="VALIDATION_ERROR",
                message="Invalid extraction payload",
            ) from exc

        return ScreenshotExtractionResult(
            task=self._to_screenshot_task(task_record),
            replayed=replayed,
        )

    def create_screenshot_anchor(
        self,
        *,
        owner_id: str,
        instruction_id: str,
        payload: ScreenshotAnchorCreateRequest,
    ) -> ScreenshotAnchor:
        instruction_version = self._resolve_instruction_version_id(payload.instruction_version_id)
        if instruction_version is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        instruction_record = self._store.get_instruction_for_owner(
            owner_id=owner_id,
            instruction_id=instruction_id,
            version=instruction_version,
        )
        if instruction_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        addressing_type, block_id, char_range, strategy = self._normalize_anchor_addressing(payload.addressing)
        self._validate_anchor_addressing_against_instruction(
            addressing_type=addressing_type,
            block_id=block_id,
            char_range=char_range,
            instruction_markdown=instruction_record.markdown,
        )
        anchor_record = self._store.create_screenshot_anchor(
            owner_id=owner_id,
            job_id=instruction_record.job_id,
            instruction_id=instruction_id,
            instruction_version_id=str(instruction_record.version),
            addressing_type=addressing_type.value,
            addressing_block_id=block_id,
            addressing_char_range=char_range,
            addressing_strategy=strategy,
        )
        return self._to_screenshot_anchor(anchor_record, assets=[])

    def list_screenshot_anchors(
        self,
        *,
        owner_id: str,
        instruction_id: str,
        instruction_version_id: str | None,
        include_deleted_assets: bool,
    ) -> list[ScreenshotAnchor]:
        instruction_record = self._store.get_instruction_for_owner(
            owner_id=owner_id,
            instruction_id=instruction_id,
            version=None,
        )
        if instruction_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        normalized_instruction_version_id: str | None = None
        if instruction_version_id is not None:
            parsed_version = self._resolve_instruction_version_id(instruction_version_id)
            if parsed_version is None:
                raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")
            selected_instruction = self._store.get_instruction_for_owner(
                owner_id=owner_id,
                instruction_id=instruction_id,
                version=parsed_version,
            )
            if selected_instruction is None or selected_instruction.job_id != instruction_record.job_id:
                raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")
            normalized_instruction_version_id = str(selected_instruction.version)

        anchors = self._store.list_screenshot_anchors_for_owner_instruction(
            owner_id=owner_id,
            instruction_id=instruction_id,
            instruction_version_id=normalized_instruction_version_id,
        )

        results: list[ScreenshotAnchor] = []
        for anchor in anchors:
            assets = self._store.list_screenshot_assets_for_owner_anchor(
                owner_id=owner_id,
                anchor_id=anchor.anchor_id,
                include_deleted_assets=include_deleted_assets,
            )
            results.append(self._to_screenshot_anchor(anchor, assets=assets))
        return results

    def get_screenshot_anchor(
        self,
        *,
        owner_id: str,
        anchor_id: str,
        target_instruction_version_id: str | None,
    ) -> ScreenshotAnchor:
        anchor_record = self._store.get_screenshot_anchor_for_owner(owner_id=owner_id, anchor_id=anchor_id)
        if anchor_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        assets = self._store.list_screenshot_assets_for_owner_anchor(
            owner_id=owner_id,
            anchor_id=anchor_record.anchor_id,
            include_deleted_assets=True,
        )

        resolution: AnchorResolution | None = None
        if target_instruction_version_id is not None:
            parsed_target_version = self._resolve_instruction_version_id(target_instruction_version_id)
            if parsed_target_version is None:
                raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

            target_instruction = self._store.get_instruction_for_owner(
                owner_id=owner_id,
                instruction_id=anchor_record.instruction_id,
                version=parsed_target_version,
            )
            if target_instruction is None or target_instruction.job_id != anchor_record.job_id:
                raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

            source_version = self._resolve_instruction_version_id(anchor_record.instruction_version_id)
            if source_version is None:
                raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")
            source_instruction = self._store.get_instruction_for_owner(
                owner_id=owner_id,
                instruction_id=anchor_record.instruction_id,
                version=source_version,
            )
            if source_instruction is None or source_instruction.job_id != anchor_record.job_id:
                raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

            resolution = self._resolve_anchor_resolution(
                anchor=anchor_record,
                source_markdown=source_instruction.markdown,
                source_instruction_version_id=str(source_instruction.version),
                target_markdown=target_instruction.markdown,
                target_instruction_version_id=str(target_instruction.version),
            )

        return self._to_screenshot_anchor(anchor_record, assets=assets, resolution=resolution)

    def request_screenshot_replacement(
        self,
        *,
        owner_id: str,
        anchor_id: str,
        payload: ScreenshotReplaceRequest,
    ) -> ScreenshotExtractionResult:
        anchor_record = self._store.get_screenshot_anchor_for_owner(owner_id=owner_id, anchor_id=anchor_id)
        if anchor_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        instruction_version = self._resolve_instruction_version_id(payload.instruction_version_id)
        if instruction_version is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        anchor_instruction_version = self._resolve_instruction_version_id(anchor_record.instruction_version_id)
        if anchor_instruction_version is None or instruction_version != anchor_instruction_version:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        instruction_record = self._store.get_instruction_for_owner(
            owner_id=owner_id,
            instruction_id=anchor_record.instruction_id,
            version=instruction_version,
        )
        if instruction_record is None or instruction_record.job_id != anchor_record.job_id:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        if anchor_record.active_asset_id is None:
            raise ApiError(
                status_code=400,
                code="VALIDATION_ERROR",
                message="Invalid replacement payload",
            )

        normalized_payload = payload.model_copy(update={"instruction_version_id": str(instruction_record.version)})
        try:
            task_record, replayed = self._store.create_screenshot_replace_task(
                owner_id=owner_id,
                anchor_id=anchor_record.anchor_id,
                job_id=anchor_record.job_id,
                instruction_id=anchor_record.instruction_id,
                payload=normalized_payload,
            )
        except ValueError as exc:
            message = str(exc)
            if "idempotency_key" in message:
                raise ApiError(
                    status_code=400,
                    code="VALIDATION_ERROR",
                    message="Duplicate idempotency_key payload differs from first accepted request.",
                ) from exc
            raise ApiError(
                status_code=400,
                code="VALIDATION_ERROR",
                message="Invalid replacement payload",
            ) from exc

        return ScreenshotExtractionResult(
            task=self._to_screenshot_task(task_record),
            replayed=replayed,
        )

    def get_screenshot_task(
        self,
        *,
        owner_id: str,
        task_id: str,
    ) -> ScreenshotTask:
        task_record = self._store.get_screenshot_task_for_owner(owner_id=owner_id, task_id=task_id)
        if task_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")
        return self._to_screenshot_task(task_record)

    def soft_delete_screenshot_asset(
        self,
        *,
        owner_id: str,
        anchor_id: str,
        asset_id: str,
    ) -> SoftDeleteScreenshotAssetResponse:
        try:
            anchor_record, asset_record, _ = self._store.soft_delete_screenshot_asset(
                owner_id=owner_id,
                anchor_id=anchor_id,
                asset_id=asset_id,
            )
        except ValueError as exc:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found") from exc

        return SoftDeleteScreenshotAssetResponse(
            anchor_id=anchor_record.anchor_id,
            deleted_asset_id=asset_record.asset_id,
            active_asset_id=anchor_record.active_asset_id,
        )

    def create_custom_upload_ticket(
        self,
        *,
        owner_id: str,
        job_id: str,
        payload: CreateCustomUploadRequest,
    ) -> CustomUploadTicket:
        job_record = self._store.get_job_for_owner(owner_id=owner_id, job_id=job_id)
        if job_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        try:
            ticket_record = self._store.create_custom_upload_ticket(
                owner_id=owner_id,
                job_id=job_record.id,
                payload=payload,
            )
        except ValueError as exc:
            # Keep this endpoint contract-safe (201/404 only).
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found") from exc
        return self._to_custom_upload_ticket(ticket_record)

    def confirm_custom_upload(
        self,
        *,
        owner_id: str,
        job_id: str,
        upload_id: str,
        payload: ConfirmCustomUploadRequest,
    ) -> ConfirmCustomUploadResponse:
        job_record = self._store.get_job_for_owner(owner_id=owner_id, job_id=job_id)
        if job_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        try:
            asset_record, _ = self._store.confirm_custom_upload(
                owner_id=owner_id,
                job_id=job_record.id,
                upload_id=upload_id,
                payload=payload,
            )
        except ValueError as exc:
            # Keep this endpoint contract-safe (200/404 only).
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found") from exc
        return ConfirmCustomUploadResponse(asset=self._to_screenshot_asset(asset_record))

    def attach_uploaded_asset(
        self,
        *,
        owner_id: str,
        anchor_id: str,
        payload: AttachUploadedAssetRequest,
    ) -> ScreenshotAnchor:
        anchor_record = self._store.get_screenshot_anchor_for_owner(owner_id=owner_id, anchor_id=anchor_id)
        if anchor_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        instruction_version = self._resolve_instruction_version_id(payload.instruction_version_id)
        if instruction_version is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        instruction_record = self._store.get_instruction_for_owner(
            owner_id=owner_id,
            instruction_id=anchor_record.instruction_id,
            version=instruction_version,
        )
        if instruction_record is None or instruction_record.job_id != anchor_record.job_id:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        normalized_instruction_version_id = str(instruction_record.version)
        payload_signature = self._build_attach_upload_payload_signature(
            upload_id=payload.upload_id,
            instruction_version_id=normalized_instruction_version_id,
        )
        try:
            attached_anchor_record, _ = self._store.attach_confirmed_upload_to_anchor(
                owner_id=owner_id,
                anchor_id=anchor_record.anchor_id,
                instruction_version_id=normalized_instruction_version_id,
                upload_id=payload.upload_id,
                idempotency_key=payload.idempotency_key,
                payload_signature=payload_signature,
            )
        except ValueError as exc:
            # Keep this endpoint contract-safe (200/404 only).
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found") from exc

        return self._to_screenshot_anchor(attached_anchor_record)

    def annotate_screenshot(
        self,
        *,
        owner_id: str,
        anchor_id: str,
        payload: AnnotateScreenshotRequest,
    ) -> AnnotateScreenshotResponse:
        anchor_record = self._store.get_screenshot_anchor_for_owner(owner_id=owner_id, anchor_id=anchor_id)
        if anchor_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        base_asset_record = self._store.get_screenshot_asset_for_owner(owner_id=owner_id, asset_id=payload.base_asset_id)
        if (
            base_asset_record is None
            or base_asset_record.anchor_id != anchor_record.anchor_id
            or base_asset_record.job_id != anchor_record.job_id
            or base_asset_record.is_deleted
        ):
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        operation_payloads = [operation.model_dump(mode="json") for operation in payload.operations]
        try:
            result = self._store.apply_screenshot_annotations(
                owner_id=owner_id,
                anchor_id=anchor_record.anchor_id,
                base_asset_id=payload.base_asset_id,
                operations=operation_payloads,
                idempotency_key=payload.idempotency_key,
            )
        except ValueError as exc:
            message = str(exc)
            if "idempotency_key" in message:
                raise ApiError(
                    status_code=400,
                    code="VALIDATION_ERROR",
                    message="Duplicate idempotency_key payload differs from first accepted request.",
                ) from exc
            if "not found" in message or "linked" in message:
                raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found") from exc
            raise ApiError(
                status_code=400,
                code="VALIDATION_ERROR",
                message="Invalid annotation payload",
            ) from exc
        return self._to_annotate_screenshot_response(result)

    @staticmethod
    def _normalize_anchor_addressing(
        addressing: AnchorAddress,
    ) -> tuple[AnchorAddressType, str | None, CharRange | None, str]:
        if addressing.address_type is AnchorAddressType.BLOCK_ID:
            block_id = (addressing.block_id or "").strip()
            if not block_id or addressing.char_range is not None:
                raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")
            strategy = (addressing.strategy or "").strip() or "block_id_primary"
            return AnchorAddressType.BLOCK_ID, block_id, None, strategy

        if addressing.char_range is None or addressing.block_id is not None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")
        if addressing.char_range.end_offset < addressing.char_range.start_offset:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        strategy = (addressing.strategy or "").strip() or "char_range_fallback"
        return AnchorAddressType.CHAR_RANGE, None, addressing.char_range.model_copy(deep=True), strategy

    @classmethod
    def _validate_anchor_addressing_against_instruction(
        cls,
        *,
        addressing_type: AnchorAddressType,
        block_id: str | None,
        char_range: CharRange | None,
        instruction_markdown: str,
    ) -> None:
        if addressing_type is AnchorAddressType.BLOCK_ID:
            block_ids = cls._extract_block_ids(instruction_markdown)
            if block_id is None or block_id not in block_ids:
                raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")
            return

        if char_range is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")
        markdown_length = len(instruction_markdown)
        if (
            char_range.start_offset < 0
            or char_range.end_offset <= char_range.start_offset
            or char_range.end_offset > markdown_length
        ):
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

    @classmethod
    def _resolve_anchor_resolution(
        cls,
        *,
        anchor: ScreenshotAnchorRecord,
        source_markdown: str,
        source_instruction_version_id: str,
        target_markdown: str,
        target_instruction_version_id: str,
    ) -> AnchorResolution:
        if source_instruction_version_id == target_instruction_version_id:
            return AnchorResolution(
                source_instruction_version_id=source_instruction_version_id,
                target_instruction_version_id=target_instruction_version_id,
                resolution_state=AnchorResolutionState.RETAIN,
                trace={
                    "method": "same_version",
                    "evidence": {
                        "instruction_version_id": source_instruction_version_id,
                    },
                },
            )

        if anchor.addressing_type == AnchorAddressType.BLOCK_ID.value:
            source_block_id = (anchor.addressing_block_id or "").strip()
            source_block_ids = cls._extract_block_ids(source_markdown)
            target_block_ids = cls._extract_block_ids(target_markdown)

            if source_block_id and source_block_id in target_block_ids:
                return AnchorResolution(
                    source_instruction_version_id=source_instruction_version_id,
                    target_instruction_version_id=target_instruction_version_id,
                    resolution_state=AnchorResolutionState.RETAIN,
                    trace={
                        "method": "block_id_match",
                        "evidence": {
                            "source_block_id": source_block_id,
                            "matched_block_id": source_block_id,
                        },
                    },
                )

            if source_block_id and source_block_id in source_block_ids:
                source_index = source_block_ids.index(source_block_id)
                if source_index < len(target_block_ids):
                    remapped_block_id = target_block_ids[source_index]
                    return AnchorResolution(
                        source_instruction_version_id=source_instruction_version_id,
                        target_instruction_version_id=target_instruction_version_id,
                        resolution_state=AnchorResolutionState.REMAP,
                        trace={
                            "method": "block_index_remap",
                            "evidence": {
                                "source_block_id": source_block_id,
                                "source_index": source_index,
                                "remapped_block_id": remapped_block_id,
                            },
                        },
                    )

            return AnchorResolution(
                source_instruction_version_id=source_instruction_version_id,
                target_instruction_version_id=target_instruction_version_id,
                resolution_state=AnchorResolutionState.UNRESOLVED,
                trace={
                    "method": "block_index_remap",
                    "evidence": {
                        "source_block_id": source_block_id,
                        "source_block_ids": source_block_ids,
                        "target_block_ids": target_block_ids,
                    },
                    "reason": "unable_to_map_block_id",
                },
            )

        char_range = anchor.addressing_char_range
        if char_range is None:
            return AnchorResolution(
                source_instruction_version_id=source_instruction_version_id,
                target_instruction_version_id=target_instruction_version_id,
                resolution_state=AnchorResolutionState.UNRESOLVED,
                trace={
                    "method": "char_range_scale",
                    "reason": "missing_source_char_range",
                },
            )

        source_start = char_range.start_offset
        source_end = char_range.end_offset
        target_length = len(target_markdown)
        source_length = len(source_markdown)

        if source_end <= target_length:
            return AnchorResolution(
                source_instruction_version_id=source_instruction_version_id,
                target_instruction_version_id=target_instruction_version_id,
                resolution_state=AnchorResolutionState.RETAIN,
                trace={
                    "method": "char_range_direct",
                    "evidence": {
                        "source_range": {
                            "start_offset": source_start,
                            "end_offset": source_end,
                        },
                    },
                },
            )

        if source_length > 0 and target_length > 0 and source_start <= source_length and source_end <= source_length:
            scale = target_length / source_length
            remapped_start = int(round(source_start * scale))
            remapped_start = max(0, min(remapped_start, target_length - 1))
            remapped_end = int(round(source_end * scale))
            remapped_end = max(remapped_start + 1, min(remapped_end, target_length))
            return AnchorResolution(
                source_instruction_version_id=source_instruction_version_id,
                target_instruction_version_id=target_instruction_version_id,
                resolution_state=AnchorResolutionState.REMAP,
                trace={
                    "method": "char_range_scale",
                    "evidence": {
                        "source_length": source_length,
                        "target_length": target_length,
                        "source_range": {
                            "start_offset": source_start,
                            "end_offset": source_end,
                        },
                        "remapped_range": {
                            "start_offset": remapped_start,
                            "end_offset": remapped_end,
                        },
                    },
                },
            )

        return AnchorResolution(
            source_instruction_version_id=source_instruction_version_id,
            target_instruction_version_id=target_instruction_version_id,
            resolution_state=AnchorResolutionState.UNRESOLVED,
            trace={
                "method": "char_range_scale",
                "evidence": {
                    "source_length": source_length,
                    "target_length": target_length,
                    "source_range": {
                        "start_offset": source_start,
                        "end_offset": source_end,
                    },
                },
                "reason": "unable_to_map_char_range",
            },
        )

    @staticmethod
    def _extract_block_ids(markdown: str) -> list[str]:
        block_ids: list[str] = []
        seen: set[str] = set()
        for match in _BLOCK_ID_PATTERN.finditer(markdown):
            block_id = match.group(1)
            if block_id in seen:
                continue
            seen.add(block_id)
            block_ids.append(block_id)
        return block_ids

    @staticmethod
    def _build_retry_payload_signature(
        *,
        model_profile: str,
        resume_from_status: JobStatus,
        checkpoint_ref: str,
    ) -> str:
        return "|".join((model_profile, resume_from_status.value, checkpoint_ref))

    @staticmethod
    def _build_attach_upload_payload_signature(*, upload_id: str, instruction_version_id: str) -> str:
        payload = {
            "upload_id": upload_id,
            "instruction_version_id": instruction_version_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

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
    def _resolve_instruction_version_id(raw_version_id: str) -> int | None:
        normalized = raw_version_id.strip()
        if not normalized:
            return None
        if normalized.isdigit():
            parsed = int(normalized)
            return parsed if parsed >= 1 else None
        if normalized.startswith("v") and normalized[1:].isdigit():
            parsed = int(normalized[1:])
            return parsed if parsed >= 1 else None
        return None

    @staticmethod
    def _raise_invalid_export_request() -> None:
        raise ApiError(
            status_code=400,
            code="EXPORT_REQUEST_INVALID",
            message="Unsupported format or invalid instruction version.",
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

    @staticmethod
    def _to_screenshot_task(record: ScreenshotTaskRecord) -> ScreenshotTask:
        return ScreenshotTask(
            task_id=record.id,
            operation=record.operation,
            status=record.status,
            anchor_id=record.anchor_id,
            asset_id=record.asset_id,
            failure_code=record.failure_code,
            failure_message=record.failure_message,
        )

    @staticmethod
    def _to_annotate_screenshot_response(record: ScreenshotAnnotationResultRecord) -> AnnotateScreenshotResponse:
        return AnnotateScreenshotResponse(
            anchor_id=record.anchor_id,
            base_asset_id=record.base_asset_id,
            ops_hash=record.ops_hash,
            rendered_asset_id=record.rendered_asset_id,
            active_asset_id=record.active_asset_id,
        )

    @staticmethod
    def _to_custom_upload_ticket(record: CustomUploadRecord) -> CustomUploadTicket:
        return CustomUploadTicket(
            upload_id=record.upload_id,
            upload_url=record.upload_url,
            expires_at=record.expires_at,
            max_size_bytes=record.max_size_bytes,
            allowed_mime_types=[ScreenshotMimeType(item) for item in record.allowed_mime_types],
        )

    @staticmethod
    def _to_export(record: ExportRecord) -> Export:
        return Export(
            id=record.export_id,
            job_id=record.job_id,
            format=record.format,
            status=record.status,
            instruction_version_id=record.instruction_version_id,
            identity_key=record.identity_key,
            screenshot_set_hash=record.screenshot_set_hash,
            provenance=record.provenance.model_copy(deep=True),
            provenance_frozen_at=record.provenance_frozen_at,
            last_audit_event=record.last_audit_event,
            download_url=record.download_url,
            download_url_expires_at=record.download_url_expires_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _to_screenshot_asset(record: ScreenshotAssetRecord) -> ScreenshotAsset:
        return ScreenshotAsset(
            id=record.asset_id,
            anchor_id=record.anchor_id,
            version=record.version,
            kind=ScreenshotAssetKind(record.kind),
            previous_asset_id=record.previous_asset_id,
            image_uri=record.image_uri,
            mime_type=ScreenshotMimeType(record.mime_type),
            width=record.width,
            height=record.height,
            extraction_key=record.extraction_key,
            checksum_sha256=record.checksum_sha256,
            upload_id=record.upload_id,
            ops_hash=record.ops_hash,
            rendered_from_asset_id=record.rendered_from_asset_id,
            is_deleted=record.is_deleted,
            created_at=record.created_at,
        )

    @classmethod
    def _to_screenshot_anchor(
        cls,
        record: ScreenshotAnchorRecord,
        *,
        assets: list[ScreenshotAssetRecord] | None = None,
        resolution: AnchorResolution | None = None,
    ) -> ScreenshotAnchor:
        return ScreenshotAnchor(
            id=record.anchor_id,
            instruction_id=record.instruction_id,
            instruction_version_id=record.instruction_version_id,
            addressing=AnchorAddress(
                address_type=AnchorAddressType(record.addressing_type),
                block_id=record.addressing_block_id,
                char_range=record.addressing_char_range.model_copy(deep=True)
                if record.addressing_char_range is not None
                else None,
            strategy=record.addressing_strategy,
            ),
            active_asset_id=record.active_asset_id,
            assets=[cls._to_screenshot_asset(asset) for asset in assets] if assets is not None else None,
            resolution=resolution,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
