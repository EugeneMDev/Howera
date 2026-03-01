"""Instruction ownership and version-selection tests for Story 4.2."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
import unittest

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.errors import ApiError
from app.main import create_app
from app.repositories.memory import InMemoryStore
from app.schemas.instruction import ValidationStatus
from app.services.instructions import InstructionService


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


class InstructionOwnershipApiTests(_SettingsEnvCase):
    def test_get_instruction_latest_version_by_default_returns_required_fields(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = store.create_project(owner_id="owner-1", name="Owned")
        job = store.create_job(owner_id="owner-1", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-1",
            instruction_id="inst-1",
            job_id=job.id,
            version=1,
            markdown="# v1",
            validation_status=ValidationStatus.FAIL,
        )
        store.create_instruction_version(
            owner_id="owner-1",
            instruction_id="inst-1",
            job_id=job.id,
            version=2,
            markdown="# v2",
            validation_status=ValidationStatus.PASS,
        )

        response = client.get("/api/v1/instructions/inst-1", headers=owner_headers)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["instruction_id"], "inst-1")
        self.assertEqual(payload["id"], "inst-1")
        self.assertEqual(payload["job_id"], job.id)
        self.assertEqual(payload["version"], 2)
        self.assertEqual(payload["markdown"], "# v2")
        self.assertEqual(payload["validation_status"], "PASS")
        self.assertIn("updated_at", payload)

    def test_get_instruction_specific_version_returns_exact_version(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-2:editor"}

        project = store.create_project(owner_id="owner-2", name="Owned")
        job = store.create_job(owner_id="owner-2", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-2",
            instruction_id="inst-2",
            job_id=job.id,
            version=1,
            markdown="first",
            validation_status=ValidationStatus.PASS,
        )
        store.create_instruction_version(
            owner_id="owner-2",
            instruction_id="inst-2",
            job_id=job.id,
            version=2,
            markdown="second",
            validation_status=ValidationStatus.FAIL,
        )

        response = client.get("/api/v1/instructions/inst-2?version=1", headers=owner_headers)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["instruction_id"], "inst-2")
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["markdown"], "first")
        self.assertEqual(payload["validation_status"], "PASS")

    def test_missing_version_returns_no_leak_404_without_side_effects(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-3:editor"}

        project = store.create_project(owner_id="owner-3", name="Owned")
        job = store.create_job(owner_id="owner-3", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-3",
            instruction_id="inst-3",
            job_id=job.id,
            version=1,
            markdown="only-version",
        )
        before_project_writes = store.project_write_count
        before_job_writes = store.job_write_count
        before_instruction_writes = store.instruction_write_count

        response = client.get("/api/v1/instructions/inst-3?version=99", headers=owner_headers)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(store.project_write_count, before_project_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.instruction_write_count, before_instruction_writes)

    def test_cross_owner_and_missing_instruction_share_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-a:editor"}
        other_headers = {"Authorization": "Bearer test:owner-b:editor"}

        project = store.create_project(owner_id="owner-a", name="Owned")
        job = store.create_job(owner_id="owner-a", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-a",
            instruction_id="inst-owned",
            job_id=job.id,
            version=1,
            markdown="owner-only",
        )
        before_project_writes = store.project_write_count
        before_job_writes = store.job_write_count
        before_instruction_writes = store.instruction_write_count

        cross_owner = client.get("/api/v1/instructions/inst-owned", headers=other_headers)
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing = client.get("/api/v1/instructions/inst-missing", headers=other_headers)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        self.assertEqual(store.project_write_count, before_project_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.instruction_write_count, before_instruction_writes)

    def test_version_query_minimum_validation_returns_404_without_side_effects(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-4:editor"}

        project = store.create_project(owner_id="owner-4", name="Owned")
        job = store.create_job(owner_id="owner-4", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-4",
            instruction_id="inst-4",
            job_id=job.id,
            version=1,
            markdown="v1",
        )
        before_project_writes = store.project_write_count
        before_job_writes = store.job_write_count
        before_instruction_writes = store.instruction_write_count

        response = client.get("/api/v1/instructions/inst-4?version=0", headers=owner_headers)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(store.project_write_count, before_project_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.instruction_write_count, before_instruction_writes)

    def test_update_instruction_success_creates_new_version_and_preserves_history(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-5:editor"}
        initial_updated_at = datetime.now(UTC) - timedelta(minutes=10)

        project = store.create_project(owner_id="owner-5", name="Owned")
        job = store.create_job(owner_id="owner-5", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-5",
            instruction_id="inst-5",
            job_id=job.id,
            version=1,
            markdown="before",
            validation_status=ValidationStatus.PASS,
            updated_at=initial_updated_at,
        )
        before_instruction_writes = store.instruction_write_count
        before_job_writes = store.job_write_count
        before_project_writes = store.project_write_count

        response = client.put(
            "/api/v1/instructions/inst-5",
            headers=owner_headers,
            json={"base_version": 1, "markdown": "after"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["instruction_id"], "inst-5")
        self.assertEqual(payload["job_id"], job.id)
        self.assertEqual(payload["version"], 2)
        self.assertEqual(payload["markdown"], "after")
        self.assertEqual(payload["validation_status"], "PASS")
        updated_at = datetime.fromisoformat(payload["updated_at"])
        self.assertGreater(updated_at, initial_updated_at)
        self.assertEqual(store.instruction_write_count, before_instruction_writes + 1)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.project_write_count, before_project_writes)

        old_version = store.get_instruction_for_owner(owner_id="owner-5", instruction_id="inst-5", version=1)
        self.assertIsNotNone(old_version)
        assert old_version is not None
        self.assertEqual(old_version.markdown, "before")
        self.assertEqual(old_version.updated_at, initial_updated_at)
        latest = store.get_instruction_for_owner(owner_id="owner-5", instruction_id="inst-5", version=None)
        self.assertIsNotNone(latest)
        assert latest is not None
        self.assertEqual(latest.version, 2)
        self.assertEqual(latest.markdown, "after")
        self.assertGreater(latest.updated_at, initial_updated_at)

    def test_update_instruction_stale_base_version_returns_409_without_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-6:editor"}

        project = store.create_project(owner_id="owner-6", name="Owned")
        job = store.create_job(owner_id="owner-6", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-6",
            instruction_id="inst-6",
            job_id=job.id,
            version=1,
            markdown="v1",
        )
        store.create_instruction_version(
            owner_id="owner-6",
            instruction_id="inst-6",
            job_id=job.id,
            version=2,
            markdown="v2",
        )
        before_instruction_writes = store.instruction_write_count
        before_job_writes = store.job_write_count
        before_project_writes = store.project_write_count

        response = client.put(
            "/api/v1/instructions/inst-6",
            headers=owner_headers,
            json={"base_version": 1, "markdown": "should-fail"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "VERSION_CONFLICT")
        self.assertEqual(response.json()["details"]["base_version"], 1)
        self.assertEqual(response.json()["details"]["current_version"], 2)
        self.assertEqual(store.instruction_write_count, before_instruction_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.project_write_count, before_project_writes)

        latest = store.get_instruction_for_owner(owner_id="owner-6", instruction_id="inst-6", version=None)
        self.assertIsNotNone(latest)
        assert latest is not None
        self.assertEqual(latest.version, 2)
        self.assertEqual(latest.markdown, "v2")

    def test_update_instruction_cross_owner_and_missing_instruction_share_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-c:editor"}
        other_headers = {"Authorization": "Bearer test:owner-d:editor"}

        project = store.create_project(owner_id="owner-c", name="Owned")
        job = store.create_job(owner_id="owner-c", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-c",
            instruction_id="inst-owned-update",
            job_id=job.id,
            version=1,
            markdown="owner-only",
        )
        before_instruction_writes = store.instruction_write_count
        before_job_writes = store.job_write_count
        before_project_writes = store.project_write_count

        cross_owner = client.put(
            "/api/v1/instructions/inst-owned-update",
            headers=other_headers,
            json={"base_version": 1, "markdown": "x"},
        )
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing = client.put(
            "/api/v1/instructions/inst-missing-update",
            headers=other_headers,
            json={"base_version": 1, "markdown": "x"},
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        self.assertEqual(store.instruction_write_count, before_instruction_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.project_write_count, before_project_writes)

    def test_update_instruction_invalid_payload_returns_409_version_conflict_schema_without_side_effects(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-7:editor"}

        project = store.create_project(owner_id="owner-7", name="Owned")
        job = store.create_job(owner_id="owner-7", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-7",
            instruction_id="inst-7",
            job_id=job.id,
            version=1,
            markdown="v1",
        )
        before_instruction_writes = store.instruction_write_count
        before_job_writes = store.job_write_count
        before_project_writes = store.project_write_count

        missing_field = client.put(
            "/api/v1/instructions/inst-7",
            headers=owner_headers,
            json={"base_version": 1},
        )
        self.assertEqual(missing_field.status_code, 409)
        self.assertEqual(missing_field.json()["code"], "VERSION_CONFLICT")
        self.assertEqual(missing_field.json()["details"], {"base_version": 1, "current_version": 0})

        invalid_version = client.put(
            "/api/v1/instructions/inst-7",
            headers=owner_headers,
            json={"base_version": 0, "markdown": "v2"},
        )
        self.assertEqual(invalid_version.status_code, 409)
        self.assertEqual(invalid_version.json()["code"], "VERSION_CONFLICT")
        self.assertEqual(invalid_version.json()["details"], {"base_version": 0, "current_version": 0})

        self.assertEqual(store.instruction_write_count, before_instruction_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.project_write_count, before_project_writes)


class InstructionOwnershipUnitTests(unittest.TestCase):
    def test_get_instruction_defaults_to_latest_version(self) -> None:
        store = InMemoryStore()
        service = InstructionService(store)
        project = store.create_project(owner_id="user-1", name="Project")
        job = store.create_job(owner_id="user-1", project_id=project.id)
        store.create_instruction_version(
            owner_id="user-1",
            instruction_id="inst-unit-1",
            job_id=job.id,
            version=1,
            markdown="v1",
        )
        store.create_instruction_version(
            owner_id="user-1",
            instruction_id="inst-unit-1",
            job_id=job.id,
            version=2,
            markdown="v2",
        )

        latest = service.get_instruction(owner_id="user-1", instruction_id="inst-unit-1")

        self.assertEqual(latest.version, 2)
        self.assertEqual(latest.markdown, "v2")
        self.assertEqual(latest.model_dump()["id"], "inst-unit-1")

    def test_get_instruction_returns_requested_version_and_404_for_missing_version(self) -> None:
        store = InMemoryStore()
        service = InstructionService(store)
        project = store.create_project(owner_id="user-2", name="Project")
        job = store.create_job(owner_id="user-2", project_id=project.id)
        store.create_instruction_version(
            owner_id="user-2",
            instruction_id="inst-unit-2",
            job_id=job.id,
            version=1,
            markdown="v1",
        )

        version_one = service.get_instruction(owner_id="user-2", instruction_id="inst-unit-2", version=1)
        self.assertEqual(version_one.version, 1)
        self.assertEqual(version_one.markdown, "v1")

        with self.assertRaises(ApiError) as context:
            service.get_instruction(owner_id="user-2", instruction_id="inst-unit-2", version=9)
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.payload.code, "RESOURCE_NOT_FOUND")

    def test_get_instruction_non_owner_is_no_leak_404(self) -> None:
        store = InMemoryStore()
        service = InstructionService(store)
        project = store.create_project(owner_id="owner-a", name="Project")
        job = store.create_job(owner_id="owner-a", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-a",
            instruction_id="inst-unit-3",
            job_id=job.id,
            version=1,
            markdown="owner-a-only",
        )

        with self.assertRaises(ApiError) as context:
            service.get_instruction(owner_id="owner-b", instruction_id="inst-unit-3")
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.payload.code, "RESOURCE_NOT_FOUND")

    def test_update_instruction_creates_new_version_when_base_matches(self) -> None:
        store = InMemoryStore()
        service = InstructionService(store)
        project = store.create_project(owner_id="owner-upd", name="Project")
        job = store.create_job(owner_id="owner-upd", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-upd",
            instruction_id="inst-unit-upd-1",
            job_id=job.id,
            version=1,
            markdown="v1",
        )
        before_writes = store.instruction_write_count

        updated = service.update_instruction(
            owner_id="owner-upd",
            instruction_id="inst-unit-upd-1",
            base_version=1,
            markdown="v2",
        )

        self.assertEqual(updated.version, 2)
        self.assertEqual(updated.markdown, "v2")
        self.assertEqual(store.instruction_write_count, before_writes + 1)
        previous = service.get_instruction(owner_id="owner-upd", instruction_id="inst-unit-upd-1", version=1)
        self.assertEqual(previous.markdown, "v1")

    def test_update_instruction_stale_base_version_returns_409_without_mutation(self) -> None:
        store = InMemoryStore()
        service = InstructionService(store)
        project = store.create_project(owner_id="owner-upd-2", name="Project")
        job = store.create_job(owner_id="owner-upd-2", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-upd-2",
            instruction_id="inst-unit-upd-2",
            job_id=job.id,
            version=1,
            markdown="v1",
        )
        store.create_instruction_version(
            owner_id="owner-upd-2",
            instruction_id="inst-unit-upd-2",
            job_id=job.id,
            version=2,
            markdown="v2",
        )
        before_writes = store.instruction_write_count

        with self.assertRaises(ApiError) as context:
            service.update_instruction(
                owner_id="owner-upd-2",
                instruction_id="inst-unit-upd-2",
                base_version=1,
                markdown="v3",
            )
        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(context.exception.payload.code, "VERSION_CONFLICT")
        self.assertEqual(context.exception.payload.details, {"base_version": 1, "current_version": 2})
        self.assertEqual(store.instruction_write_count, before_writes)

    def test_update_instruction_non_owner_and_missing_are_no_leak_404(self) -> None:
        store = InMemoryStore()
        service = InstructionService(store)
        project = store.create_project(owner_id="owner-upd-3", name="Project")
        job = store.create_job(owner_id="owner-upd-3", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-upd-3",
            instruction_id="inst-unit-upd-3",
            job_id=job.id,
            version=1,
            markdown="v1",
        )

        with self.assertRaises(ApiError) as non_owner_context:
            service.update_instruction(
                owner_id="owner-other",
                instruction_id="inst-unit-upd-3",
                base_version=1,
                markdown="v2",
            )
        self.assertEqual(non_owner_context.exception.status_code, 404)
        self.assertEqual(non_owner_context.exception.payload.code, "RESOURCE_NOT_FOUND")

        with self.assertRaises(ApiError) as missing_context:
            service.update_instruction(
                owner_id="owner-upd-3",
                instruction_id="inst-unit-upd-missing",
                base_version=1,
                markdown="v2",
            )
        self.assertEqual(missing_context.exception.status_code, 404)
        self.assertEqual(missing_context.exception.payload.code, "RESOURCE_NOT_FOUND")
