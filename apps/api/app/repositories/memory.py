"""In-memory repositories used by the API scaffold and tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4

from app.schemas.job import JobStatus


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


@dataclass(slots=True)
class InMemoryStore:
    """Simple, deterministic persistence layer for scaffolding and tests."""

    projects: dict[str, ProjectRecord] = field(default_factory=dict)
    jobs: dict[str, JobRecord] = field(default_factory=dict)
    project_write_count: int = 0
    job_write_count: int = 0

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
