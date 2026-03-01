"""In-memory repositories used by the API scaffold and tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from typing import Literal
from uuid import uuid4

from pydantic import ValidationError

from app.domain.job_fsm import ensure_transition
from app.schemas.instruction import ValidationIssue, ValidationStatus
from app.schemas.job import ArtifactManifest, JobStatus, TranscriptSegment

_IMMUTABLE_RAW_ARTIFACT_KEYS = frozenset({"video_uri", "audio_uri", "transcript_uri"})
_MUTABLE_ARTIFACT_KEYS = frozenset({"draft_uri", "exports"})
_TRANSITION_AUDIT_EVENT_TYPE = "JOB_STATUS_TRANSITION_APPLIED"
_CALLBACK_FAILPOINT_STAGES = (
    "after_status",
    "after_manifest",
    "after_failure_metadata",
    "after_callback_event",
)


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
    transcript_segments_by_job: dict[str, list[TranscriptSegment]] = field(default_factory=dict)
    project_write_count: int = 0
    job_write_count: int = 0
    instruction_write_count: int = 0
    dispatch_write_count: int = 0
    dispatch_failure_message: str | None = None
    callback_mutation_failpoint_event_id: str | None = None
    callback_mutation_failpoint_stage: Literal[
        "after_status",
        "after_manifest",
        "after_failure_metadata",
        "after_callback_event",
    ] | None = None
    callback_mutation_failpoint_message: str = "Injected callback persistence failure"

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
        validation_status: ValidationStatus = ValidationStatus.PASS,
        updated_at: datetime | None = None,
        validation_errors: list[ValidationIssue] | None = None,
        validated_at: datetime | None = None,
        validator_version: str | None = None,
        model_profile_id: str | None = None,
        prompt_template_id: str | None = None,
        prompt_params_ref: str | None = None,
    ) -> InstructionRecord:
        if version < 1:
            raise ValueError("instruction version must be >= 1")

        history = self.instructions_by_id.setdefault(instruction_id, [])
        if any(record.version == version for record in history):
            raise ValueError("instruction version already exists")

        record = InstructionRecord(
            instruction_id=instruction_id,
            job_id=job_id,
            owner_id=owner_id,
            version=version,
            markdown=markdown,
            updated_at=updated_at or datetime.now(UTC),
            validation_status=validation_status,
            validation_errors=[issue.model_copy(deep=True) for issue in validation_errors]
            if validation_errors is not None
            else None,
            validated_at=validated_at,
            validator_version=validator_version,
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

        try:
            if job.status is JobStatus.FAILED and job.retry_resume_from_status is not None and job.retry_dispatch_id is not None:
                # Retry accepts from FAILED; subsequent callbacks are validated from persisted checkpoint resume status.
                self.transition_job_status_from_retry_checkpoint(job=job, new_status=callback_event.status)
            else:
                self.transition_job_status(job=job, new_status=callback_event.status)
            self._maybe_raise_callback_failpoint(event_id=callback_event.event_id, stage="after_status")

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
            raise

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
