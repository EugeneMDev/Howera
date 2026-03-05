"""In-memory repositories used by the API scaffold and tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import math
from typing import Any
from typing import Literal
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from pydantic import ValidationError

from app.domain.export_fsm import ensure_export_transition
from app.domain.instruction_validation import validate_instruction_markdown
from app.domain.job_fsm import ensure_transition
from app.errors import ApiError
from app.schemas.instruction import (
    CharRange,
    RegenerateProvenance,
    RegenerateSelection,
    RegenerateTaskStatus,
    ValidationIssue,
    ValidationStatus,
)
from app.schemas.job import (
    ArtifactManifest,
    ConfirmCustomUploadRequest,
    CreateCustomUploadRequest,
    ExportAuditEventType,
    ExportFormat,
    ExportProvenance,
    ExportStatus,
    ScreenshotFormat,
    JobStatus,
    ScreenshotExtractionRequest,
    ScreenshotMimeType,
    ScreenshotReplaceRequest,
    ScreenshotOperation,
    ScreenshotTaskStatus,
    ScreenshotStrategy,
    TranscriptSegment,
)

_IMMUTABLE_RAW_ARTIFACT_KEYS = frozenset({"video_uri", "audio_uri", "transcript_uri"})
_MUTABLE_ARTIFACT_KEYS = frozenset({"draft_uri", "exports"})
_TRANSITION_AUDIT_EVENT_TYPE = "JOB_STATUS_TRANSITION_APPLIED"
_REGENERATE_AUDIT_EVENT_TYPE = "INSTRUCTION_REGENERATE_SUCCEEDED"
_CALLBACK_FAILPOINT_STAGES = (
    "after_status",
    "after_manifest",
    "after_failure_metadata",
    "after_callback_event",
)
_CUSTOM_UPLOAD_MAX_SIZE_BYTES = 10 * 1024 * 1024
_CUSTOM_UPLOAD_ALLOWED_MIME_TYPES: tuple[str, ...] = (
    ScreenshotMimeType.PNG.value,
    ScreenshotMimeType.JPEG.value,
    ScreenshotMimeType.WEBP.value,
)
_SCREENSHOT_FORMAT_TO_MIME_TYPE: dict[str, str] = {
    ScreenshotFormat.PNG.value: ScreenshotMimeType.PNG.value,
    ScreenshotFormat.JPG.value: ScreenshotMimeType.JPEG.value,
    ScreenshotFormat.WEBP.value: ScreenshotMimeType.WEBP.value,
}
_CUSTOM_UPLOAD_URL_SCHEME = "https"
_CUSTOM_UPLOAD_URL_HOST = "uploads.howera.local"
_CUSTOM_UPLOAD_SIGNING_KEY = b"howera-custom-upload-v1"
_EXPORT_DOWNLOAD_URL_SCHEME = "https"
_EXPORT_FORMAT_TO_EXTENSION: dict[ExportFormat, str] = {
    ExportFormat.PDF: ".pdf",
    ExportFormat.MD_ZIP: ".zip",
}
_CUSTOM_UPLOAD_MIME_TO_EXTENSION: dict[str, str] = {
    ScreenshotMimeType.PNG.value: ".png",
    ScreenshotMimeType.JPEG.value: ".jpg",
    ScreenshotMimeType.WEBP.value: ".webp",
}
_ANNOTATION_ALLOWED_OP_TYPES = frozenset({"blur", "arrow", "marker", "pencil"})


@dataclass(slots=True)
class ProjectRecord:
    id: str
    name: str
    owner_id: str
    created_at: datetime


@dataclass(slots=True)
class JobRecord:
    id: str
    project_id: str
    owner_id: str
    status: JobStatus
    created_at: datetime
    updated_at: datetime | None = None
    manifest: ArtifactManifest | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    failed_stage: str | None = None
    retry_resume_from_status: JobStatus | None = None
    retry_checkpoint_ref: str | None = None
    retry_model_profile: str | None = None
    retry_client_request_id: str | None = None
    retry_dispatch_id: str | None = None


@dataclass(slots=True)
class InstructionRecord:
    instruction_id: str
    job_id: str
    owner_id: str
    version: int
    markdown: str
    updated_at: datetime
    validation_status: ValidationStatus
    validation_errors: list[ValidationIssue] | None = None
    validated_at: datetime | None = None
    validator_version: str | None = None
    model_profile_id: str | None = None
    prompt_template_id: str | None = None
    prompt_params_ref: str | None = None


@dataclass(slots=True)
class CallbackEventRecord:
    job_id: str
    event_id: str
    status: JobStatus
    occurred_at: datetime
    actor_type: Literal["orchestrator", "system"] | None
    artifact_updates: dict[str, Any] | None
    failure_code: str | None
    failure_message: str | None
    failed_stage: str | None
    correlation_id: str


@dataclass(slots=True)
class TransitionAuditRecord:
    event_type: str
    job_id: str
    project_id: str
    actor_type: Literal["editor", "orchestrator", "system"]
    prev_status: JobStatus
    new_status: JobStatus
    occurred_at: datetime
    recorded_at: datetime
    correlation_id: str


@dataclass(slots=True)
class WorkflowDispatchRecord:
    job_id: str
    dispatch_id: str
    dispatch_type: Literal["run", "retry"]
    payload: dict[str, str]
    created_at: datetime


@dataclass(slots=True)
class RetryRequestRecord:
    job_id: str
    client_request_id: str
    payload_signature: str
    resume_from_status: JobStatus
    checkpoint_ref: str
    model_profile: str
    dispatch_id: str
    created_at: datetime


@dataclass(slots=True)
class RegenerateTaskRecord:
    id: str
    instruction_id: str
    owner_id: str
    job_id: str
    status: RegenerateTaskStatus
    progress_pct: int | None
    instruction_version: int | None
    failure_code: str | None
    failure_message: str | None
    failed_stage: str | None
    provenance: RegenerateProvenance
    payload_signature: str
    client_request_id: str
    requested_at: datetime
    updated_at: datetime | None = None


@dataclass(slots=True)
class RegenerateAuditRecord:
    event_type: str
    task_id: str
    instruction_id: str
    owner_id: str
    instruction_version: int
    occurred_at: datetime
    recorded_at: datetime


@dataclass(slots=True)
class ScreenshotTaskRecord:
    id: str
    owner_id: str
    job_id: str
    instruction_id: str
    instruction_version_id: str
    operation: ScreenshotOperation
    status: ScreenshotTaskStatus
    timestamp_ms: int
    offset_ms: int
    strategy: ScreenshotStrategy
    image_format: str
    anchor_id: str | None
    block_id: str | None
    char_range: CharRange | None
    idempotency_key: str | None
    canonical_key: str
    payload_signature: str
    asset_id: str | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    requested_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class ScreenshotAnchorRecord:
    anchor_id: str
    owner_id: str
    job_id: str
    instruction_id: str
    instruction_version_id: str
    active_asset_id: str | None
    latest_asset_version: int
    created_at: datetime
    updated_at: datetime
    addressing_type: Literal["block_id", "char_range"] = "block_id"
    addressing_block_id: str | None = None
    addressing_char_range: CharRange | None = None
    addressing_strategy: str | None = None


@dataclass(slots=True)
class ScreenshotAssetRecord:
    asset_id: str
    anchor_id: str
    owner_id: str
    job_id: str
    version: int
    previous_asset_id: str | None
    extraction_key: str | None
    kind: str
    image_uri: str
    mime_type: str
    width: int
    height: int
    checksum_sha256: str | None
    upload_id: str | None
    ops_hash: str | None
    rendered_from_asset_id: str | None
    is_deleted: bool
    extraction_parameters: dict[str, Any]
    created_at: datetime


@dataclass(slots=True)
class CustomUploadRecord:
    upload_id: str
    owner_id: str
    job_id: str
    filename: str
    requested_mime_type: str
    requested_size_bytes: int
    requested_checksum_sha256: str
    upload_url: str
    expires_at: datetime
    max_size_bytes: int
    allowed_mime_types: tuple[str, ...]
    confirmed: bool = False
    confirmed_mime_type: str | None = None
    confirmed_size_bytes: int | None = None
    confirmed_checksum_sha256: str | None = None
    confirmed_width: int | None = None
    confirmed_height: int | None = None
    confirmed_asset_id: str | None = None
    confirmed_image_uri: str | None = None
    confirmed_at: datetime | None = None


@dataclass(slots=True)
class AttachUploadReplayRecord:
    asset_id: str
    payload_signature: str
    instruction_version_id: str
    updated_at: datetime


@dataclass(slots=True)
class AnnotationReplayRecord:
    anchor_id: str
    base_asset_id: str
    ops_hash: str
    rendered_asset_id: str
    active_asset_id: str
    payload_signature: str


@dataclass(slots=True)
class ScreenshotAnnotationResultRecord:
    anchor_id: str
    base_asset_id: str
    ops_hash: str
    rendered_asset_id: str
    active_asset_id: str
    replayed: bool


@dataclass(slots=True)
class ExportAnchorBindingRecord:
    anchor_id: str
    active_asset_id: str
    rendered_asset_id: str | None


@dataclass(slots=True)
class ExportRecord:
    export_id: str
    owner_id: str
    job_id: str
    format: ExportFormat
    status: ExportStatus
    instruction_version_id: str
    identity_key: str
    screenshot_set_hash: str
    provenance: ExportProvenance
    provenance_frozen_at: datetime | None
    last_audit_event: ExportAuditEventType | None
    download_url: str | None
    download_url_expires_at: datetime | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class ExportAuditRecord:
    event_type: ExportAuditEventType
    export_id: str
    identity_key: str
    occurred_at: datetime
    recorded_at: datetime
    correlation_id: str


@dataclass(slots=True)
class ExportManifestLinkageRecord:
    export_id: str
    identity_key: str
    linked_at: datetime


@dataclass(slots=True)
class InMemoryStore:
    """Simple, deterministic persistence layer for scaffolding and tests."""

    projects: dict[str, ProjectRecord] = field(default_factory=dict)
    jobs: dict[str, JobRecord] = field(default_factory=dict)
    instructions_by_id: dict[str, list[InstructionRecord]] = field(default_factory=dict)
    callback_events: dict[tuple[str, str], CallbackEventRecord] = field(default_factory=dict)
    transition_audit_events: list[TransitionAuditRecord] = field(default_factory=list)
    latest_callback_at_by_job: dict[str, datetime] = field(default_factory=dict)
    workflow_dispatches_by_job: dict[str, WorkflowDispatchRecord] = field(default_factory=dict)
    retry_requests_by_job_and_client: dict[tuple[str, str], RetryRequestRecord] = field(default_factory=dict)
    regenerate_tasks_by_id: dict[str, RegenerateTaskRecord] = field(default_factory=dict)
    regenerate_request_task_id_by_owner_instruction_client: dict[tuple[str, str, str], str] = field(default_factory=dict)
    regenerate_audit_events: list[RegenerateAuditRecord] = field(default_factory=list)
    screenshot_tasks_by_id: dict[str, ScreenshotTaskRecord] = field(default_factory=dict)
    screenshot_anchors_by_id: dict[str, ScreenshotAnchorRecord] = field(default_factory=dict)
    screenshot_task_id_by_canonical_key: dict[str, str] = field(default_factory=dict)
    screenshot_task_id_by_owner_job_idempotency: dict[tuple[str, str, str], str] = field(default_factory=dict)
    screenshot_replace_task_id_by_anchor_canonical_key: dict[tuple[str, str], str] = field(default_factory=dict)
    screenshot_replace_task_id_by_owner_anchor_idempotency: dict[tuple[str, str, str], str] = field(default_factory=dict)
    screenshot_assets_by_id: dict[str, ScreenshotAssetRecord] = field(default_factory=dict)
    screenshot_asset_ids_by_anchor: dict[str, list[str]] = field(default_factory=dict)
    screenshot_annotation_asset_id_by_anchor_base_ops_hash: dict[tuple[str, str, str], str] = field(default_factory=dict)
    screenshot_annotation_replay_by_owner_anchor_idempotency: dict[
        tuple[str, str, str],
        AnnotationReplayRecord,
    ] = field(default_factory=dict)
    custom_uploads_by_id: dict[str, CustomUploadRecord] = field(default_factory=dict)
    attach_upload_replay_by_owner_anchor_idempotency: dict[
        tuple[str, str, str],
        AttachUploadReplayRecord,
    ] = field(default_factory=dict)
    exports_by_id: dict[str, ExportRecord] = field(default_factory=dict)
    export_id_by_owner_job_identity: dict[tuple[str, str, str], str] = field(default_factory=dict)
    export_linkages_by_job: dict[str, list[ExportManifestLinkageRecord]] = field(default_factory=dict)
    export_audit_events: list[ExportAuditRecord] = field(default_factory=list)
    transcript_segments_by_job: dict[str, list[TranscriptSegment]] = field(default_factory=dict)
    project_write_count: int = 0
    job_write_count: int = 0
    instruction_write_count: int = 0
    dispatch_write_count: int = 0
    regenerate_task_write_count: int = 0
    regenerate_audit_write_count: int = 0
    screenshot_task_write_count: int = 0
    export_write_count: int = 0
    export_audit_write_count: int = 0
    export_download_url_host: str = "downloads.howera.local"
    export_download_url_ttl_minutes: int = 15
    export_download_signing_key: bytes | str = field(default_factory=lambda: uuid4().hex.encode("utf-8"))
    dispatch_failure_message: str | None = None
    callback_mutation_failpoint_event_id: str | None = None
    callback_mutation_failpoint_stage: Literal[
        "after_status",
        "after_manifest",
        "after_failure_metadata",
        "after_callback_event",
    ] | None = None
    callback_mutation_failpoint_message: str = "Injected callback persistence failure"
    annotation_render_failure_message: str | None = None

    def __post_init__(self) -> None:
        normalized_host = self.export_download_url_host.strip()
        if not normalized_host:
            raise ValueError("export_download_url_host must be non-empty")
        self.export_download_url_host = normalized_host

        if self.export_download_url_ttl_minutes < 1:
            raise ValueError("export_download_url_ttl_minutes must be >= 1")

        key_material = self.export_download_signing_key
        if isinstance(key_material, str):
            normalized_key = key_material.encode("utf-8")
        else:
            normalized_key = key_material
        if not normalized_key:
            raise ValueError("export_download_signing_key must be non-empty")
        self.export_download_signing_key = normalized_key

    def create_project(self, owner_id: str, name: str) -> ProjectRecord:
        now = datetime.now(UTC)
        project = ProjectRecord(
            id=str(uuid4()),
            name=name,
            owner_id=owner_id,
            created_at=now,
        )
        self.projects[project.id] = project
        self.project_write_count += 1
        return project

    def get_project(self, project_id: str) -> ProjectRecord | None:
        return self.projects.get(project_id)

    def list_projects_for_owner(self, owner_id: str) -> list[ProjectRecord]:
        projects = [record for record in self.projects.values() if record.owner_id == owner_id]
        projects.sort(key=lambda record: record.created_at)
        return projects

    def get_project_for_owner(self, owner_id: str, project_id: str) -> ProjectRecord | None:
        project = self.projects.get(project_id)
        if project is None or project.owner_id != owner_id:
            return None
        return project

    def create_job(self, owner_id: str, project_id: str) -> JobRecord:
        now = datetime.now(UTC)
        job = JobRecord(
            id=str(uuid4()),
            project_id=project_id,
            owner_id=owner_id,
            status=JobStatus.CREATED,
            created_at=now,
            updated_at=now,
        )
        self.jobs[job.id] = job
        self.job_write_count += 1
        return job

    def get_job_for_owner(self, owner_id: str, job_id: str) -> JobRecord | None:
        job = self.jobs.get(job_id)
        if job is None or job.owner_id != owner_id:
            return None
        return job

    def get_job_for_internal_callback(self, job_id: str) -> JobRecord | None:
        return self.jobs.get(job_id)

    def create_instruction_version(
        self,
        *,
        owner_id: str,
        instruction_id: str,
        job_id: str,
        version: int,
        markdown: str,
        updated_at: datetime | None = None,
        model_profile_id: str | None = None,
        prompt_template_id: str | None = None,
        prompt_params_ref: str | None = None,
    ) -> InstructionRecord:
        if version < 1:
            raise ValueError("instruction version must be >= 1")

        history = self.instructions_by_id.setdefault(instruction_id, [])
        if any(record.version == version for record in history):
            raise ValueError("instruction version already exists")

        validation_result = validate_instruction_markdown(markdown)
        record = InstructionRecord(
            instruction_id=instruction_id,
            job_id=job_id,
            owner_id=owner_id,
            version=version,
            markdown=markdown,
            updated_at=updated_at or datetime.now(UTC),
            validation_status=validation_result.status,
            validation_errors=[issue.model_copy(deep=True) for issue in validation_result.errors]
            if validation_result.errors is not None
            else None,
            validated_at=validation_result.validated_at,
            validator_version=validation_result.validator_version,
            model_profile_id=model_profile_id,
            prompt_template_id=prompt_template_id,
            prompt_params_ref=prompt_params_ref,
        )
        history.append(record)
        history.sort(key=lambda item: item.version)
        self.instruction_write_count += 1
        return self._copy_instruction_record(record)

    def get_instruction_for_owner(
        self,
        *,
        owner_id: str,
        instruction_id: str,
        version: int | None = None,
    ) -> InstructionRecord | None:
        history = self.instructions_by_id.get(instruction_id)
        if history is None:
            return None

        owned_history = [record for record in history if record.owner_id == owner_id]
        if not owned_history:
            return None

        if version is None:
            selected = max(owned_history, key=lambda item: item.version)
            return self._copy_instruction_record(selected)

        for record in owned_history:
            if record.version == version:
                return self._copy_instruction_record(record)
        return None

    def get_instruction_for_owner_job_version(
        self,
        *,
        owner_id: str,
        job_id: str,
        version: int,
    ) -> InstructionRecord | None:
        matches: list[InstructionRecord] = []
        for instruction_id in sorted(self.instructions_by_id.keys()):
            history = self.instructions_by_id[instruction_id]
            for record in history:
                if record.owner_id == owner_id and record.job_id == job_id and record.version == version:
                    matches.append(record)

        if len(matches) != 1:
            return None
        return self._copy_instruction_record(matches[0])

    def list_export_anchor_bindings(
        self,
        *,
        owner_id: str,
        job_id: str,
        instruction_id: str,
        instruction_version_id: str,
    ) -> list[ExportAnchorBindingRecord]:
        bindings: list[ExportAnchorBindingRecord] = []
        for anchor in self.screenshot_anchors_by_id.values():
            if (
                anchor.owner_id != owner_id
                or anchor.job_id != job_id
                or anchor.instruction_id != instruction_id
                or anchor.instruction_version_id != instruction_version_id
            ):
                continue
            active_asset_id = anchor.active_asset_id
            if not active_asset_id:
                continue
            active_asset = self.screenshot_assets_by_id.get(active_asset_id)
            if (
                active_asset is None
                or active_asset.owner_id != owner_id
                or active_asset.job_id != job_id
                or active_asset.anchor_id != anchor.anchor_id
                or active_asset.is_deleted
            ):
                continue
            rendered_asset_id = active_asset_id if active_asset.kind == "ANNOTATED" else None
            bindings.append(
                ExportAnchorBindingRecord(
                    anchor_id=anchor.anchor_id,
                    active_asset_id=active_asset_id,
                    rendered_asset_id=rendered_asset_id,
                )
            )

        bindings.sort(
            key=lambda record: (
                record.anchor_id,
                record.active_asset_id,
                record.rendered_asset_id or "",
            )
        )
        return [
            ExportAnchorBindingRecord(
                anchor_id=record.anchor_id,
                active_asset_id=record.active_asset_id,
                rendered_asset_id=record.rendered_asset_id,
            )
            for record in bindings
        ]

    @staticmethod
    def build_export_screenshot_set_hash(*, bindings: list[ExportAnchorBindingRecord]) -> str:
        canonical_bindings = [
            {
                "anchor_id": binding.anchor_id,
                "active_asset_id": binding.active_asset_id,
                "rendered_asset_id": binding.rendered_asset_id,
            }
            for binding in sorted(
                bindings,
                key=lambda record: (
                    record.anchor_id,
                    record.active_asset_id,
                    record.rendered_asset_id or "",
                ),
            )
        ]
        encoded = json.dumps(
            {"anchors": canonical_bindings},
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def build_export_identity_key(
        *,
        instruction_version_id: str,
        export_format: ExportFormat,
        screenshot_set_hash: str,
    ) -> str:
        return "|".join((instruction_version_id, export_format.value, screenshot_set_hash))

    def create_export_request(
        self,
        *,
        owner_id: str,
        job_id: str,
        export_format: ExportFormat,
        instruction_version_id: str,
        identity_key: str,
        screenshot_set_hash: str,
        provenance: ExportProvenance,
        occurred_at: datetime | None = None,
        correlation_id: str | None = None,
    ) -> tuple[ExportRecord, bool]:
        request_key = (owner_id, job_id, identity_key)
        existing_export_id = self.export_id_by_owner_job_identity.get(request_key)
        if existing_export_id is not None:
            existing_export = self.exports_by_id.get(existing_export_id)
            if existing_export is not None:
                return self._copy_export_record(existing_export), True
            self.export_id_by_owner_job_identity.pop(request_key, None)

        now = datetime.now(UTC)
        export_id = f"export-{uuid4()}"
        export_record = ExportRecord(
            export_id=export_id,
            owner_id=owner_id,
            job_id=job_id,
            format=export_format,
            status=ExportStatus.REQUESTED,
            instruction_version_id=instruction_version_id,
            identity_key=identity_key,
            screenshot_set_hash=screenshot_set_hash,
            provenance=provenance.model_copy(deep=True),
            provenance_frozen_at=None,
            last_audit_event=ExportAuditEventType.EXPORT_REQUESTED,
            download_url=None,
            download_url_expires_at=None,
            created_at=now,
            updated_at=now,
        )
        self.exports_by_id[export_id] = export_record
        self.export_id_by_owner_job_identity[request_key] = export_id
        self.export_write_count += 1
        self._append_export_audit_record(
            event_type=ExportAuditEventType.EXPORT_REQUESTED,
            export_record=export_record,
            occurred_at=occurred_at or now,
            correlation_id=correlation_id,
        )
        return self._copy_export_record(export_record), False

    def get_export_for_owner(
        self,
        *,
        owner_id: str,
        export_id: str,
    ) -> ExportRecord | None:
        record = self.exports_by_id.get(export_id)
        if record is None or record.owner_id != owner_id:
            return None
        return self._copy_export_record(record)

    def issue_export_download_url(
        self,
        *,
        owner_id: str,
        export_id: str,
    ) -> tuple[str, datetime]:
        export_record = self._get_export_record_for_owner_mutable(owner_id=owner_id, export_id=export_id)
        if export_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")
        if export_record.status is not ExportStatus.SUCCEEDED:
            raise ApiError(
                status_code=409,
                code="EXPORT_NOT_READY",
                message="Export download URL is available only for SUCCEEDED.",
                details={"current_status": export_record.status},
            )

        issued_at = datetime.now(UTC).replace(microsecond=0)
        expires_at = issued_at + timedelta(minutes=self.export_download_url_ttl_minutes)
        return self._build_export_download_url(
            owner_id=owner_id,
            export_id=export_id,
            export_format=export_record.format,
            expires_at=expires_at,
        ), expires_at

    def start_export_execution(
        self,
        *,
        owner_id: str,
        export_id: str,
        transition_job_status: bool = True,
        occurred_at: datetime | None = None,
        correlation_id: str | None = None,
    ) -> tuple[ExportRecord, bool]:
        export_record = self._get_export_record_for_owner_mutable(owner_id=owner_id, export_id=export_id)
        if export_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        if export_record.status in {
            ExportStatus.RUNNING,
            ExportStatus.SUCCEEDED,
            ExportStatus.FAILED,
        }:
            return self._copy_export_record(export_record), True

        job_record = self.jobs.get(export_record.job_id)
        if job_record is None or job_record.owner_id != owner_id:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        previous_export_status = export_record.status
        previous_export_updated_at = export_record.updated_at
        previous_export_event = export_record.last_audit_event
        previous_export_write_count = self.export_write_count
        previous_export_audit_count = len(self.export_audit_events)
        previous_export_audit_write_count = self.export_audit_write_count
        previous_job_status = job_record.status
        previous_job_updated_at = job_record.updated_at
        previous_job_write_count = self.job_write_count

        try:
            ensure_export_transition(export_record.status, ExportStatus.RUNNING)
            now = datetime.now(UTC)
            export_record.status = ExportStatus.RUNNING
            export_record.updated_at = now
            export_record.last_audit_event = ExportAuditEventType.EXPORT_STARTED
            self.export_write_count += 1

            if transition_job_status and job_record.status is not JobStatus.EXPORTING:
                self.transition_job_status(job=job_record, new_status=JobStatus.EXPORTING)

            self._append_export_audit_record(
                event_type=ExportAuditEventType.EXPORT_STARTED,
                export_record=export_record,
                occurred_at=occurred_at or now,
                correlation_id=correlation_id,
            )
            return self._copy_export_record(export_record), False
        except Exception:
            export_record.status = previous_export_status
            export_record.updated_at = previous_export_updated_at
            export_record.last_audit_event = previous_export_event
            self.export_write_count = previous_export_write_count
            if len(self.export_audit_events) > previous_export_audit_count:
                del self.export_audit_events[previous_export_audit_count:]
            self.export_audit_write_count = previous_export_audit_write_count
            job_record.status = previous_job_status
            job_record.updated_at = previous_job_updated_at
            self.job_write_count = previous_job_write_count
            raise

    def complete_export_success(
        self,
        *,
        owner_id: str,
        export_id: str,
        transition_job_status: bool = True,
        occurred_at: datetime | None = None,
        correlation_id: str | None = None,
    ) -> tuple[ExportRecord, bool]:
        export_record = self._get_export_record_for_owner_mutable(owner_id=owner_id, export_id=export_id)
        if export_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        if export_record.status is ExportStatus.SUCCEEDED:
            return self._copy_export_record(export_record), True

        job_record = self.jobs.get(export_record.job_id)
        if job_record is None or job_record.owner_id != owner_id:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        previous_export_status = export_record.status
        previous_export_updated_at = export_record.updated_at
        previous_export_event = export_record.last_audit_event
        previous_frozen_at = export_record.provenance_frozen_at
        previous_export_write_count = self.export_write_count
        previous_export_audit_count = len(self.export_audit_events)
        previous_export_audit_write_count = self.export_audit_write_count
        previous_job_status = job_record.status
        previous_job_updated_at = job_record.updated_at
        previous_job_manifest = job_record.manifest.model_copy(deep=True) if job_record.manifest is not None else None
        previous_job_write_count = self.job_write_count
        previous_linkages = [
            self._copy_export_manifest_linkage_record(record)
            for record in self.export_linkages_by_job.get(job_record.id, [])
        ]
        had_linkages = job_record.id in self.export_linkages_by_job

        try:
            ensure_export_transition(export_record.status, ExportStatus.SUCCEEDED)
            now = datetime.now(UTC)
            export_record.status = ExportStatus.SUCCEEDED
            export_record.updated_at = now
            export_record.last_audit_event = ExportAuditEventType.EXPORT_SUCCEEDED
            if export_record.provenance_frozen_at is None:
                export_record.provenance_frozen_at = now
            self.export_write_count += 1

            manifest = job_record.manifest.model_copy(deep=True) if job_record.manifest is not None else ArtifactManifest()
            existing_exports = list(manifest.exports or [])
            manifest_changed = False
            if export_record.export_id not in existing_exports:
                existing_exports.append(export_record.export_id)
                manifest.exports = existing_exports
                job_record.manifest = manifest
                manifest_changed = True
            self._record_export_manifest_linkage(
                job_id=job_record.id,
                export_id=export_record.export_id,
                identity_key=export_record.identity_key,
                linked_at=now,
            )

            if transition_job_status and job_record.status is not JobStatus.DONE:
                self.transition_job_status(job=job_record, new_status=JobStatus.DONE)
            elif manifest_changed:
                job_record.updated_at = now
                self.job_write_count += 1

            self._append_export_audit_record(
                event_type=ExportAuditEventType.EXPORT_SUCCEEDED,
                export_record=export_record,
                occurred_at=occurred_at or now,
                correlation_id=correlation_id,
            )

            return self._copy_export_record(export_record), False
        except Exception:
            export_record.status = previous_export_status
            export_record.updated_at = previous_export_updated_at
            export_record.last_audit_event = previous_export_event
            export_record.provenance_frozen_at = previous_frozen_at
            self.export_write_count = previous_export_write_count
            if len(self.export_audit_events) > previous_export_audit_count:
                del self.export_audit_events[previous_export_audit_count:]
            self.export_audit_write_count = previous_export_audit_write_count
            job_record.status = previous_job_status
            job_record.updated_at = previous_job_updated_at
            job_record.manifest = previous_job_manifest
            self.job_write_count = previous_job_write_count
            if had_linkages:
                self.export_linkages_by_job[job_record.id] = previous_linkages
            else:
                self.export_linkages_by_job.pop(job_record.id, None)
            raise

    def complete_export_failure(
        self,
        *,
        owner_id: str,
        export_id: str,
        transition_job_status: bool = True,
        occurred_at: datetime | None = None,
        correlation_id: str | None = None,
    ) -> tuple[ExportRecord, bool]:
        export_record = self._get_export_record_for_owner_mutable(owner_id=owner_id, export_id=export_id)
        if export_record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        if export_record.status is ExportStatus.FAILED:
            return self._copy_export_record(export_record), True

        job_record = self.jobs.get(export_record.job_id)
        if job_record is None or job_record.owner_id != owner_id:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        previous_export_status = export_record.status
        previous_export_updated_at = export_record.updated_at
        previous_export_event = export_record.last_audit_event
        previous_export_write_count = self.export_write_count
        previous_export_audit_count = len(self.export_audit_events)
        previous_export_audit_write_count = self.export_audit_write_count
        previous_job_status = job_record.status
        previous_job_updated_at = job_record.updated_at
        previous_job_write_count = self.job_write_count

        try:
            ensure_export_transition(export_record.status, ExportStatus.FAILED)
            now = datetime.now(UTC)
            export_record.status = ExportStatus.FAILED
            export_record.updated_at = now
            export_record.last_audit_event = ExportAuditEventType.EXPORT_FAILED
            self.export_write_count += 1

            if transition_job_status and job_record.status is not JobStatus.EDITING:
                self.transition_job_status(job=job_record, new_status=JobStatus.EDITING)

            self._append_export_audit_record(
                event_type=ExportAuditEventType.EXPORT_FAILED,
                export_record=export_record,
                occurred_at=occurred_at or now,
                correlation_id=correlation_id,
            )

            return self._copy_export_record(export_record), False
        except Exception:
            export_record.status = previous_export_status
            export_record.updated_at = previous_export_updated_at
            export_record.last_audit_event = previous_export_event
            self.export_write_count = previous_export_write_count
            if len(self.export_audit_events) > previous_export_audit_count:
                del self.export_audit_events[previous_export_audit_count:]
            self.export_audit_write_count = previous_export_audit_write_count
            job_record.status = previous_job_status
            job_record.updated_at = previous_job_updated_at
            self.job_write_count = previous_job_write_count
            raise

    def _record_export_manifest_linkage(
        self,
        *,
        job_id: str,
        export_id: str,
        identity_key: str,
        linked_at: datetime,
    ) -> None:
        existing = self.export_linkages_by_job.get(job_id, [])
        for record in existing:
            if record.export_id == export_id and record.identity_key == identity_key:
                return
        existing.append(
            ExportManifestLinkageRecord(
                export_id=export_id,
                identity_key=identity_key,
                linked_at=linked_at,
            )
        )
        existing.sort(key=lambda record: (record.export_id, record.identity_key))
        self.export_linkages_by_job[job_id] = existing

    def set_transcript_segments_for_job(self, *, job_id: str, segments: list[TranscriptSegment]) -> None:
        self.transcript_segments_by_job[job_id] = [segment.model_copy(deep=True) for segment in segments]

    def list_transcript_segments_for_job(self, *, job_id: str) -> list[TranscriptSegment]:
        segments = self.transcript_segments_by_job.get(job_id, [])
        return [segment.model_copy(deep=True) for segment in segments]

    def transition_job_status(self, *, job: JobRecord, new_status: JobStatus) -> None:
        """Apply an FSM-validated status mutation with consistent write bookkeeping."""
        ensure_transition(job.status, new_status)
        job.status = new_status
        job.updated_at = datetime.now(UTC)
        self.job_write_count += 1

    def transition_job_status_from_retry_checkpoint(self, *, job: JobRecord, new_status: JobStatus) -> None:
        """Apply a retry-resume transition using persisted checkpoint status as FSM source."""
        resume_from_status = job.retry_resume_from_status
        if resume_from_status is None:
            raise RuntimeError("retry_resume_from_status is required for retry-resume transition")

        ensure_transition(resume_from_status, new_status)
        job.status = new_status
        job.updated_at = datetime.now(UTC)
        self.job_write_count += 1

    def transition_job_status_with_audit(
        self,
        *,
        job: JobRecord,
        new_status: JobStatus,
        actor_type: Literal["editor", "orchestrator", "system"] | None,
        occurred_at: datetime,
        correlation_id: str,
    ) -> None:
        """Apply a status transition and corresponding audit event atomically."""
        previous_status = job.status
        previous_updated_at = job.updated_at
        previous_job_write_count = self.job_write_count
        previous_transition_audit_count = len(self.transition_audit_events)
        try:
            self.transition_job_status(job=job, new_status=new_status)
            self.transition_audit_events.append(
                self._build_transition_audit_record(
                    job=job,
                    prev_status=previous_status,
                    new_status=new_status,
                    actor_type=actor_type,
                    occurred_at=occurred_at,
                    correlation_id=correlation_id,
                )
            )
        except Exception:
            job.status = previous_status
            job.updated_at = previous_updated_at
            self.job_write_count = previous_job_write_count
            if len(self.transition_audit_events) > previous_transition_audit_count:
                del self.transition_audit_events[previous_transition_audit_count:]
            raise

    def apply_callback_mutation(
        self,
        *,
        job: JobRecord,
        callback_event: CallbackEventRecord,
    ) -> None:
        """Atomically apply callback status + side effects; rollback everything on failure."""
        callback_key = (callback_event.job_id, callback_event.event_id)
        previous_status = job.status
        previous_updated_at = job.updated_at
        previous_manifest = job.manifest.model_copy(deep=True) if job.manifest is not None else None
        previous_failure_code = job.failure_code
        previous_failure_message = job.failure_message
        previous_failed_stage = job.failed_stage
        previous_job_write_count = self.job_write_count
        previous_callback_event = self.callback_events.get(callback_key)
        had_callback_event = callback_key in self.callback_events
        previous_transition_audit_count = len(self.transition_audit_events)
        previous_latest_callback_at = self.latest_callback_at_by_job.get(job.id)
        had_latest_callback = job.id in self.latest_callback_at_by_job
        previous_transcript_segments = self.transcript_segments_by_job.get(job.id)
        had_transcript_segments = job.id in self.transcript_segments_by_job
        export_id = self._extract_export_id_from_updates(callback_event.artifact_updates)
        previous_export_record: ExportRecord | None = None
        had_export_record = False
        previous_export_write_count = self.export_write_count
        previous_export_audit_count = len(self.export_audit_events)
        previous_export_audit_write_count = self.export_audit_write_count
        previous_export_linkages = [
            self._copy_export_manifest_linkage_record(record) for record in self.export_linkages_by_job.get(job.id, [])
        ]
        had_export_linkages = job.id in self.export_linkages_by_job
        if export_id is not None:
            existing_export_record = self.exports_by_id.get(export_id)
            had_export_record = export_id in self.exports_by_id
            if existing_export_record is not None:
                previous_export_record = self._copy_export_record(existing_export_record)

        try:
            if job.status is JobStatus.FAILED and job.retry_resume_from_status is not None and job.retry_dispatch_id is not None:
                # Retry accepts from FAILED; subsequent callbacks are validated from persisted checkpoint resume status.
                self.transition_job_status_from_retry_checkpoint(job=job, new_status=callback_event.status)
            else:
                self.transition_job_status(job=job, new_status=callback_event.status)
            self._maybe_raise_callback_failpoint(event_id=callback_event.event_id, stage="after_status")
            self._apply_export_execution_callback(
                job=job,
                callback_event=callback_event,
                export_id=export_id,
            )

            job.manifest = self._merge_artifact_updates(
                current_manifest=job.manifest,
                artifact_updates=callback_event.artifact_updates,
            )
            self._apply_transcript_segment_updates(
                job_id=job.id,
                artifact_updates=callback_event.artifact_updates,
            )
            self._maybe_raise_callback_failpoint(event_id=callback_event.event_id, stage="after_manifest")

            self._apply_failure_metadata(job=job, callback_event=callback_event)
            self._maybe_raise_callback_failpoint(event_id=callback_event.event_id, stage="after_failure_metadata")

            self.callback_events[callback_key] = callback_event
            self.transition_audit_events.append(
                self._build_transition_audit_record(
                    job=job,
                    prev_status=previous_status,
                    new_status=callback_event.status,
                    actor_type=callback_event.actor_type,
                    occurred_at=callback_event.occurred_at,
                    correlation_id=callback_event.correlation_id,
                )
            )
            self.latest_callback_at_by_job[job.id] = callback_event.occurred_at
            self._maybe_raise_callback_failpoint(event_id=callback_event.event_id, stage="after_callback_event")
        except Exception:
            job.status = previous_status
            job.updated_at = previous_updated_at
            job.manifest = previous_manifest
            job.failure_code = previous_failure_code
            job.failure_message = previous_failure_message
            job.failed_stage = previous_failed_stage
            self.job_write_count = previous_job_write_count
            if had_callback_event and previous_callback_event is not None:
                self.callback_events[callback_key] = previous_callback_event
            else:
                self.callback_events.pop(callback_key, None)
            if len(self.transition_audit_events) > previous_transition_audit_count:
                del self.transition_audit_events[previous_transition_audit_count:]
            if had_latest_callback and previous_latest_callback_at is not None:
                self.latest_callback_at_by_job[job.id] = previous_latest_callback_at
            else:
                self.latest_callback_at_by_job.pop(job.id, None)
            if had_transcript_segments and previous_transcript_segments is not None:
                self.transcript_segments_by_job[job.id] = [
                    segment.model_copy(deep=True) for segment in previous_transcript_segments
                ]
            else:
                self.transcript_segments_by_job.pop(job.id, None)
            self.export_write_count = previous_export_write_count
            if len(self.export_audit_events) > previous_export_audit_count:
                del self.export_audit_events[previous_export_audit_count:]
            self.export_audit_write_count = previous_export_audit_write_count
            if export_id is not None:
                if had_export_record and previous_export_record is not None:
                    self.exports_by_id[export_id] = previous_export_record
                else:
                    self.exports_by_id.pop(export_id, None)
            if had_export_linkages:
                self.export_linkages_by_job[job.id] = previous_export_linkages
            else:
                self.export_linkages_by_job.pop(job.id, None)
            raise

    @staticmethod
    def _extract_export_id_from_updates(artifact_updates: dict[str, Any] | None) -> str | None:
        if artifact_updates is None:
            return None
        export_id = artifact_updates.get("export_id")
        if not isinstance(export_id, str):
            return None
        normalized = export_id.strip()
        return normalized or None

    def _apply_export_execution_callback(
        self,
        *,
        job: JobRecord,
        callback_event: CallbackEventRecord,
        export_id: str | None,
    ) -> None:
        if export_id is None:
            return

        if callback_event.status is JobStatus.EXPORTING:
            self.start_export_execution(
                owner_id=job.owner_id,
                export_id=export_id,
                transition_job_status=False,
                occurred_at=callback_event.occurred_at,
                correlation_id=callback_event.correlation_id,
            )
            return
        if callback_event.status is JobStatus.DONE:
            self.complete_export_success(
                owner_id=job.owner_id,
                export_id=export_id,
                transition_job_status=False,
                occurred_at=callback_event.occurred_at,
                correlation_id=callback_event.correlation_id,
            )
            return
        if callback_event.status in {JobStatus.EDITING, JobStatus.FAILED}:
            self.complete_export_failure(
                owner_id=job.owner_id,
                export_id=export_id,
                transition_job_status=False,
                occurred_at=callback_event.occurred_at,
                correlation_id=callback_event.correlation_id,
            )

    @staticmethod
    def _merge_artifact_updates(
        *,
        current_manifest: ArtifactManifest | None,
        artifact_updates: dict[str, Any] | None,
    ) -> ArtifactManifest | None:
        if artifact_updates is None:
            return current_manifest

        merged_manifest = current_manifest.model_copy(deep=True) if current_manifest is not None else ArtifactManifest()
        has_applied_update = False

        for key, value in artifact_updates.items():
            if key in _IMMUTABLE_RAW_ARTIFACT_KEYS:
                # Immutable raw keys allow first-write only; overwrite/delete attempts are ignored.
                if not isinstance(value, str):
                    continue
                if getattr(merged_manifest, key) is None:
                    setattr(merged_manifest, key, value)
                    has_applied_update = True
                continue
            # Unknown keys are ignored deterministically.
            if key not in _MUTABLE_ARTIFACT_KEYS:
                continue
            # Null updates never clear existing manifest values implicitly.
            if value is None:
                continue
            if key == "draft_uri" and isinstance(value, str):
                merged_manifest.draft_uri = value
                has_applied_update = True
                continue
            if key == "exports" and isinstance(value, list) and all(isinstance(item, str) for item in value):
                merged_manifest.exports = list(value)
                has_applied_update = True

        if current_manifest is None and not has_applied_update:
            return None
        return merged_manifest

    @staticmethod
    def _apply_failure_metadata(*, job: JobRecord, callback_event: CallbackEventRecord) -> None:
        if callback_event.failure_code is not None:
            job.failure_code = callback_event.failure_code
        if callback_event.failure_message is not None:
            job.failure_message = callback_event.failure_message
        if callback_event.failed_stage is not None:
            job.failed_stage = callback_event.failed_stage

    def _apply_transcript_segment_updates(
        self,
        *,
        job_id: str,
        artifact_updates: dict[str, Any] | None,
    ) -> None:
        segments = self._extract_transcript_segments_from_updates(artifact_updates=artifact_updates)
        if segments is None:
            return
        self.transcript_segments_by_job[job_id] = [segment.model_copy(deep=True) for segment in segments]

    @staticmethod
    def _extract_transcript_segments_from_updates(
        *,
        artifact_updates: dict[str, Any] | None,
    ) -> list[TranscriptSegment] | None:
        if artifact_updates is None:
            return None

        raw_segments = artifact_updates.get("transcript_segments")
        if raw_segments is None or not isinstance(raw_segments, list):
            return None

        parsed_segments: list[TranscriptSegment] = []
        for raw_segment in raw_segments:
            if not isinstance(raw_segment, dict):
                return None
            try:
                parsed_segments.append(TranscriptSegment.model_validate(raw_segment))
            except ValidationError:
                return None
        return parsed_segments

    @staticmethod
    def _build_transition_audit_record(
        *,
        job: JobRecord,
        prev_status: JobStatus,
        new_status: JobStatus,
        actor_type: Literal["editor", "orchestrator", "system"] | None,
        occurred_at: datetime,
        correlation_id: str,
    ) -> TransitionAuditRecord:
        return TransitionAuditRecord(
            event_type=_TRANSITION_AUDIT_EVENT_TYPE,
            job_id=job.id,
            project_id=job.project_id,
            actor_type=actor_type or "system",
            prev_status=prev_status,
            new_status=new_status,
            occurred_at=occurred_at,
            recorded_at=datetime.now(UTC),
            correlation_id=correlation_id,
        )

    def _maybe_raise_callback_failpoint(
        self,
        *,
        event_id: str,
        stage: Literal[
            "after_status",
            "after_manifest",
            "after_failure_metadata",
            "after_callback_event",
        ],
    ) -> None:
        if stage not in _CALLBACK_FAILPOINT_STAGES:
            return
        if self.callback_mutation_failpoint_event_id != event_id:
            return
        if self.callback_mutation_failpoint_stage != stage:
            return

        self.callback_mutation_failpoint_event_id = None
        self.callback_mutation_failpoint_stage = None
        raise RuntimeError(self.callback_mutation_failpoint_message)

    def get_dispatch_for_job(self, job_id: str) -> WorkflowDispatchRecord | None:
        return self.workflow_dispatches_by_job.get(job_id)

    def delete_dispatch_for_job(self, job_id: str) -> WorkflowDispatchRecord | None:
        return self.workflow_dispatches_by_job.pop(job_id, None)

    def get_retry_request(self, *, job_id: str, client_request_id: str) -> RetryRequestRecord | None:
        return self.retry_requests_by_job_and_client.get((job_id, client_request_id))

    def create_regenerate_task(
        self,
        *,
        owner_id: str,
        instruction_id: str,
        job_id: str,
        base_version: int,
        selection: RegenerateSelection,
        client_request_id: str,
        context: str | None = None,
        model_profile: str | None = None,
        prompt_template_id: str | None = None,
        prompt_params_ref: str | None = None,
    ) -> tuple[RegenerateTaskRecord, bool]:
        request_key = (owner_id, instruction_id, client_request_id)
        payload_signature = self._build_regenerate_payload_signature(
            base_version=base_version,
            selection=selection,
            context=context,
            model_profile=model_profile,
            prompt_template_id=prompt_template_id,
            prompt_params_ref=prompt_params_ref,
        )

        existing_task_id = self.regenerate_request_task_id_by_owner_instruction_client.get(request_key)
        if existing_task_id is not None:
            existing_task = self.regenerate_tasks_by_id[existing_task_id]
            if existing_task.payload_signature != payload_signature:
                raise ValueError("regenerate request payload differs from first accepted payload")
            return self._copy_regenerate_task_record(existing_task), True

        now = datetime.now(UTC)
        task = RegenerateTaskRecord(
            id=f"task-{uuid4()}",
            instruction_id=instruction_id,
            owner_id=owner_id,
            job_id=job_id,
            status=RegenerateTaskStatus.PENDING,
            progress_pct=0,
            instruction_version=None,
            failure_code=None,
            failure_message=None,
            failed_stage=None,
            provenance=RegenerateProvenance(
                instruction_id=instruction_id,
                base_version=base_version,
                selection=selection.model_copy(deep=True),
                requested_by=owner_id,
                requested_at=now,
                model_profile=model_profile,
                prompt_template_id=prompt_template_id,
                prompt_params_ref=prompt_params_ref,
            ),
            payload_signature=payload_signature,
            client_request_id=client_request_id,
            requested_at=now,
            updated_at=now,
        )
        self.regenerate_tasks_by_id[task.id] = task
        self.regenerate_request_task_id_by_owner_instruction_client[request_key] = task.id
        self.regenerate_task_write_count += 1
        return self._copy_regenerate_task_record(task), False

    def get_regenerate_task_for_request(
        self,
        *,
        owner_id: str,
        instruction_id: str,
        client_request_id: str,
    ) -> RegenerateTaskRecord | None:
        request_key = (owner_id, instruction_id, client_request_id)
        task_id = self.regenerate_request_task_id_by_owner_instruction_client.get(request_key)
        if task_id is None:
            return None
        task = self.regenerate_tasks_by_id.get(task_id)
        if task is None:
            return None
        return self._copy_regenerate_task_record(task)

    def regenerate_payload_matches_task(
        self,
        *,
        task: RegenerateTaskRecord,
        base_version: int,
        selection: RegenerateSelection,
        context: str | None = None,
        model_profile: str | None = None,
        prompt_template_id: str | None = None,
        prompt_params_ref: str | None = None,
    ) -> bool:
        payload_signature = self._build_regenerate_payload_signature(
            base_version=base_version,
            selection=selection,
            context=context,
            model_profile=model_profile,
            prompt_template_id=prompt_template_id,
            prompt_params_ref=prompt_params_ref,
        )
        return task.payload_signature == payload_signature

    def get_regenerate_task_for_owner(self, *, owner_id: str, task_id: str) -> RegenerateTaskRecord | None:
        task = self.regenerate_tasks_by_id.get(task_id)
        if task is None or task.owner_id != owner_id:
            return None
        return self._copy_regenerate_task_record(task)

    def complete_regenerate_task_success(
        self,
        *,
        task_id: str,
        markdown: str,
    ) -> RegenerateTaskRecord:
        task = self.regenerate_tasks_by_id.get(task_id)
        if task is None:
            raise ValueError("regenerate task not found")
        if task.status is RegenerateTaskStatus.SUCCEEDED:
            return self._copy_regenerate_task_record(task)

        current_instruction = self.get_instruction_for_owner(
            owner_id=task.owner_id,
            instruction_id=task.instruction_id,
            version=None,
        )
        if current_instruction is None:
            raise ValueError("instruction not found for regenerate task")

        new_instruction = self.create_instruction_version(
            owner_id=task.owner_id,
            instruction_id=task.instruction_id,
            job_id=task.job_id,
            version=current_instruction.version + 1,
            markdown=markdown,
            model_profile_id=task.provenance.model_profile,
            prompt_template_id=task.provenance.prompt_template_id,
            prompt_params_ref=task.provenance.prompt_params_ref,
        )

        now = datetime.now(UTC)
        task.status = RegenerateTaskStatus.SUCCEEDED
        task.progress_pct = 100
        task.instruction_version = new_instruction.version
        task.failure_code = None
        task.failure_message = None
        task.failed_stage = None
        task.updated_at = now
        self.regenerate_task_write_count += 1

        self.regenerate_audit_events.append(
            RegenerateAuditRecord(
                event_type=_REGENERATE_AUDIT_EVENT_TYPE,
                task_id=task.id,
                instruction_id=task.instruction_id,
                owner_id=task.owner_id,
                instruction_version=new_instruction.version,
                occurred_at=now,
                recorded_at=now,
            )
        )
        self.regenerate_audit_write_count += 1
        return self._copy_regenerate_task_record(task)

    def fail_regenerate_task(
        self,
        *,
        task_id: str,
        failure_code: str,
        failure_message: str | None = None,
        failed_stage: str | None = None,
    ) -> RegenerateTaskRecord:
        task = self.regenerate_tasks_by_id.get(task_id)
        if task is None:
            raise ValueError("regenerate task not found")

        task.status = RegenerateTaskStatus.FAILED
        task.progress_pct = 100
        task.instruction_version = None
        task.failure_code = failure_code
        task.failure_message = self._sanitize_regenerate_failure_message(failure_message)
        task.failed_stage = failed_stage
        task.updated_at = datetime.now(UTC)
        self.regenerate_task_write_count += 1
        return self._copy_regenerate_task_record(task)

    def create_screenshot_extraction_task(
        self,
        *,
        owner_id: str,
        job_id: str,
        payload: ScreenshotExtractionRequest,
    ) -> tuple[ScreenshotTaskRecord, bool]:
        canonical_key = self.build_screenshot_extraction_canonical_key(
            job_id=job_id,
            instruction_version_id=payload.instruction_version_id,
            timestamp_ms=payload.timestamp_ms,
            offset_ms=payload.offset_ms,
            strategy=payload.strategy,
            image_format=payload.format,
        )
        payload_signature = self._build_screenshot_payload_signature(payload=payload)

        if payload.idempotency_key is not None:
            request_key = (owner_id, job_id, payload.idempotency_key)
            existing_task_id = self.screenshot_task_id_by_owner_job_idempotency.get(request_key)
            if existing_task_id is not None:
                existing_task = self.screenshot_tasks_by_id[existing_task_id]
                if existing_task.payload_signature != payload_signature:
                    raise ValueError("duplicate idempotency_key payload differs from first accepted request")
                return self._copy_screenshot_task_record(existing_task), True

        existing_task_id = self.screenshot_task_id_by_canonical_key.get(canonical_key)
        if existing_task_id is not None:
            existing_task = self.screenshot_tasks_by_id[existing_task_id]
            if payload.idempotency_key is not None:
                # Canonical duplicates should replay, but avoid binding idempotency keys to a task
                # when non-canonical payload fields differ from the original accepted payload.
                if existing_task.payload_signature == payload_signature:
                    self.screenshot_task_id_by_owner_job_idempotency[(owner_id, job_id, payload.idempotency_key)] = (
                        existing_task.id
                    )
            return self._copy_screenshot_task_record(existing_task), True

        now = datetime.now(UTC)
        task = ScreenshotTaskRecord(
            id=f"screenshot-task-{uuid4()}",
            owner_id=owner_id,
            job_id=job_id,
            instruction_id=payload.instruction_id,
            instruction_version_id=payload.instruction_version_id,
            operation=ScreenshotOperation.EXTRACT,
            status=ScreenshotTaskStatus.PENDING,
            timestamp_ms=payload.timestamp_ms,
            offset_ms=payload.offset_ms,
            strategy=payload.strategy,
            image_format=payload.format.value,
            anchor_id=payload.anchor_id,
            block_id=payload.block_id,
            char_range=payload.char_range.model_copy(deep=True) if payload.char_range is not None else None,
            idempotency_key=payload.idempotency_key,
            canonical_key=canonical_key,
            payload_signature=payload_signature,
            requested_at=now,
            updated_at=now,
        )
        self.screenshot_tasks_by_id[task.id] = task
        self.screenshot_task_id_by_canonical_key[canonical_key] = task.id
        if payload.idempotency_key is not None:
            self.screenshot_task_id_by_owner_job_idempotency[(owner_id, job_id, payload.idempotency_key)] = task.id
        self.screenshot_task_write_count += 1
        return self._copy_screenshot_task_record(task), False

    def create_screenshot_replace_task(
        self,
        *,
        owner_id: str,
        anchor_id: str,
        job_id: str,
        instruction_id: str,
        payload: ScreenshotReplaceRequest,
    ) -> tuple[ScreenshotTaskRecord, bool]:
        anchor = self.screenshot_anchors_by_id.get(anchor_id)
        if anchor is None or anchor.owner_id != owner_id:
            raise ValueError("screenshot anchor not found")
        if anchor.job_id != job_id or anchor.instruction_id != instruction_id:
            raise ValueError("screenshot anchor context mismatch")

        canonical_key = self.build_screenshot_extraction_canonical_key(
            job_id=job_id,
            instruction_version_id=payload.instruction_version_id,
            timestamp_ms=payload.timestamp_ms,
            offset_ms=payload.offset_ms,
            strategy=payload.strategy,
            image_format=payload.format,
        )
        payload_signature = self._build_screenshot_replace_payload_signature(payload=payload)
        current_active_asset = (
            self.screenshot_assets_by_id.get(anchor.active_asset_id) if anchor.active_asset_id is not None else None
        )
        current_active_extraction_key = current_active_asset.extraction_key if current_active_asset is not None else None

        if payload.idempotency_key is not None:
            request_key = (owner_id, anchor_id, payload.idempotency_key)
            existing_task_id = self.screenshot_replace_task_id_by_owner_anchor_idempotency.get(request_key)
            if existing_task_id is not None:
                existing_task = self.screenshot_tasks_by_id[existing_task_id]
                if existing_task.payload_signature != payload_signature:
                    raise ValueError("duplicate idempotency_key payload differs from first accepted request")
                return self._copy_screenshot_task_record(existing_task), True

        existing_task_id = self.screenshot_replace_task_id_by_anchor_canonical_key.get((anchor_id, canonical_key))
        if existing_task_id is not None:
            existing_task = self.screenshot_tasks_by_id[existing_task_id]
            # If anchor moved to a different active extraction key after a previous SUCCEEDED
            # replacement, allow creating a new replacement task for this historical key.
            should_replay = not (
                existing_task.status is ScreenshotTaskStatus.SUCCEEDED and current_active_extraction_key != canonical_key
            )
            if should_replay:
                if payload.idempotency_key is not None and existing_task.payload_signature == payload_signature:
                    self.screenshot_replace_task_id_by_owner_anchor_idempotency[(owner_id, anchor_id, payload.idempotency_key)] = (
                        existing_task.id
                    )
                return self._copy_screenshot_task_record(existing_task), True

        if current_active_extraction_key == canonical_key:
            # State-equivalent replay: persist a replace task snapshot but do not mutate asset versions.
            now = datetime.now(UTC)
            noop_task = ScreenshotTaskRecord(
                id=f"screenshot-task-{uuid4()}",
                owner_id=owner_id,
                job_id=job_id,
                instruction_id=instruction_id,
                instruction_version_id=payload.instruction_version_id,
                operation=ScreenshotOperation.REPLACE,
                status=ScreenshotTaskStatus.SUCCEEDED,
                timestamp_ms=payload.timestamp_ms,
                offset_ms=payload.offset_ms,
                strategy=payload.strategy,
                image_format=payload.format.value,
                anchor_id=anchor_id,
                block_id=None,
                char_range=None,
                idempotency_key=payload.idempotency_key,
                canonical_key=canonical_key,
                payload_signature=payload_signature,
                asset_id=anchor.active_asset_id,
                requested_at=now,
                updated_at=now,
            )
            self.screenshot_tasks_by_id[noop_task.id] = noop_task
            self.screenshot_replace_task_id_by_anchor_canonical_key[(anchor_id, canonical_key)] = noop_task.id
            if payload.idempotency_key is not None:
                self.screenshot_replace_task_id_by_owner_anchor_idempotency[(owner_id, anchor_id, payload.idempotency_key)] = (
                    noop_task.id
                )
            self.screenshot_task_write_count += 1
            return self._copy_screenshot_task_record(noop_task), True

        now = datetime.now(UTC)
        task = ScreenshotTaskRecord(
            id=f"screenshot-task-{uuid4()}",
            owner_id=owner_id,
            job_id=job_id,
            instruction_id=instruction_id,
            instruction_version_id=payload.instruction_version_id,
            operation=ScreenshotOperation.REPLACE,
            status=ScreenshotTaskStatus.PENDING,
            timestamp_ms=payload.timestamp_ms,
            offset_ms=payload.offset_ms,
            strategy=payload.strategy,
            image_format=payload.format.value,
            anchor_id=anchor_id,
            block_id=None,
            char_range=None,
            idempotency_key=payload.idempotency_key,
            canonical_key=canonical_key,
            payload_signature=payload_signature,
            requested_at=now,
            updated_at=now,
        )
        self.screenshot_tasks_by_id[task.id] = task
        self.screenshot_replace_task_id_by_anchor_canonical_key[(anchor_id, canonical_key)] = task.id
        if payload.idempotency_key is not None:
            self.screenshot_replace_task_id_by_owner_anchor_idempotency[(owner_id, anchor_id, payload.idempotency_key)] = (
                task.id
            )
        self.screenshot_task_write_count += 1
        return self._copy_screenshot_task_record(task), False

    def get_screenshot_anchor_for_owner(self, *, owner_id: str, anchor_id: str) -> ScreenshotAnchorRecord | None:
        anchor = self.screenshot_anchors_by_id.get(anchor_id)
        if anchor is None or anchor.owner_id != owner_id:
            return None
        return self._copy_screenshot_anchor_record(anchor)

    def create_screenshot_anchor(
        self,
        *,
        owner_id: str,
        job_id: str,
        instruction_id: str,
        instruction_version_id: str,
        addressing_type: Literal["block_id", "char_range"],
        addressing_block_id: str | None,
        addressing_char_range: CharRange | None,
        addressing_strategy: str,
    ) -> ScreenshotAnchorRecord:
        now = datetime.now(UTC)
        anchor = ScreenshotAnchorRecord(
            anchor_id=f"anchor-{uuid4()}",
            owner_id=owner_id,
            job_id=job_id,
            instruction_id=instruction_id,
            instruction_version_id=instruction_version_id,
            active_asset_id=None,
            latest_asset_version=0,
            created_at=now,
            updated_at=now,
            addressing_type=addressing_type,
            addressing_block_id=addressing_block_id,
            addressing_char_range=addressing_char_range.model_copy(deep=True)
            if addressing_char_range is not None
            else None,
            addressing_strategy=addressing_strategy,
        )
        self.screenshot_anchors_by_id[anchor.anchor_id] = anchor
        self.screenshot_asset_ids_by_anchor.setdefault(anchor.anchor_id, [])
        return self._copy_screenshot_anchor_record(anchor)

    def list_screenshot_anchors_for_owner_instruction(
        self,
        *,
        owner_id: str,
        instruction_id: str,
        instruction_version_id: str | None = None,
    ) -> list[ScreenshotAnchorRecord]:
        anchors: list[ScreenshotAnchorRecord] = []
        for anchor in self.screenshot_anchors_by_id.values():
            if anchor.owner_id != owner_id or anchor.instruction_id != instruction_id:
                continue
            if instruction_version_id is not None and anchor.instruction_version_id != instruction_version_id:
                continue
            anchors.append(self._copy_screenshot_anchor_record(anchor))

        anchors.sort(key=lambda record: (record.created_at, record.anchor_id))
        return anchors

    def get_screenshot_task_for_owner(self, *, owner_id: str, task_id: str) -> ScreenshotTaskRecord | None:
        task = self.screenshot_tasks_by_id.get(task_id)
        if task is None or task.owner_id != owner_id:
            return None
        return self._copy_screenshot_task_record(task)

    def get_screenshot_asset_for_owner(self, *, owner_id: str, asset_id: str) -> ScreenshotAssetRecord | None:
        asset = self.screenshot_assets_by_id.get(asset_id)
        if asset is None or asset.owner_id != owner_id:
            return None
        return self._copy_screenshot_asset_record(asset)

    def list_screenshot_assets_for_owner_anchor(
        self,
        *,
        owner_id: str,
        anchor_id: str,
        include_deleted_assets: bool = True,
    ) -> list[ScreenshotAssetRecord]:
        anchor = self.screenshot_anchors_by_id.get(anchor_id)
        if anchor is None or anchor.owner_id != owner_id:
            return []

        assets: list[ScreenshotAssetRecord] = []
        for asset_id in self.screenshot_asset_ids_by_anchor.get(anchor_id, []):
            asset = self.screenshot_assets_by_id.get(asset_id)
            if asset is None or asset.owner_id != owner_id:
                continue
            if not include_deleted_assets and asset.is_deleted:
                continue
            assets.append(self._copy_screenshot_asset_record(asset))
        assets.sort(key=lambda record: (record.version, record.created_at, record.asset_id))
        return assets

    def create_custom_upload_ticket(
        self,
        *,
        owner_id: str,
        job_id: str,
        payload: CreateCustomUploadRequest,
    ) -> CustomUploadRecord:
        if payload.mime_type.value not in _CUSTOM_UPLOAD_ALLOWED_MIME_TYPES:
            raise ValueError("unsupported mime type")
        if payload.size_bytes > _CUSTOM_UPLOAD_MAX_SIZE_BYTES:
            raise ValueError("upload size exceeds limit")
        normalized_filename = self._normalize_custom_upload_filename(payload.filename)

        now = datetime.now(UTC)
        upload_id = f"upload-{uuid4()}"
        expires_at = now + timedelta(minutes=15)
        ticket = CustomUploadRecord(
            upload_id=upload_id,
            owner_id=owner_id,
            job_id=job_id,
            filename=normalized_filename,
            requested_mime_type=payload.mime_type.value,
            requested_size_bytes=payload.size_bytes,
            requested_checksum_sha256=payload.checksum_sha256,
            upload_url=self._build_custom_upload_url(
                upload_id=upload_id,
                owner_id=owner_id,
                job_id=job_id,
                expires_at=expires_at,
            ),
            expires_at=expires_at,
            max_size_bytes=_CUSTOM_UPLOAD_MAX_SIZE_BYTES,
            allowed_mime_types=_CUSTOM_UPLOAD_ALLOWED_MIME_TYPES,
        )
        self.custom_uploads_by_id[upload_id] = ticket
        return self._copy_custom_upload_record(ticket)

    def get_custom_upload_for_owner(
        self,
        *,
        owner_id: str,
        job_id: str,
        upload_id: str,
    ) -> CustomUploadRecord | None:
        upload = self.custom_uploads_by_id.get(upload_id)
        if upload is None or upload.owner_id != owner_id or upload.job_id != job_id:
            return None
        return self._copy_custom_upload_record(upload)

    def confirm_custom_upload(
        self,
        *,
        owner_id: str,
        job_id: str,
        upload_id: str,
        payload: ConfirmCustomUploadRequest,
    ) -> tuple[ScreenshotAssetRecord, bool]:
        upload = self.custom_uploads_by_id.get(upload_id)
        if upload is None or upload.owner_id != owner_id or upload.job_id != job_id:
            raise ValueError("upload not found")
        now = datetime.now(UTC)
        if payload.mime_type.value not in upload.allowed_mime_types:
            raise ValueError("unsupported mime type")
        if payload.size_bytes > upload.max_size_bytes:
            raise ValueError("upload size exceeds limit")
        if payload.mime_type.value != upload.requested_mime_type:
            raise ValueError("upload mime mismatch")
        if payload.size_bytes != upload.requested_size_bytes:
            raise ValueError("upload size mismatch")
        if payload.checksum_sha256 != upload.requested_checksum_sha256:
            raise ValueError("upload checksum mismatch")

        if not upload.confirmed and now > upload.expires_at:
            raise ValueError("upload ticket expired")
        self._validate_custom_upload_ticket_signature(
            upload=upload,
            require_not_expired=not upload.confirmed,
            now=now,
        )

        if upload.confirmed:
            if (
                upload.confirmed_mime_type != payload.mime_type.value
                or upload.confirmed_size_bytes != payload.size_bytes
                or upload.confirmed_checksum_sha256 != payload.checksum_sha256
                or upload.confirmed_width != payload.width
                or upload.confirmed_height != payload.height
            ):
                raise ValueError("upload confirmation payload differs from first accepted payload")
            existing_asset = self.screenshot_assets_by_id.get(upload.confirmed_asset_id or "")
            if existing_asset is None or existing_asset.owner_id != owner_id:
                raise ValueError("upload confirmed asset not found")
            return self._copy_screenshot_asset_record(existing_asset), True

        confirmed_asset_id = f"asset-{uuid4()}"
        synthetic_anchor_id = f"upload-{upload.upload_id}"
        extension = self._resolve_custom_upload_extension(mime_type=payload.mime_type.value)
        confirmed_image_uri = f"s3://bucket/uploads/{upload.upload_id}/original{extension}"
        confirmed_asset = ScreenshotAssetRecord(
            asset_id=confirmed_asset_id,
            anchor_id=synthetic_anchor_id,
            owner_id=owner_id,
            job_id=job_id,
            version=1,
            previous_asset_id=None,
            extraction_key=None,
            kind="UPLOADED",
            image_uri=confirmed_image_uri,
            mime_type=payload.mime_type.value,
            width=payload.width,
            height=payload.height,
            checksum_sha256=payload.checksum_sha256,
            upload_id=upload.upload_id,
            ops_hash=None,
            rendered_from_asset_id=None,
            is_deleted=False,
            extraction_parameters={"upload_id": upload.upload_id, "filename": upload.filename},
            created_at=now,
        )
        self.screenshot_assets_by_id[confirmed_asset_id] = confirmed_asset
        self.screenshot_asset_ids_by_anchor.setdefault(synthetic_anchor_id, []).append(confirmed_asset_id)

        upload.confirmed = True
        upload.confirmed_mime_type = payload.mime_type.value
        upload.confirmed_size_bytes = payload.size_bytes
        upload.confirmed_checksum_sha256 = payload.checksum_sha256
        upload.confirmed_width = payload.width
        upload.confirmed_height = payload.height
        upload.confirmed_asset_id = confirmed_asset_id
        upload.confirmed_image_uri = confirmed_image_uri
        upload.confirmed_at = now

        return self._copy_screenshot_asset_record(confirmed_asset), False

    def attach_confirmed_upload_to_anchor(
        self,
        *,
        owner_id: str,
        anchor_id: str,
        instruction_version_id: str,
        upload_id: str,
        idempotency_key: str | None,
        payload_signature: str,
    ) -> tuple[ScreenshotAnchorRecord, bool]:
        anchor = self.screenshot_anchors_by_id.get(anchor_id)
        if anchor is None or anchor.owner_id != owner_id:
            raise ValueError("screenshot anchor not found")

        upload = self.custom_uploads_by_id.get(upload_id)
        if upload is None or upload.owner_id != owner_id or upload.job_id != anchor.job_id or not upload.confirmed:
            raise ValueError("confirmed upload not found")

        if idempotency_key is not None:
            request_key = (owner_id, anchor_id, idempotency_key)
            existing = self.attach_upload_replay_by_owner_anchor_idempotency.get(request_key)
            if existing is not None:
                if existing.payload_signature != payload_signature:
                    raise ValueError("duplicate idempotency_key payload differs from first accepted request")
                replay_anchor = self._copy_screenshot_anchor_record(anchor)
                replay_anchor.active_asset_id = existing.asset_id
                replay_anchor.instruction_version_id = existing.instruction_version_id
                replay_anchor.updated_at = existing.updated_at
                return replay_anchor, True

        source_asset_id = upload.confirmed_asset_id
        if source_asset_id is None:
            raise ValueError("confirmed upload not found")
        source_asset = self.screenshot_assets_by_id.get(source_asset_id)
        if source_asset is None or source_asset.owner_id != owner_id:
            raise ValueError("confirmed upload asset not found")

        now = datetime.now(UTC)
        previous_asset_id = anchor.active_asset_id
        next_version = anchor.latest_asset_version + 1
        if previous_asset_id is not None:
            previous_asset = self.screenshot_assets_by_id.get(previous_asset_id)
            if previous_asset is not None and previous_asset.version >= next_version:
                next_version = previous_asset.version + 1

        asset_id = f"asset-{uuid4()}"
        attached_asset = ScreenshotAssetRecord(
            asset_id=asset_id,
            anchor_id=anchor_id,
            owner_id=owner_id,
            job_id=anchor.job_id,
            version=next_version,
            previous_asset_id=previous_asset_id,
            extraction_key=None,
            kind="UPLOADED",
            image_uri=source_asset.image_uri,
            mime_type=source_asset.mime_type,
            width=source_asset.width,
            height=source_asset.height,
            checksum_sha256=source_asset.checksum_sha256,
            upload_id=upload.upload_id,
            ops_hash=None,
            rendered_from_asset_id=None,
            is_deleted=False,
            extraction_parameters={"upload_id": upload.upload_id},
            created_at=now,
        )
        self.screenshot_assets_by_id[asset_id] = attached_asset
        self.screenshot_asset_ids_by_anchor.setdefault(anchor_id, []).append(asset_id)
        anchor.active_asset_id = asset_id
        anchor.latest_asset_version = next_version
        anchor.instruction_version_id = instruction_version_id
        anchor.updated_at = now

        if idempotency_key is not None:
            request_key = (owner_id, anchor_id, idempotency_key)
            self.attach_upload_replay_by_owner_anchor_idempotency[request_key] = AttachUploadReplayRecord(
                asset_id=asset_id,
                payload_signature=payload_signature,
                instruction_version_id=instruction_version_id,
                updated_at=now,
            )

        return self._copy_screenshot_anchor_record(anchor), False

    def apply_screenshot_annotations(
        self,
        *,
        owner_id: str,
        anchor_id: str,
        base_asset_id: str,
        operations: list[dict[str, Any]],
        idempotency_key: str | None,
    ) -> ScreenshotAnnotationResultRecord:
        anchor = self.screenshot_anchors_by_id.get(anchor_id)
        if anchor is None or anchor.owner_id != owner_id:
            raise ValueError("screenshot anchor not found")

        base_asset = self.screenshot_assets_by_id.get(base_asset_id)
        if base_asset is None or base_asset.owner_id != owner_id or base_asset.is_deleted:
            raise ValueError("screenshot asset not found")
        if base_asset.anchor_id != anchor_id or base_asset.job_id != anchor.job_id:
            raise ValueError("screenshot asset not linked to anchor")

        normalized_operations = self._normalize_annotation_operations(operations=operations)
        ops_hash = self.build_annotation_ops_hash(
            anchor_id=anchor_id,
            base_asset_id=base_asset_id,
            normalized_operations=normalized_operations,
        )
        payload_signature = self._build_annotation_payload_signature(
            base_asset_id=base_asset_id,
            normalized_operations=normalized_operations,
        )

        if idempotency_key is not None:
            request_key = (owner_id, anchor_id, idempotency_key)
            existing_replay = self.screenshot_annotation_replay_by_owner_anchor_idempotency.get(request_key)
            if existing_replay is not None:
                if existing_replay.payload_signature != payload_signature:
                    raise ValueError("duplicate idempotency_key payload differs from first accepted request")
                return ScreenshotAnnotationResultRecord(
                    anchor_id=existing_replay.anchor_id,
                    base_asset_id=existing_replay.base_asset_id,
                    ops_hash=existing_replay.ops_hash,
                    rendered_asset_id=existing_replay.rendered_asset_id,
                    active_asset_id=existing_replay.active_asset_id,
                    replayed=True,
                )

        annotation_key = (anchor_id, base_asset_id, ops_hash)
        existing_asset_id = self.screenshot_annotation_asset_id_by_anchor_base_ops_hash.get(annotation_key)
        if existing_asset_id is not None:
            existing_asset = self.screenshot_assets_by_id.get(existing_asset_id)
            if existing_asset is not None and existing_asset.owner_id == owner_id and not existing_asset.is_deleted:
                now = datetime.now(UTC)
                if anchor.active_asset_id != existing_asset_id:
                    anchor.active_asset_id = existing_asset_id
                    anchor.updated_at = now
                active_asset_id = anchor.active_asset_id or existing_asset_id
                result = ScreenshotAnnotationResultRecord(
                    anchor_id=anchor_id,
                    base_asset_id=base_asset_id,
                    ops_hash=ops_hash,
                    rendered_asset_id=existing_asset_id,
                    active_asset_id=active_asset_id,
                    replayed=True,
                )
                if idempotency_key is not None:
                    self.screenshot_annotation_replay_by_owner_anchor_idempotency[(owner_id, anchor_id, idempotency_key)] = (
                        AnnotationReplayRecord(
                            anchor_id=result.anchor_id,
                            base_asset_id=result.base_asset_id,
                            ops_hash=result.ops_hash,
                            rendered_asset_id=result.rendered_asset_id,
                            active_asset_id=result.active_asset_id,
                            payload_signature=payload_signature,
                        )
                    )
                return result
            self.screenshot_annotation_asset_id_by_anchor_base_ops_hash.pop(annotation_key, None)

        if self.annotation_render_failure_message is not None:
            message = self.annotation_render_failure_message
            self.annotation_render_failure_message = None
            raise ValueError(message)

        now = datetime.now(UTC)
        previous_asset_id = anchor.active_asset_id
        next_version = anchor.latest_asset_version + 1
        if previous_asset_id is not None:
            previous_asset = self.screenshot_assets_by_id.get(previous_asset_id)
            if previous_asset is not None and previous_asset.version >= next_version:
                next_version = previous_asset.version + 1

        rendered_asset_id = self._build_annotation_asset_id(
            anchor_id=anchor_id,
            base_asset_id=base_asset_id,
            ops_hash=ops_hash,
        )
        existing_rendered_asset = self.screenshot_assets_by_id.get(rendered_asset_id)
        if existing_rendered_asset is not None and not (
            existing_rendered_asset.anchor_id == anchor_id
            and existing_rendered_asset.rendered_from_asset_id == base_asset_id
            and existing_rendered_asset.ops_hash == ops_hash
        ):
            raise ValueError("annotation render collision")

        self.screenshot_assets_by_id[rendered_asset_id] = ScreenshotAssetRecord(
            asset_id=rendered_asset_id,
            anchor_id=anchor_id,
            owner_id=owner_id,
            job_id=anchor.job_id,
            version=next_version,
            previous_asset_id=previous_asset_id,
            extraction_key=None,
            kind="ANNOTATED",
            image_uri=self._build_annotation_render_image_uri(base_asset=base_asset, ops_hash=ops_hash),
            mime_type=base_asset.mime_type,
            width=base_asset.width,
            height=base_asset.height,
            checksum_sha256=None,
            upload_id=None,
            ops_hash=ops_hash,
            rendered_from_asset_id=base_asset_id,
            is_deleted=False,
            extraction_parameters={
                "base_asset_id": base_asset_id,
                "operations": json.loads(
                    json.dumps(
                        normalized_operations,
                        sort_keys=True,
                        separators=(",", ":"),
                        allow_nan=False,
                    )
                ),
            },
            created_at=now,
        )
        self.screenshot_asset_ids_by_anchor.setdefault(anchor_id, []).append(rendered_asset_id)
        anchor.active_asset_id = rendered_asset_id
        anchor.latest_asset_version = next_version
        anchor.updated_at = now
        self.screenshot_annotation_asset_id_by_anchor_base_ops_hash[annotation_key] = rendered_asset_id

        result = ScreenshotAnnotationResultRecord(
            anchor_id=anchor_id,
            base_asset_id=base_asset_id,
            ops_hash=ops_hash,
            rendered_asset_id=rendered_asset_id,
            active_asset_id=rendered_asset_id,
            replayed=False,
        )
        if idempotency_key is not None:
            self.screenshot_annotation_replay_by_owner_anchor_idempotency[(owner_id, anchor_id, idempotency_key)] = (
                AnnotationReplayRecord(
                    anchor_id=result.anchor_id,
                    base_asset_id=result.base_asset_id,
                    ops_hash=result.ops_hash,
                    rendered_asset_id=result.rendered_asset_id,
                    active_asset_id=result.active_asset_id,
                    payload_signature=payload_signature,
                )
            )
        return result

    def soft_delete_screenshot_asset(
        self,
        *,
        owner_id: str,
        anchor_id: str,
        asset_id: str,
    ) -> tuple[ScreenshotAnchorRecord, ScreenshotAssetRecord, bool]:
        anchor = self.screenshot_anchors_by_id.get(anchor_id)
        if anchor is None or anchor.owner_id != owner_id:
            raise ValueError("screenshot anchor not found")

        asset = self.screenshot_assets_by_id.get(asset_id)
        if asset is None or asset.owner_id != owner_id:
            raise ValueError("screenshot asset not found")
        if asset.anchor_id != anchor_id:
            raise ValueError("screenshot asset not linked to anchor")

        if asset.is_deleted:
            return self._copy_screenshot_anchor_record(anchor), self._copy_screenshot_asset_record(asset), True

        asset.is_deleted = True
        if anchor.active_asset_id == asset_id:
            anchor.active_asset_id = self._resolve_previous_active_asset_id(
                anchor_id=anchor_id,
                previous_asset_id=asset.previous_asset_id,
            )
        anchor.updated_at = datetime.now(UTC)
        return self._copy_screenshot_anchor_record(anchor), self._copy_screenshot_asset_record(asset), False

    def complete_screenshot_task_success(
        self,
        *,
        task_id: str,
        image_uri: str,
        width: int,
        height: int,
        anchor_id: str | None = None,
        asset_id: str | None = None,
    ) -> ScreenshotTaskRecord:
        task = self.screenshot_tasks_by_id.get(task_id)
        if task is None:
            raise ValueError("screenshot task not found")
        if task.status is ScreenshotTaskStatus.SUCCEEDED:
            return self._copy_screenshot_task_record(task)

        now = datetime.now(UTC)
        resolved_anchor_id = anchor_id or task.anchor_id or f"anchor-{uuid4()}"
        resolved_asset_id = asset_id or task.asset_id or f"asset-{uuid4()}"

        anchor_record = self.screenshot_anchors_by_id.get(resolved_anchor_id)
        if anchor_record is None:
            addressing_type: Literal["block_id", "char_range"] = "char_range" if task.char_range is not None else "block_id"
            anchor_record = ScreenshotAnchorRecord(
                anchor_id=resolved_anchor_id,
                owner_id=task.owner_id,
                job_id=task.job_id,
                instruction_id=task.instruction_id,
                instruction_version_id=task.instruction_version_id,
                active_asset_id=None,
                latest_asset_version=0,
                created_at=now,
                updated_at=now,
                addressing_type=addressing_type,
                addressing_block_id=task.block_id,
                addressing_char_range=task.char_range.model_copy(deep=True) if task.char_range is not None else None,
                addressing_strategy=task.strategy.value,
            )
            self.screenshot_anchors_by_id[resolved_anchor_id] = anchor_record
        elif anchor_record.owner_id != task.owner_id:
            raise ValueError("screenshot anchor owner mismatch")

        previous_asset_id = anchor_record.active_asset_id
        next_version = anchor_record.latest_asset_version + 1
        if previous_asset_id is not None:
            previous_asset = self.screenshot_assets_by_id.get(previous_asset_id)
            if previous_asset is not None and previous_asset.version >= next_version:
                next_version = previous_asset.version + 1

        if task.operation is ScreenshotOperation.REPLACE and previous_asset_id is None:
            raise ValueError("screenshot anchor has no active asset to replace")

        task.status = ScreenshotTaskStatus.SUCCEEDED
        task.anchor_id = resolved_anchor_id
        task.asset_id = resolved_asset_id
        task.failure_code = None
        task.failure_message = None
        task.updated_at = now
        self.screenshot_task_write_count += 1

        extraction_parameters: dict[str, Any] = {
            "instruction_id": task.instruction_id,
            "instruction_version_id": task.instruction_version_id,
            "timestamp_ms": task.timestamp_ms,
            "offset_ms": task.offset_ms,
            "strategy": task.strategy.value,
            "format": task.image_format,
        }
        if task.block_id is not None:
            extraction_parameters["block_id"] = task.block_id
        if task.char_range is not None:
            extraction_parameters["char_range"] = task.char_range.model_dump(mode="json")

        self.screenshot_assets_by_id[resolved_asset_id] = ScreenshotAssetRecord(
            asset_id=resolved_asset_id,
            anchor_id=resolved_anchor_id,
            owner_id=task.owner_id,
            job_id=task.job_id,
            version=next_version,
            previous_asset_id=previous_asset_id,
            extraction_key=task.canonical_key,
            kind="EXTRACTED",
            image_uri=image_uri,
            mime_type=self._resolve_screenshot_mime_type(image_format=task.image_format),
            width=width,
            height=height,
            checksum_sha256=None,
            upload_id=None,
            ops_hash=None,
            rendered_from_asset_id=None,
            is_deleted=False,
            extraction_parameters=extraction_parameters,
            created_at=now,
        )
        self.screenshot_asset_ids_by_anchor.setdefault(resolved_anchor_id, []).append(resolved_asset_id)
        anchor_record.active_asset_id = resolved_asset_id
        anchor_record.latest_asset_version = next_version
        anchor_record.instruction_version_id = task.instruction_version_id
        anchor_record.updated_at = now
        return self._copy_screenshot_task_record(task)

    def fail_screenshot_task(
        self,
        *,
        task_id: str,
        failure_code: str,
        failure_message: str | None = None,
    ) -> ScreenshotTaskRecord:
        task = self.screenshot_tasks_by_id.get(task_id)
        if task is None:
            raise ValueError("screenshot task not found")

        task.status = ScreenshotTaskStatus.FAILED
        task.failure_code = failure_code
        task.failure_message = self._sanitize_screenshot_failure_message(failure_message)
        task.updated_at = datetime.now(UTC)
        self.screenshot_task_write_count += 1
        return self._copy_screenshot_task_record(task)

    def persist_retry_metadata(
        self,
        *,
        job: JobRecord,
        client_request_id: str,
        payload_signature: str,
        resume_from_status: JobStatus,
        checkpoint_ref: str,
        model_profile: str,
        dispatch_id: str,
    ) -> None:
        now = datetime.now(UTC)
        job.retry_resume_from_status = resume_from_status
        job.retry_checkpoint_ref = checkpoint_ref
        job.retry_model_profile = model_profile
        job.retry_client_request_id = client_request_id
        job.retry_dispatch_id = dispatch_id
        job.updated_at = now
        self.job_write_count += 1
        self.retry_requests_by_job_and_client[(job.id, client_request_id)] = RetryRequestRecord(
            job_id=job.id,
            client_request_id=client_request_id,
            payload_signature=payload_signature,
            resume_from_status=resume_from_status,
            checkpoint_ref=checkpoint_ref,
            model_profile=model_profile,
            dispatch_id=dispatch_id,
            created_at=now,
        )

    def create_dispatch_for_job(
        self,
        *,
        job_id: str,
        payload: dict[str, str],
        dispatch_type: Literal["run", "retry"] = "run",
    ) -> WorkflowDispatchRecord:
        if self.dispatch_failure_message is not None:
            message = self.dispatch_failure_message
            self.dispatch_failure_message = None
            raise RuntimeError(message)

        dispatch = WorkflowDispatchRecord(
            job_id=job_id,
            dispatch_id=f"dispatch-{uuid4()}",
            dispatch_type=dispatch_type,
            payload=dict(payload),
            created_at=datetime.now(UTC),
        )
        self.workflow_dispatches_by_job[job_id] = dispatch
        self.dispatch_write_count += 1
        return dispatch

    @staticmethod
    def _build_regenerate_payload_signature(
        *,
        base_version: int,
        selection: RegenerateSelection,
        context: str | None,
        model_profile: str | None,
        prompt_template_id: str | None,
        prompt_params_ref: str | None,
    ) -> str:
        signature_payload = {
            "base_version": base_version,
            "selection": selection.model_dump(mode="json", exclude_none=True),
            "context": context,
            "model_profile": model_profile,
            "prompt_template_id": prompt_template_id,
            "prompt_params_ref": prompt_params_ref,
        }
        return json.dumps(signature_payload, sort_keys=True, separators=(",", ":"))

    def _resolve_previous_active_asset_id(self, *, anchor_id: str, previous_asset_id: str | None) -> str | None:
        candidate_id = previous_asset_id
        visited: set[str] = set()
        while candidate_id is not None:
            if candidate_id in visited:
                return None
            visited.add(candidate_id)
            candidate = self.screenshot_assets_by_id.get(candidate_id)
            if candidate is None or candidate.anchor_id != anchor_id:
                return None
            if not candidate.is_deleted:
                return candidate.asset_id
            candidate_id = candidate.previous_asset_id
        return None

    @staticmethod
    def build_screenshot_extraction_canonical_key(
        *,
        job_id: str,
        instruction_version_id: str,
        timestamp_ms: int,
        offset_ms: int,
        strategy: ScreenshotStrategy,
        image_format: ScreenshotFormat,
    ) -> str:
        return "|".join(
            (
                job_id,
                instruction_version_id,
                str(timestamp_ms),
                str(offset_ms),
                strategy.value,
                image_format.value,
            )
        )

    @classmethod
    def build_annotation_ops_hash(
        cls,
        *,
        anchor_id: str,
        base_asset_id: str,
        normalized_operations: list[dict[str, Any]],
    ) -> str:
        payload = {
            "anchor_id": anchor_id,
            "base_asset_id": base_asset_id,
            "operations": normalized_operations,
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @classmethod
    def _build_annotation_payload_signature(
        cls,
        *,
        base_asset_id: str,
        normalized_operations: list[dict[str, Any]],
    ) -> str:
        payload = {
            "base_asset_id": base_asset_id,
            "operations": normalized_operations,
        }
        return json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )

    @staticmethod
    def _build_annotation_asset_id(*, anchor_id: str, base_asset_id: str, ops_hash: str) -> str:
        material = f"{anchor_id}|{base_asset_id}|{ops_hash}".encode("utf-8")
        return f"asset-{hashlib.sha256(material).hexdigest()[:32]}"

    @staticmethod
    def _build_annotation_render_image_uri(*, base_asset: ScreenshotAssetRecord, ops_hash: str) -> str:
        extension = _CUSTOM_UPLOAD_MIME_TO_EXTENSION.get(base_asset.mime_type, ".png")
        return f"s3://bucket/screenshots/annotated/{base_asset.anchor_id}/{ops_hash}{extension}"

    @classmethod
    def _normalize_annotation_operations(cls, *, operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized_operations: list[dict[str, Any]] = []
        for operation in operations:
            op_type = operation.get("op_type")
            geometry = operation.get("geometry")
            style = operation.get("style")
            if op_type not in _ANNOTATION_ALLOWED_OP_TYPES:
                raise ValueError("invalid annotation operations")
            if not isinstance(geometry, dict) or not isinstance(style, dict):
                raise ValueError("invalid annotation operations")
            normalized_operation = {
                "op_type": op_type,
                "geometry": cls._normalize_annotation_value(geometry),
                "style": cls._normalize_annotation_value(style),
            }
            normalized_operations.append(normalized_operation)

        if not normalized_operations:
            raise ValueError("invalid annotation operations")

        normalized_operations.sort(
            key=lambda operation: json.dumps(
                operation,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        )
        return normalized_operations

    @classmethod
    def _normalize_annotation_value(cls, value: Any) -> Any:
        if isinstance(value, dict):
            normalized: dict[str, Any] = {}
            for key in sorted(value.keys()):
                if not isinstance(key, str):
                    raise ValueError("invalid annotation operations")
                normalized[key] = cls._normalize_annotation_value(value[key])
            return normalized
        if isinstance(value, list):
            return [cls._normalize_annotation_value(item) for item in value]
        if isinstance(value, bool) or isinstance(value, int) or isinstance(value, str) or value is None:
            return value
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                raise ValueError("invalid annotation operations")
            return value
        raise ValueError("invalid annotation operations")

    @staticmethod
    def _build_screenshot_payload_signature(*, payload: ScreenshotExtractionRequest) -> str:
        signature_payload = payload.model_dump(mode="json", exclude_none=True)
        return json.dumps(signature_payload, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _build_screenshot_replace_payload_signature(*, payload: ScreenshotReplaceRequest) -> str:
        signature_payload = payload.model_dump(mode="json", exclude_none=True)
        return json.dumps(signature_payload, sort_keys=True, separators=(",", ":"))

    def _build_export_download_url(
        self,
        *,
        owner_id: str,
        export_id: str,
        export_format: ExportFormat,
        expires_at: datetime,
    ) -> str:
        expires_epoch = int(expires_at.timestamp())
        extension = _EXPORT_FORMAT_TO_EXTENSION.get(export_format, ".bin")
        filename = f"{export_id}{extension}"
        signature = self._build_export_download_signature(
            owner_id=owner_id,
            export_id=export_id,
            filename=filename,
            expires_epoch=expires_epoch,
        )
        return (
            f"{_EXPORT_DOWNLOAD_URL_SCHEME}://{self.export_download_url_host}/exports/{export_id}/{filename}"
            f"?expires={expires_epoch}&sig={signature}"
        )

    def _build_export_download_signature(
        self,
        *,
        owner_id: str,
        export_id: str,
        filename: str,
        expires_epoch: int,
    ) -> str:
        payload = f"{owner_id}|{export_id}|{filename}|{expires_epoch}".encode("utf-8")
        return hmac.new(self.export_download_signing_key, payload, hashlib.sha256).hexdigest()

    @staticmethod
    def _normalize_custom_upload_filename(filename: str) -> str:
        normalized = filename.strip().replace("\\", "/").split("/")[-1]
        if not normalized or normalized in {".", ".."}:
            raise ValueError("invalid filename")
        if len(normalized) > 255:
            raise ValueError("filename too long")
        if any(ord(char) < 32 for char in normalized):
            raise ValueError("filename contains invalid characters")
        return normalized

    @classmethod
    def _build_custom_upload_url(
        cls,
        *,
        upload_id: str,
        owner_id: str,
        job_id: str,
        expires_at: datetime,
    ) -> str:
        expires_epoch = int(expires_at.timestamp())
        signature = cls._build_custom_upload_signature(
            upload_id=upload_id,
            owner_id=owner_id,
            job_id=job_id,
            expires_epoch=expires_epoch,
        )
        return (
            f"{_CUSTOM_UPLOAD_URL_SCHEME}://{_CUSTOM_UPLOAD_URL_HOST}/{upload_id}"
            f"?expires={expires_epoch}&sig={signature}"
        )

    @classmethod
    def _build_custom_upload_signature(
        cls,
        *,
        upload_id: str,
        owner_id: str,
        job_id: str,
        expires_epoch: int,
    ) -> str:
        payload = f"{upload_id}|{owner_id}|{job_id}|{expires_epoch}".encode("utf-8")
        return hmac.new(_CUSTOM_UPLOAD_SIGNING_KEY, payload, hashlib.sha256).hexdigest()

    @classmethod
    def _validate_custom_upload_ticket_signature(
        cls,
        *,
        upload: CustomUploadRecord,
        require_not_expired: bool,
        now: datetime,
    ) -> None:
        parsed = urlparse(upload.upload_url)
        if parsed.scheme != _CUSTOM_UPLOAD_URL_SCHEME or parsed.netloc != _CUSTOM_UPLOAD_URL_HOST:
            raise ValueError("upload ticket signature invalid")
        if parsed.path != f"/{upload.upload_id}":
            raise ValueError("upload ticket signature invalid")

        params = parse_qs(parsed.query, keep_blank_values=False)
        expires_values = params.get("expires")
        signature_values = params.get("sig")
        if not expires_values or not signature_values:
            raise ValueError("upload ticket signature invalid")
        if len(expires_values) != 1 or len(signature_values) != 1:
            raise ValueError("upload ticket signature invalid")

        try:
            expires_epoch = int(expires_values[0])
        except ValueError as exc:
            raise ValueError("upload ticket signature invalid") from exc

        expected_expires_epoch = int(upload.expires_at.timestamp())
        if expires_epoch != expected_expires_epoch:
            raise ValueError("upload ticket signature invalid")
        if require_not_expired and now.timestamp() > expires_epoch:
            raise ValueError("upload ticket expired")

        expected_signature = cls._build_custom_upload_signature(
            upload_id=upload.upload_id,
            owner_id=upload.owner_id,
            job_id=upload.job_id,
            expires_epoch=expires_epoch,
        )
        if not hmac.compare_digest(signature_values[0], expected_signature):
            raise ValueError("upload ticket signature invalid")

    @staticmethod
    def _resolve_custom_upload_extension(*, mime_type: str) -> str:
        return _CUSTOM_UPLOAD_MIME_TO_EXTENSION.get(mime_type, ".bin")

    @staticmethod
    def _resolve_screenshot_mime_type(*, image_format: str) -> str:
        return _SCREENSHOT_FORMAT_TO_MIME_TYPE.get(image_format, ScreenshotMimeType.PNG.value)

    @staticmethod
    def _sanitize_regenerate_failure_message(message: str | None) -> str | None:
        if message is None:
            return None
        return "Regenerate task failed."

    @staticmethod
    def _sanitize_screenshot_failure_message(message: str | None) -> str | None:
        if message is None:
            return None
        return "Screenshot task failed."

    @staticmethod
    def _copy_regenerate_task_record(record: RegenerateTaskRecord) -> RegenerateTaskRecord:
        return RegenerateTaskRecord(
            id=record.id,
            instruction_id=record.instruction_id,
            owner_id=record.owner_id,
            job_id=record.job_id,
            status=record.status,
            progress_pct=record.progress_pct,
            instruction_version=record.instruction_version,
            failure_code=record.failure_code,
            failure_message=record.failure_message,
            failed_stage=record.failed_stage,
            provenance=record.provenance.model_copy(deep=True),
            payload_signature=record.payload_signature,
            client_request_id=record.client_request_id,
            requested_at=record.requested_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _copy_screenshot_task_record(record: ScreenshotTaskRecord) -> ScreenshotTaskRecord:
        return ScreenshotTaskRecord(
            id=record.id,
            owner_id=record.owner_id,
            job_id=record.job_id,
            instruction_id=record.instruction_id,
            instruction_version_id=record.instruction_version_id,
            operation=record.operation,
            status=record.status,
            timestamp_ms=record.timestamp_ms,
            offset_ms=record.offset_ms,
            strategy=record.strategy,
            image_format=record.image_format,
            anchor_id=record.anchor_id,
            block_id=record.block_id,
            char_range=record.char_range.model_copy(deep=True) if record.char_range is not None else None,
            idempotency_key=record.idempotency_key,
            canonical_key=record.canonical_key,
            payload_signature=record.payload_signature,
            asset_id=record.asset_id,
            failure_code=record.failure_code,
            failure_message=record.failure_message,
            requested_at=record.requested_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _copy_screenshot_anchor_record(record: ScreenshotAnchorRecord) -> ScreenshotAnchorRecord:
        return ScreenshotAnchorRecord(
            anchor_id=record.anchor_id,
            owner_id=record.owner_id,
            job_id=record.job_id,
            instruction_id=record.instruction_id,
            instruction_version_id=record.instruction_version_id,
            active_asset_id=record.active_asset_id,
            latest_asset_version=record.latest_asset_version,
            created_at=record.created_at,
            updated_at=record.updated_at,
            addressing_type=record.addressing_type,
            addressing_block_id=record.addressing_block_id,
            addressing_char_range=record.addressing_char_range.model_copy(deep=True)
            if record.addressing_char_range is not None
            else None,
            addressing_strategy=record.addressing_strategy,
        )

    @staticmethod
    def _copy_screenshot_asset_record(record: ScreenshotAssetRecord) -> ScreenshotAssetRecord:
        return ScreenshotAssetRecord(
            asset_id=record.asset_id,
            anchor_id=record.anchor_id,
            owner_id=record.owner_id,
            job_id=record.job_id,
            version=record.version,
            previous_asset_id=record.previous_asset_id,
            extraction_key=record.extraction_key,
            kind=record.kind,
            image_uri=record.image_uri,
            mime_type=record.mime_type,
            width=record.width,
            height=record.height,
            checksum_sha256=record.checksum_sha256,
            upload_id=record.upload_id,
            ops_hash=record.ops_hash,
            rendered_from_asset_id=record.rendered_from_asset_id,
            is_deleted=record.is_deleted,
            extraction_parameters=dict(record.extraction_parameters),
            created_at=record.created_at,
        )

    @staticmethod
    def _copy_custom_upload_record(record: CustomUploadRecord) -> CustomUploadRecord:
        return CustomUploadRecord(
            upload_id=record.upload_id,
            owner_id=record.owner_id,
            job_id=record.job_id,
            filename=record.filename,
            requested_mime_type=record.requested_mime_type,
            requested_size_bytes=record.requested_size_bytes,
            requested_checksum_sha256=record.requested_checksum_sha256,
            upload_url=record.upload_url,
            expires_at=record.expires_at,
            max_size_bytes=record.max_size_bytes,
            allowed_mime_types=tuple(record.allowed_mime_types),
            confirmed=record.confirmed,
            confirmed_mime_type=record.confirmed_mime_type,
            confirmed_size_bytes=record.confirmed_size_bytes,
            confirmed_checksum_sha256=record.confirmed_checksum_sha256,
            confirmed_width=record.confirmed_width,
            confirmed_height=record.confirmed_height,
            confirmed_asset_id=record.confirmed_asset_id,
            confirmed_image_uri=record.confirmed_image_uri,
            confirmed_at=record.confirmed_at,
        )

    @staticmethod
    def _copy_export_record(record: ExportRecord) -> ExportRecord:
        return ExportRecord(
            export_id=record.export_id,
            owner_id=record.owner_id,
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
    def _copy_export_manifest_linkage_record(record: ExportManifestLinkageRecord) -> ExportManifestLinkageRecord:
        return ExportManifestLinkageRecord(
            export_id=record.export_id,
            identity_key=record.identity_key,
            linked_at=record.linked_at,
        )

    def _append_export_audit_record(
        self,
        *,
        event_type: ExportAuditEventType,
        export_record: ExportRecord,
        occurred_at: datetime,
        correlation_id: str | None,
    ) -> None:
        self.export_audit_events.append(
            ExportAuditRecord(
                event_type=event_type,
                export_id=export_record.export_id,
                identity_key=export_record.identity_key,
                occurred_at=occurred_at,
                recorded_at=datetime.now(UTC),
                correlation_id=self._normalize_export_audit_correlation_id(correlation_id),
            )
        )
        self.export_audit_write_count += 1

    @staticmethod
    def _normalize_export_audit_correlation_id(correlation_id: str | None) -> str:
        if correlation_id is not None:
            normalized = correlation_id.strip()
            if normalized:
                return normalized
        return f"corr-export-{uuid4()}"

    def _get_export_record_for_owner_mutable(
        self,
        *,
        owner_id: str,
        export_id: str,
    ) -> ExportRecord | None:
        record = self.exports_by_id.get(export_id)
        if record is None or record.owner_id != owner_id:
            return None
        return record

    @staticmethod
    def _copy_instruction_record(record: InstructionRecord) -> InstructionRecord:
        return InstructionRecord(
            instruction_id=record.instruction_id,
            job_id=record.job_id,
            owner_id=record.owner_id,
            version=record.version,
            markdown=record.markdown,
            updated_at=record.updated_at,
            validation_status=record.validation_status,
            validation_errors=[issue.model_copy(deep=True) for issue in record.validation_errors]
            if record.validation_errors is not None
            else None,
            validated_at=record.validated_at,
            validator_version=record.validator_version,
            model_profile_id=record.model_profile_id,
            prompt_template_id=record.prompt_template_id,
            prompt_params_ref=record.prompt_params_ref,
        )
