"""Project service layer."""

from app.errors import ApiError
from app.repositories.memory import InMemoryStore
from app.schemas.project import Project


class ProjectService:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def create_project(self, *, owner_id: str, name: str) -> Project:
        record = self._store.create_project(owner_id=owner_id, name=name)
        return Project(id=record.id, name=record.name, created_at=record.created_at)

    def list_projects(self, *, owner_id: str) -> list[Project]:
        return [
            Project(id=record.id, name=record.name, created_at=record.created_at)
            for record in self._store.list_projects_for_owner(owner_id)
        ]

    def get_project(self, *, owner_id: str, project_id: str) -> Project:
        record = self._store.get_project_for_owner(owner_id=owner_id, project_id=project_id)
        if record is None:
            raise ApiError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found")

        return Project(id=record.id, name=record.name, created_at=record.created_at)
