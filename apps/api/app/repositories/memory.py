"""In-memory repositories used by the API scaffold and tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from typing import Literal
from uuid import uuid4

from app.schemas.job import ArtifactManifest, JobStatus


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
class WorkflowDispatchRecord:
    job_id: str
    dispatch_id: str
    payload: dict[str, str]
    created_at: datetime


@dataclass(slots=True)
class InMemoryStore:
    """Simple, deterministic persistence layer for scaffolding and tests."""

    projects: dict[str, ProjectRecord] = field(default_factory=dict)
    jobs: dict[str, JobRecord] = field(default_factory=dict)
    callback_events: dict[tuple[str, str], CallbackEventRecord] = field(default_factory=dict)
    latest_callback_at_by_job: dict[str, datetime] = field(default_factory=dict)
    workflow_dispatches_by_job: dict[str, WorkflowDispatchRecord] = field(default_factory=dict)
    project_write_count: int = 0
    job_write_count: int = 0
    dispatch_write_count: int = 0
    dispatch_failure_message: str | None = None

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

    def get_dispatch_for_job(self, job_id: str) -> WorkflowDispatchRecord | None:
        return self.workflow_dispatches_by_job.get(job_id)

    def create_dispatch_for_job(self, *, job_id: str, payload: dict[str, str]) -> WorkflowDispatchRecord:
        if self.dispatch_failure_message is not None:
            message = self.dispatch_failure_message
            self.dispatch_failure_message = None
            raise RuntimeError(message)

        dispatch = WorkflowDispatchRecord(
            job_id=job_id,
            dispatch_id=f"dispatch-{uuid4()}",
            payload=dict(payload),
            created_at=datetime.now(UTC),
        )
        self.workflow_dispatches_by_job[job_id] = dispatch
        self.dispatch_write_count += 1
        return dispatch
