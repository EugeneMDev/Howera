"""Project service layer."""

from app.repositories.memory import InMemoryStore
from app.schemas.project import Project


class ProjectService:
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    def create_project(self, *, owner_id: str, name: str) -> Project:
        record = self._store.create_project(owner_id=owner_id, name=name)
        return Project(id=record.id, name=record.name, created_at=record.created_at)
