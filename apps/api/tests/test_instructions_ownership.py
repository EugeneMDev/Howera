"""Instruction ownership and version-selection tests for Story 4.2."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
import unittest

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.domain.instruction_validation import INSTRUCTION_VALIDATOR_VERSION, validate_instruction_markdown
from app.errors import ApiError
from app.main import create_app
from app.repositories.memory import InMemoryStore
from app.schemas.instruction import CharRange, RegenerateSelection, RegenerateTaskStatus, ValidationStatus
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
            markdown="v1",
        )
        store.create_instruction_version(
            owner_id="owner-1",
            instruction_id="inst-1",
            job_id=job.id,
            version=2,
            markdown="# v2",
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
            markdown="# first",
        )
        store.create_instruction_version(
            owner_id="owner-2",
            instruction_id="inst-2",
            job_id=job.id,
            version=2,
            markdown="second",
        )

        response = client.get("/api/v1/instructions/inst-2?version=1", headers=owner_headers)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["instruction_id"], "inst-2")
        self.assertEqual(payload["version"], 1)
        self.assertEqual(payload["markdown"], "# first")
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

    def test_openapi_instruction_schema_exposes_validation_fields_and_enum(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        document = response.json()
        self.assertIn("/api/v1/instructions/{instructionId}", document["paths"])
        schemas = document["components"]["schemas"]
        instruction = schemas["Instruction"]
        properties = instruction["properties"]
        self.assertIn("validation_status", properties)
        self.assertIn("validation_errors", properties)
        self.assertIn("validated_at", properties)
        self.assertIn("validator_version", properties)
        self.assertEqual(
            properties["validation_status"]["$ref"],
            "#/components/schemas/ValidationStatus",
        )
        self.assertEqual(schemas["ValidationStatus"]["enum"], ["PASS", "FAIL"])

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
            markdown="# before",
            updated_at=initial_updated_at,
        )
        before_instruction_writes = store.instruction_write_count
        before_job_writes = store.job_write_count
        before_project_writes = store.project_write_count

        response = client.put(
            "/api/v1/instructions/inst-5",
            headers=owner_headers,
            json={"base_version": 1, "markdown": "# after"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["instruction_id"], "inst-5")
        self.assertEqual(payload["job_id"], job.id)
        self.assertEqual(payload["version"], 2)
        self.assertEqual(payload["markdown"], "# after")
        self.assertEqual(payload["validation_status"], "PASS")
        updated_at = datetime.fromisoformat(payload["updated_at"])
        self.assertGreater(updated_at, initial_updated_at)
        self.assertEqual(store.instruction_write_count, before_instruction_writes + 1)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.project_write_count, before_project_writes)

        old_version = store.get_instruction_for_owner(owner_id="owner-5", instruction_id="inst-5", version=1)
        self.assertIsNotNone(old_version)
        assert old_version is not None
        self.assertEqual(old_version.markdown, "# before")
        self.assertEqual(old_version.updated_at, initial_updated_at)
        latest = store.get_instruction_for_owner(owner_id="owner-5", instruction_id="inst-5", version=None)
        self.assertIsNotNone(latest)
        assert latest is not None
        self.assertEqual(latest.version, 2)
        self.assertEqual(latest.markdown, "# after")
        self.assertGreater(latest.updated_at, initial_updated_at)

    def test_update_instruction_invalid_structure_persists_fail_status_with_sanitized_diagnostics(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-8:editor"}

        project = store.create_project(owner_id="owner-8", name="Owned")
        job = store.create_job(owner_id="owner-8", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-8",
            instruction_id="inst-8",
            job_id=job.id,
            version=1,
            markdown="# valid-heading",
        )

        secret_marker = "prompt=sk-secret-value"
        response = client.put(
            "/api/v1/instructions/inst-8",
            headers=owner_headers,
            json={"base_version": 1, "markdown": secret_marker},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["version"], 2)
        self.assertEqual(payload["validation_status"], "FAIL")
        self.assertEqual(payload["validator_version"], INSTRUCTION_VALIDATOR_VERSION)
        self.assertIsNotNone(payload["validated_at"])
        errors = payload["validation_errors"]
        self.assertIsInstance(errors, list)
        self.assertGreater(len(errors), 0)
        self.assertEqual(errors[0]["code"], "STRUCTURE_MISSING_HEADING")
        self.assertEqual(errors[0]["path"], "heading[0]")
        self.assertNotIn(secret_marker, " ".join(item["message"] for item in errors))

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

    def test_request_regenerate_first_call_returns_202_and_persists_provenance(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-r1:editor"}

        project = store.create_project(owner_id="owner-r1", name="Owned")
        job = store.create_job(owner_id="owner-r1", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r1",
            instruction_id="inst-r1",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        before_regenerate_writes = store.regenerate_task_write_count
        before_instruction_writes = store.instruction_write_count

        response = client.post(
            "/api/v1/instructions/inst-r1/regenerate",
            headers=owner_headers,
            json={
                "base_version": 1,
                "selection": {"block_id": "block-1"},
                "client_request_id": "regen-req-1",
                "model_profile": "cloud-default",
                "prompt_template_id": "tmpl-1",
                "prompt_params_ref": "params-1",
            },
        )

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertEqual(payload["status"], "PENDING")
        self.assertFalse(payload["replayed"])
        self.assertEqual(payload["instruction_id"], "inst-r1")
        self.assertIsNone(payload.get("instruction_version"))
        self.assertEqual(payload["provenance"]["instruction_id"], "inst-r1")
        self.assertEqual(payload["provenance"]["base_version"], 1)
        self.assertEqual(payload["provenance"]["selection"], {"block_id": "block-1"})
        self.assertEqual(payload["provenance"]["requested_by"], "owner-r1")
        self.assertEqual(payload["provenance"]["model_profile"], "cloud-default")
        self.assertEqual(payload["provenance"]["prompt_template_id"], "tmpl-1")
        self.assertEqual(payload["provenance"]["prompt_params_ref"], "params-1")
        self.assertEqual(store.regenerate_task_write_count, before_regenerate_writes + 1)
        self.assertEqual(store.instruction_write_count, before_instruction_writes)

    def test_request_regenerate_replay_returns_200_without_duplicate_task_writes(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-r2:editor"}

        project = store.create_project(owner_id="owner-r2", name="Owned")
        job = store.create_job(owner_id="owner-r2", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r2",
            instruction_id="inst-r2",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )

        request_payload = {
            "base_version": 1,
            "selection": {"char_range": {"start_offset": 0, "end_offset": 12}},
            "client_request_id": "regen-req-2",
        }
        first = client.post(
            "/api/v1/instructions/inst-r2/regenerate",
            headers=owner_headers,
            json=request_payload,
        )
        self.assertEqual(first.status_code, 202)
        first_task_id = first.json()["id"]
        writes_after_first = store.regenerate_task_write_count

        replay = client.post(
            "/api/v1/instructions/inst-r2/regenerate",
            headers=owner_headers,
            json=request_payload,
        )

        self.assertEqual(replay.status_code, 200)
        replay_payload = replay.json()
        self.assertEqual(replay_payload["id"], first_task_id)
        self.assertTrue(replay_payload["replayed"])
        self.assertEqual(store.regenerate_task_write_count, writes_after_first)

    def test_request_regenerate_replay_after_instruction_advances_still_returns_200(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-r2b:editor"}

        project = store.create_project(owner_id="owner-r2b", name="Owned")
        job = store.create_job(owner_id="owner-r2b", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r2b",
            instruction_id="inst-r2b",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )

        request_payload = {
            "base_version": 1,
            "selection": {"block_id": "block-1"},
            "client_request_id": "regen-req-2b",
        }
        first = client.post(
            "/api/v1/instructions/inst-r2b/regenerate",
            headers=owner_headers,
            json=request_payload,
        )
        self.assertEqual(first.status_code, 202)
        first_task_id = first.json()["id"]
        store.complete_regenerate_task_success(task_id=first_task_id, markdown="## regenerated")
        writes_before_replay = store.regenerate_task_write_count

        replay = client.post(
            "/api/v1/instructions/inst-r2b/regenerate",
            headers=owner_headers,
            json=request_payload,
        )

        self.assertEqual(replay.status_code, 200)
        replay_payload = replay.json()
        self.assertEqual(replay_payload["id"], first_task_id)
        self.assertTrue(replay_payload["replayed"])
        self.assertEqual(replay_payload["status"], "SUCCEEDED")
        self.assertEqual(replay_payload["instruction_version"], 2)
        self.assertEqual(store.regenerate_task_write_count, writes_before_replay)

    def test_request_regenerate_duplicate_client_request_with_different_context_returns_400(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-r2c:editor"}

        project = store.create_project(owner_id="owner-r2c", name="Owned")
        job = store.create_job(owner_id="owner-r2c", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r2c",
            instruction_id="inst-r2c",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )

        first = client.post(
            "/api/v1/instructions/inst-r2c/regenerate",
            headers=owner_headers,
            json={
                "base_version": 1,
                "selection": {"block_id": "block-1"},
                "client_request_id": "regen-req-2c",
                "context": "first",
            },
        )
        self.assertEqual(first.status_code, 202)
        writes_after_first = store.regenerate_task_write_count

        mismatch = client.post(
            "/api/v1/instructions/inst-r2c/regenerate",
            headers=owner_headers,
            json={
                "base_version": 1,
                "selection": {"block_id": "block-1"},
                "client_request_id": "regen-req-2c",
                "context": "different",
            },
        )

        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(mismatch.json()["code"], "VALIDATION_ERROR")
        self.assertEqual(store.regenerate_task_write_count, writes_after_first)

    def test_request_regenerate_invalid_selection_returns_400_without_side_effects(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-r3:editor"}

        project = store.create_project(owner_id="owner-r3", name="Owned")
        job = store.create_job(owner_id="owner-r3", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r3",
            instruction_id="inst-r3",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        before_regenerate_writes = store.regenerate_task_write_count
        before_instruction_writes = store.instruction_write_count

        response = client.post(
            "/api/v1/instructions/inst-r3/regenerate",
            headers=owner_headers,
            json={
                "base_version": 1,
                "selection": {"block_id": "block-1", "char_range": {"start_offset": 0, "end_offset": 10}},
                "client_request_id": "regen-req-3",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "VALIDATION_ERROR")
        self.assertEqual(store.regenerate_task_write_count, before_regenerate_writes)
        self.assertEqual(store.instruction_write_count, before_instruction_writes)

    def test_request_regenerate_stale_base_version_returns_409_without_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-r4:editor"}

        project = store.create_project(owner_id="owner-r4", name="Owned")
        job = store.create_job(owner_id="owner-r4", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r4",
            instruction_id="inst-r4",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        store.create_instruction_version(
            owner_id="owner-r4",
            instruction_id="inst-r4",
            job_id=job.id,
            version=2,
            markdown="## newer",
        )
        before_regenerate_writes = store.regenerate_task_write_count
        before_instruction_writes = store.instruction_write_count

        response = client.post(
            "/api/v1/instructions/inst-r4/regenerate",
            headers=owner_headers,
            json={
                "base_version": 1,
                "selection": {"block_id": "block-1"},
                "client_request_id": "regen-req-4",
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "VERSION_CONFLICT")
        self.assertEqual(response.json()["details"], {"base_version": 1, "current_version": 2})
        self.assertEqual(store.regenerate_task_write_count, before_regenerate_writes)
        self.assertEqual(store.instruction_write_count, before_instruction_writes)

    def test_request_regenerate_cross_owner_and_missing_instruction_are_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-r5:editor"}
        other_headers = {"Authorization": "Bearer test:owner-r6:editor"}

        project = store.create_project(owner_id="owner-r5", name="Owned")
        job = store.create_job(owner_id="owner-r5", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r5",
            instruction_id="inst-r5",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        before_regenerate_writes = store.regenerate_task_write_count
        before_instruction_writes = store.instruction_write_count

        cross_owner = client.post(
            "/api/v1/instructions/inst-r5/regenerate",
            headers=other_headers,
            json={
                "base_version": 1,
                "selection": {"block_id": "block-1"},
                "client_request_id": "regen-req-5",
            },
        )
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing = client.post(
            "/api/v1/instructions/inst-r5-missing/regenerate",
            headers=owner_headers,
            json={
                "base_version": 1,
                "selection": {"block_id": "block-1"},
                "client_request_id": "regen-req-5-missing",
            },
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(store.regenerate_task_write_count, before_regenerate_writes)
        self.assertEqual(store.instruction_write_count, before_instruction_writes)

    def test_get_regenerate_task_owned_pending_and_running_return_contract_metadata(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-r6a:editor"}

        project = store.create_project(owner_id="owner-r6a", name="Owned")
        job = store.create_job(owner_id="owner-r6a", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r6a",
            instruction_id="inst-r6a",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        created = client.post(
            "/api/v1/instructions/inst-r6a/regenerate",
            headers=owner_headers,
            json={
                "base_version": 1,
                "selection": {"block_id": "block-1"},
                "client_request_id": "regen-req-6a",
            },
        )
        self.assertEqual(created.status_code, 202)
        task_id = created.json()["id"]

        before_instruction_writes = store.instruction_write_count
        before_regenerate_writes = store.regenerate_task_write_count
        before_job_writes = store.job_write_count
        before_project_writes = store.project_write_count

        pending = client.get(f"/api/v1/tasks/{task_id}", headers=owner_headers)

        self.assertEqual(pending.status_code, 200)
        pending_payload = pending.json()
        self.assertEqual(pending_payload["id"], task_id)
        self.assertEqual(pending_payload["status"], "PENDING")
        self.assertEqual(pending_payload["progress_pct"], 0)
        self.assertEqual(pending_payload["instruction_id"], "inst-r6a")
        self.assertEqual(pending_payload["provenance"]["instruction_id"], "inst-r6a")
        self.assertEqual(pending_payload["provenance"]["base_version"], 1)
        self.assertEqual(pending_payload["provenance"]["selection"], {"block_id": "block-1"})
        self.assertIn("requested_at", pending_payload)
        self.assertIn("updated_at", pending_payload)
        self.assertFalse(pending_payload["replayed"])

        task_record = store.regenerate_tasks_by_id[task_id]
        task_record.status = RegenerateTaskStatus.RUNNING
        task_record.progress_pct = 50
        task_record.updated_at = datetime.now(UTC)

        running = client.get(f"/api/v1/tasks/{task_id}", headers=owner_headers)

        self.assertEqual(running.status_code, 200)
        running_payload = running.json()
        self.assertEqual(running_payload["id"], task_id)
        self.assertEqual(running_payload["status"], "RUNNING")
        self.assertEqual(running_payload["progress_pct"], 50)
        self.assertEqual(running_payload["instruction_id"], "inst-r6a")
        self.assertFalse(running_payload["replayed"])
        self.assertEqual(store.instruction_write_count, before_instruction_writes)
        self.assertEqual(store.regenerate_task_write_count, before_regenerate_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.project_write_count, before_project_writes)

    def test_get_regenerate_task_succeeded_includes_instruction_version_linkage(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-r6b:editor"}

        project = store.create_project(owner_id="owner-r6b", name="Owned")
        job = store.create_job(owner_id="owner-r6b", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r6b",
            instruction_id="inst-r6b",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        created = client.post(
            "/api/v1/instructions/inst-r6b/regenerate",
            headers=owner_headers,
            json={
                "base_version": 1,
                "selection": {"char_range": {"start_offset": 0, "end_offset": 8}},
                "client_request_id": "regen-req-6b",
            },
        )
        self.assertEqual(created.status_code, 202)
        task_id = created.json()["id"]
        store.complete_regenerate_task_success(task_id=task_id, markdown="## regenerated")

        before_instruction_writes = store.instruction_write_count
        before_regenerate_writes = store.regenerate_task_write_count
        before_job_writes = store.job_write_count
        before_project_writes = store.project_write_count

        polled = client.get(f"/api/v1/tasks/{task_id}", headers=owner_headers)

        self.assertEqual(polled.status_code, 200)
        payload = polled.json()
        self.assertEqual(payload["id"], task_id)
        self.assertEqual(payload["status"], "SUCCEEDED")
        self.assertEqual(payload["instruction_id"], "inst-r6b")
        self.assertEqual(payload["instruction_version"], 2)
        self.assertEqual(payload["progress_pct"], 100)
        self.assertNotIn("failure_code", payload)
        self.assertNotIn("failure_message", payload)
        self.assertNotIn("failed_stage", payload)
        self.assertFalse(payload["replayed"])
        self.assertEqual(store.instruction_write_count, before_instruction_writes)
        self.assertEqual(store.regenerate_task_write_count, before_regenerate_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.project_write_count, before_project_writes)

    def test_get_regenerate_task_failed_returns_sanitized_failure_fields(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-r6c:editor"}

        project = store.create_project(owner_id="owner-r6c", name="Owned")
        job = store.create_job(owner_id="owner-r6c", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r6c",
            instruction_id="inst-r6c",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        created = client.post(
            "/api/v1/instructions/inst-r6c/regenerate",
            headers=owner_headers,
            json={
                "base_version": 1,
                "selection": {"block_id": "block-1"},
                "client_request_id": "regen-req-6c",
            },
        )
        self.assertEqual(created.status_code, 202)
        task_id = created.json()["id"]
        secret_marker = "prompt=raw-secret-token"
        store.fail_regenerate_task(
            task_id=task_id,
            failure_code="REGENERATE_FAILED",
            failure_message=secret_marker,
            failed_stage="generation",
        )

        before_instruction_writes = store.instruction_write_count
        before_regenerate_writes = store.regenerate_task_write_count
        before_job_writes = store.job_write_count
        before_project_writes = store.project_write_count

        polled = client.get(f"/api/v1/tasks/{task_id}", headers=owner_headers)

        self.assertEqual(polled.status_code, 200)
        payload = polled.json()
        self.assertEqual(payload["id"], task_id)
        self.assertEqual(payload["status"], "FAILED")
        self.assertEqual(payload["failure_code"], "REGENERATE_FAILED")
        self.assertEqual(payload["failure_message"], "Regenerate task failed.")
        self.assertEqual(payload["failed_stage"], "generation")
        self.assertNotIn(secret_marker, payload["failure_message"])
        self.assertNotIn("instruction_version", payload)
        self.assertFalse(payload["replayed"])
        self.assertEqual(store.instruction_write_count, before_instruction_writes)
        self.assertEqual(store.regenerate_task_write_count, before_regenerate_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.project_write_count, before_project_writes)

    def test_get_regenerate_task_cross_owner_and_missing_are_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-r6d:editor"}
        other_headers = {"Authorization": "Bearer test:owner-r6e:editor"}

        project = store.create_project(owner_id="owner-r6d", name="Owned")
        job = store.create_job(owner_id="owner-r6d", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r6d",
            instruction_id="inst-r6d",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        created = client.post(
            "/api/v1/instructions/inst-r6d/regenerate",
            headers=owner_headers,
            json={
                "base_version": 1,
                "selection": {"block_id": "block-1"},
                "client_request_id": "regen-req-6d",
            },
        )
        self.assertEqual(created.status_code, 202)
        task_id = created.json()["id"]

        before_instruction_writes = store.instruction_write_count
        before_regenerate_writes = store.regenerate_task_write_count
        before_job_writes = store.job_write_count
        before_project_writes = store.project_write_count

        cross_owner = client.get(f"/api/v1/tasks/{task_id}", headers=other_headers)
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing = client.get("/api/v1/tasks/task-missing-r6d", headers=other_headers)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        self.assertEqual(store.instruction_write_count, before_instruction_writes)
        self.assertEqual(store.regenerate_task_write_count, before_regenerate_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.project_write_count, before_project_writes)


class InstructionOwnershipUnitTests(unittest.TestCase):
    def test_create_instruction_version_persists_pass_validation_metadata(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-val-1", name="Project")
        job = store.create_job(owner_id="user-val-1", project_id=project.id)

        record = store.create_instruction_version(
            owner_id="user-val-1",
            instruction_id="inst-val-1",
            job_id=job.id,
            version=1,
            markdown="# Heading",
        )

        self.assertEqual(record.validation_status, ValidationStatus.PASS)
        self.assertIsNone(record.validation_errors)
        self.assertIsNotNone(record.validated_at)
        self.assertEqual(record.validator_version, INSTRUCTION_VALIDATOR_VERSION)

    def test_create_instruction_version_persists_sanitized_failure_diagnostics(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-val-2", name="Project")
        job = store.create_job(owner_id="user-val-2", project_id=project.id)
        secret_marker = "transcript=very-sensitive-value"

        record = store.create_instruction_version(
            owner_id="user-val-2",
            instruction_id="inst-val-2",
            job_id=job.id,
            version=1,
            markdown=secret_marker,
        )

        self.assertEqual(record.validation_status, ValidationStatus.FAIL)
        self.assertIsNotNone(record.validation_errors)
        assert record.validation_errors is not None
        self.assertEqual(record.validation_errors[0].code, "STRUCTURE_MISSING_HEADING")
        self.assertEqual(record.validation_errors[0].path, "heading[0]")
        self.assertNotIn(secret_marker, " ".join(issue.message for issue in record.validation_errors))
        self.assertIsNotNone(record.validated_at)
        self.assertEqual(record.validator_version, INSTRUCTION_VALIDATOR_VERSION)

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

    def test_get_regenerate_task_owner_scoped_and_read_only(self) -> None:
        store = InMemoryStore()
        service = InstructionService(store)
        project = store.create_project(owner_id="owner-r-unit-0", name="Project")
        job = store.create_job(owner_id="owner-r-unit-0", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r-unit-0",
            instruction_id="inst-r-unit-0",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        task, replayed = store.create_regenerate_task(
            owner_id="owner-r-unit-0",
            instruction_id="inst-r-unit-0",
            job_id=job.id,
            base_version=1,
            selection=RegenerateSelection(block_id="block-1"),
            client_request_id="regen-unit-0",
        )
        self.assertFalse(replayed)
        before_instruction_writes = store.instruction_write_count
        before_regenerate_writes = store.regenerate_task_write_count
        before_job_writes = store.job_write_count
        before_project_writes = store.project_write_count

        polled = service.get_regenerate_task(owner_id="owner-r-unit-0", task_id=task.id)

        self.assertEqual(polled.id, task.id)
        self.assertEqual(polled.status, RegenerateTaskStatus.PENDING)
        self.assertFalse(polled.replayed)
        self.assertEqual(store.instruction_write_count, before_instruction_writes)
        self.assertEqual(store.regenerate_task_write_count, before_regenerate_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.project_write_count, before_project_writes)

        with self.assertRaises(ApiError) as non_owner_context:
            service.get_regenerate_task(owner_id="owner-other", task_id=task.id)
        self.assertEqual(non_owner_context.exception.status_code, 404)
        self.assertEqual(non_owner_context.exception.payload.code, "RESOURCE_NOT_FOUND")

        with self.assertRaises(ApiError) as missing_context:
            service.get_regenerate_task(owner_id="owner-r-unit-0", task_id="task-missing")
        self.assertEqual(missing_context.exception.status_code, 404)
        self.assertEqual(missing_context.exception.payload.code, "RESOURCE_NOT_FOUND")

    def test_get_regenerate_task_for_owner_returns_copy_and_scopes_owner(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="owner-r-unit-copy", name="Project")
        job = store.create_job(owner_id="owner-r-unit-copy", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r-unit-copy",
            instruction_id="inst-r-unit-copy",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        task, _ = store.create_regenerate_task(
            owner_id="owner-r-unit-copy",
            instruction_id="inst-r-unit-copy",
            job_id=job.id,
            base_version=1,
            selection=RegenerateSelection(block_id="block-1"),
            client_request_id="regen-unit-copy",
        )
        before_writes = store.regenerate_task_write_count

        owned = store.get_regenerate_task_for_owner(owner_id="owner-r-unit-copy", task_id=task.id)
        self.assertIsNotNone(owned)
        assert owned is not None
        owned.status = RegenerateTaskStatus.FAILED

        fetched_again = store.get_regenerate_task_for_owner(owner_id="owner-r-unit-copy", task_id=task.id)
        self.assertIsNotNone(fetched_again)
        assert fetched_again is not None
        self.assertEqual(fetched_again.status, RegenerateTaskStatus.PENDING)
        self.assertIsNone(store.get_regenerate_task_for_owner(owner_id="owner-other", task_id=task.id))
        self.assertEqual(store.regenerate_task_write_count, before_writes)

    def test_create_regenerate_task_payload_mismatch_is_rejected_without_duplicate_writes(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="owner-r-unit-1", name="Project")
        job = store.create_job(owner_id="owner-r-unit-1", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r-unit-1",
            instruction_id="inst-r-unit-1",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )

        first, replayed = store.create_regenerate_task(
            owner_id="owner-r-unit-1",
            instruction_id="inst-r-unit-1",
            job_id=job.id,
            base_version=1,
            selection=RegenerateSelection(block_id="block-1"),
            client_request_id="regen-unit-1",
            context="first",
        )
        self.assertFalse(replayed)
        writes_after_first = store.regenerate_task_write_count

        with self.assertRaises(ValueError):
            store.create_regenerate_task(
                owner_id="owner-r-unit-1",
                instruction_id="inst-r-unit-1",
                job_id=job.id,
                base_version=1,
                selection=RegenerateSelection(char_range=CharRange(start_offset=0, end_offset=10)),
                client_request_id="regen-unit-1",
                context="first",
            )

        self.assertEqual(store.regenerate_task_write_count, writes_after_first)
        replay_task, replayed_again = store.create_regenerate_task(
            owner_id="owner-r-unit-1",
            instruction_id="inst-r-unit-1",
            job_id=job.id,
            base_version=1,
            selection=RegenerateSelection(block_id="block-1"),
            client_request_id="regen-unit-1",
            context="first",
        )
        self.assertTrue(replayed_again)
        self.assertEqual(replay_task.id, first.id)

        with self.assertRaises(ValueError):
            store.create_regenerate_task(
                owner_id="owner-r-unit-1",
                instruction_id="inst-r-unit-1",
                job_id=job.id,
                base_version=1,
                selection=RegenerateSelection(block_id="block-1"),
                client_request_id="regen-unit-1",
                context="changed",
            )

    def test_complete_regenerate_task_success_creates_validated_instruction_and_audit_event(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="owner-r-unit-2", name="Project")
        job = store.create_job(owner_id="owner-r-unit-2", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r-unit-2",
            instruction_id="inst-r-unit-2",
            job_id=job.id,
            version=1,
            markdown="# before",
        )
        task, replayed = store.create_regenerate_task(
            owner_id="owner-r-unit-2",
            instruction_id="inst-r-unit-2",
            job_id=job.id,
            base_version=1,
            selection=RegenerateSelection(block_id="block-1"),
            client_request_id="regen-unit-2",
            model_profile="cloud-default",
            prompt_template_id="tmpl-2",
            prompt_params_ref="params-2",
        )
        self.assertFalse(replayed)
        before_instruction_writes = store.instruction_write_count
        before_regen_audit_writes = store.regenerate_audit_write_count

        completed = store.complete_regenerate_task_success(task_id=task.id, markdown="## regenerated")

        self.assertEqual(completed.status, RegenerateTaskStatus.SUCCEEDED)
        self.assertEqual(completed.progress_pct, 100)
        self.assertEqual(completed.instruction_version, 2)
        self.assertEqual(store.instruction_write_count, before_instruction_writes + 1)
        self.assertEqual(store.regenerate_audit_write_count, before_regen_audit_writes + 1)
        self.assertEqual(store.regenerate_audit_events[-1].event_type, "INSTRUCTION_REGENERATE_SUCCEEDED")
        latest = store.get_instruction_for_owner(
            owner_id="owner-r-unit-2",
            instruction_id="inst-r-unit-2",
            version=None,
        )
        self.assertIsNotNone(latest)
        assert latest is not None
        self.assertEqual(latest.version, 2)
        self.assertEqual(latest.markdown, "## regenerated")
        self.assertEqual(latest.validation_status, ValidationStatus.PASS)
        self.assertIsNone(latest.validation_errors)
        self.assertIsNotNone(latest.validated_at)
        self.assertEqual(latest.model_profile_id, "cloud-default")
        self.assertEqual(latest.prompt_template_id, "tmpl-2")
        self.assertEqual(latest.prompt_params_ref, "params-2")

    def test_fail_regenerate_task_persists_sanitized_failure_fields(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="owner-r-unit-3", name="Project")
        job = store.create_job(owner_id="owner-r-unit-3", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r-unit-3",
            instruction_id="inst-r-unit-3",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        task, _ = store.create_regenerate_task(
            owner_id="owner-r-unit-3",
            instruction_id="inst-r-unit-3",
            job_id=job.id,
            base_version=1,
            selection=RegenerateSelection(block_id="block-1"),
            client_request_id="regen-unit-3",
        )
        secret_marker = "prompt=super-secret-token"

        failed = store.fail_regenerate_task(
            task_id=task.id,
            failure_code="REGENERATE_FAILED",
            failure_message=secret_marker,
            failed_stage="generation",
        )

        self.assertEqual(failed.status, RegenerateTaskStatus.FAILED)
        self.assertEqual(failed.failure_code, "REGENERATE_FAILED")
        self.assertEqual(failed.failed_stage, "generation")
        self.assertEqual(failed.failure_message, "Regenerate task failed.")
        self.assertNotIn(secret_marker, failed.failure_message or "")


class InstructionValidationUnitTests(unittest.TestCase):
    def test_validate_instruction_markdown_passes_when_heading_present(self) -> None:
        result = validate_instruction_markdown("# Title\n\nBody")

        self.assertEqual(result.status, ValidationStatus.PASS)
        self.assertIsNone(result.errors)
        self.assertEqual(result.validator_version, INSTRUCTION_VALIDATOR_VERSION)
        self.assertIsNotNone(result.validated_at)

    def test_validate_instruction_markdown_passes_with_non_h1_heading(self) -> None:
        result = validate_instruction_markdown("## Section\n\nBody")

        self.assertEqual(result.status, ValidationStatus.PASS)
        self.assertIsNone(result.errors)
        self.assertEqual(result.validator_version, INSTRUCTION_VALIDATOR_VERSION)
        self.assertIsNotNone(result.validated_at)

    def test_validate_instruction_markdown_fails_for_empty_markdown(self) -> None:
        result = validate_instruction_markdown("   \n\t")

        self.assertEqual(result.status, ValidationStatus.FAIL)
        self.assertIsNotNone(result.errors)
        assert result.errors is not None
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0].code, "STRUCTURE_EMPTY")
        self.assertEqual(result.errors[0].message, "Markdown must not be empty.")
        self.assertIsNone(result.errors[0].path)
        self.assertEqual(result.validator_version, INSTRUCTION_VALIDATOR_VERSION)

    def test_validate_instruction_markdown_missing_heading_is_deterministic_and_sanitized(self) -> None:
        secret_marker = "prompt=very-sensitive-token"
        first = validate_instruction_markdown(secret_marker)
        second = validate_instruction_markdown(secret_marker)

        self.assertEqual(first.status, ValidationStatus.FAIL)
        self.assertEqual(second.status, ValidationStatus.FAIL)
        self.assertIsNotNone(first.errors)
        self.assertIsNotNone(second.errors)
        assert first.errors is not None
        assert second.errors is not None
        first_errors = [(issue.code, issue.message, issue.path) for issue in first.errors]
        second_errors = [(issue.code, issue.message, issue.path) for issue in second.errors]
        self.assertEqual(first_errors, second_errors)
        self.assertEqual(first_errors, [("STRUCTURE_MISSING_HEADING", "Markdown must include at least one heading.", "heading[0]")])
        self.assertNotIn(secret_marker, " ".join(issue.message for issue in first.errors))
        self.assertNotIn(secret_marker, " ".join(issue.message for issue in second.errors))
