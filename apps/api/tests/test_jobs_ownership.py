"""Ownership and no-leak job API tests for Story 1.3."""

from __future__ import annotations

import os
import unittest

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.errors import ApiError
from app.main import create_app
from app.repositories.memory import InMemoryStore
from app.schemas.job import JobStatus
from app.services.jobs import JobService


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


class JobOwnershipApiTests(_SettingsEnvCase):
    def test_create_job_for_owned_project_sets_created_status(self) -> None:
        app = create_app()
        client = TestClient(app)
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        response = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers)

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["project_id"], project["id"])
        self.assertEqual(payload["status"], "CREATED")

    def test_create_job_cross_owner_or_missing_project_returns_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        owner_headers = {"Authorization": "Bearer test:owner-a:editor"}
        other_headers = {"Authorization": "Bearer test:owner-b:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "A"}).json()

        cross_owner = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=other_headers)
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing = client.post("/api/v1/projects/project-missing/jobs", headers=other_headers)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

    def test_get_job_owner_only_and_no_leak_for_cross_owner_or_missing(self) -> None:
        app = create_app()
        client = TestClient(app)
        owner_headers = {"Authorization": "Bearer test:owner:editor"}
        other_headers = {"Authorization": "Bearer test:other:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()

        owned_get = client.get(f"/api/v1/jobs/{created_job['id']}", headers=owner_headers)
        self.assertEqual(owned_get.status_code, 200)
        self.assertEqual(owned_get.json()["id"], created_job["id"])

        cross_owner = client.get(f"/api/v1/jobs/{created_job['id']}", headers=other_headers)
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing = client.get("/api/v1/jobs/job-missing", headers=other_headers)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})


class JobOwnershipUnitTests(unittest.TestCase):
    def test_service_and_repository_scope_job_to_owner(self) -> None:
        store = InMemoryStore()
        project_a = store.create_project(owner_id="user-a", name="Project A")
        project_b = store.create_project(owner_id="user-b", name="Project B")
        service = JobService(store)

        job_a = service.create_job(owner_id="user-a", project_id=project_a.id)
        self.assertEqual(job_a.status, JobStatus.CREATED)

        loaded_a = service.get_job(owner_id="user-a", job_id=job_a.id)
        self.assertEqual(loaded_a.id, job_a.id)

        job_b = service.create_job(owner_id="user-b", project_id=project_b.id)
        with self.assertRaises(ApiError) as context:
            service.get_job(owner_id="user-a", job_id=job_b.id)
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.payload.code, "RESOURCE_NOT_FOUND")
