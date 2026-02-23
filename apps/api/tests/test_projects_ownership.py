"""Ownership and no-leak project API tests for Story 1.2."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.errors import ApiError
from app.main import create_app
from app.repositories.memory import InMemoryStore
from app.services.projects import ProjectService


class _SettingsEnvCase(unittest.TestCase):
    _env_keys = (
        "HOWERA_AUTH_PROVIDER",
        "HOWERA_CALLBACK_SECRET",
        "HOWERA_FIREBASE_PROJECT_ID",
        "HOWERA_FIREBASE_AUDIENCE",
    )

    def setUp(self) -> None:
        self._old_env = {k: os.environ.get(k) for k in self._env_keys}
        os.environ["HOWERA_AUTH_PROVIDER"] = "mock"
        os.environ["HOWERA_CALLBACK_SECRET"] = "test-callback-secret"
        os.environ["HOWERA_FIREBASE_PROJECT_ID"] = "test-project"
        os.environ["HOWERA_FIREBASE_AUDIENCE"] = "test-audience"
        get_settings.cache_clear()

    def tearDown(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()


class ProjectOwnershipApiTests(_SettingsEnvCase):
    def test_create_list_and_get_are_owner_scoped(self) -> None:
        app = create_app()
        client = TestClient(app)

        user_a_headers = {"Authorization": "Bearer test:user-a:editor"}
        user_b_headers = {"Authorization": "Bearer test:user-b:editor"}

        create_a = client.post("/api/v1/projects", headers=user_a_headers, json={"name": "A Project"})
        self.assertEqual(create_a.status_code, 201)
        project_a = create_a.json()

        create_b = client.post("/api/v1/projects", headers=user_b_headers, json={"name": "B Project"})
        self.assertEqual(create_b.status_code, 201)
        project_b = create_b.json()

        self.assertIn("id", project_a)
        self.assertIn("name", project_a)
        self.assertIn("created_at", project_a)
        self.assertNotIn("owner_id", project_a)

        list_a = client.get("/api/v1/projects", headers=user_a_headers)
        self.assertEqual(list_a.status_code, 200)
        self.assertEqual([p["id"] for p in list_a.json()], [project_a["id"]])

        list_b = client.get("/api/v1/projects", headers=user_b_headers)
        self.assertEqual(list_b.status_code, 200)
        self.assertEqual([p["id"] for p in list_b.json()], [project_b["id"]])

        get_a = client.get(f"/api/v1/projects/{project_a['id']}", headers=user_a_headers)
        self.assertEqual(get_a.status_code, 200)
        self.assertEqual(get_a.json()["id"], project_a["id"])

    def test_cross_owner_access_and_missing_project_share_no_leak_404_shape(self) -> None:
        app = create_app()
        client = TestClient(app)

        owner_headers = {"Authorization": "Bearer test:owner:editor"}
        other_headers = {"Authorization": "Bearer test:other:editor"}

        created = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owner Project"})
        self.assertEqual(created.status_code, 201)
        project_id = created.json()["id"]

        cross_owner = client.get(f"/api/v1/projects/{project_id}", headers=other_headers)
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing = client.get("/api/v1/projects/nonexistent-project-id", headers=other_headers)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

    def test_owner_id_is_persisted_for_project_creation(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test:owner-123:editor"},
            json={"name": "Owned"},
        )
        self.assertEqual(response.status_code, 201)
        project_id = response.json()["id"]
        stored_project = app.state.store.get_project(project_id)

        self.assertIsNotNone(stored_project)
        assert stored_project is not None
        self.assertEqual(stored_project.owner_id, "owner-123")


class ProjectOwnershipUnitTests(unittest.TestCase):
    def test_repository_and_service_scope_projects_to_owner(self) -> None:
        store = InMemoryStore()
        service = ProjectService(store)

        project_a = service.create_project(owner_id="user-a", name="Project A")
        project_b = service.create_project(owner_id="user-b", name="Project B")

        listed_for_a = service.list_projects(owner_id="user-a")
        self.assertEqual([project.id for project in listed_for_a], [project_a.id])

        loaded_for_a = service.get_project(owner_id="user-a", project_id=project_a.id)
        self.assertEqual(loaded_for_a.id, project_a.id)

        with self.assertRaises(ApiError) as context:
            service.get_project(owner_id="user-a", project_id=project_b.id)
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.payload.code, "RESOURCE_NOT_FOUND")
