"""Job service layer."""

from app.errors import ApiError
from app.repositories.memory import InMemoryStore
from app.schemas.job import Job


class JobService:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def create_job(self, *, owner_id: str, project_id: str) -> Job:
        project = self._store.get_project_for_owner(owner_id=owner_id, project_id=project_id)
        if project is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        record = self._store.create_job(owner_id=owner_id, project_id=project_id)
        return Job(
            id=record.id,
            project_id=record.project_id,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def get_job(self, *, owner_id: str, job_id: str) -> Job:
        record = self._store.get_job_for_owner(owner_id=owner_id, job_id=job_id)
        if record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        return Job(
            id=record.id,
            project_id=record.project_id,
            status=record.status,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
