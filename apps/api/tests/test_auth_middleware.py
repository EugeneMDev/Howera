"""Authentication dependency and adapter tests for Story 1.1."""

from __future__ import annotations

from datetime import UTC, datetime
import os
import re
import sys
import types
import unittest
from unittest.mock import patch

from fastapi import Request
from fastapi.testclient import TestClient

from app.adapters.auth.base import AuthVerificationError
from app.adapters.auth.firebase_auth import FirebaseTokenVerifier
from app.adapters.auth.mock_auth import MockTokenVerifier
from app.core.config import Settings, get_settings
from app.main import create_app
from app.routes.dependencies import get_project_service, get_token_verifier
from app.schemas.job import JobStatus
from app.schemas.project import Project


class _CapturingProjectService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def create_project(self, *, owner_id: str, name: str) -> Project:
        self.calls.append((owner_id, name))
        return Project(id="project-1", name=name, created_at=datetime.now(UTC))


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


class AuthApiTests(_SettingsEnvCase):
    def test_openapi_includes_story_paths_and_contract_response_codes(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]

        self.assertIn("/api/v1/projects", paths)
        self.assertIn("/api/v1/projects/{projectId}", paths)
        self.assertIn("/api/v1/projects/{projectId}/jobs", paths)
        self.assertIn("/api/v1/jobs/{jobId}", paths)
        self.assertIn("/api/v1/jobs/{jobId}/confirm-upload", paths)
        self.assertIn("/api/v1/jobs/{jobId}/run", paths)
        self.assertIn("/api/v1/internal/jobs/{jobId}/status", paths)

        self.assertEqual(set(paths["/api/v1/projects"]["post"]["responses"].keys()), {"201", "401"})
        self.assertEqual(set(paths["/api/v1/projects"]["get"]["responses"].keys()), {"200"})
        self.assertEqual(set(paths["/api/v1/projects/{projectId}"]["get"]["responses"].keys()), {"200", "404"})
        self.assertEqual(
            set(paths["/api/v1/projects/{projectId}/jobs"]["post"]["responses"].keys()),
            {"201", "404"},
        )
        self.assertEqual(set(paths["/api/v1/jobs/{jobId}"]["get"]["responses"].keys()), {"200", "404"})
        self.assertEqual(
            set(paths["/api/v1/jobs/{jobId}/confirm-upload"]["post"]["responses"].keys()),
            {"200", "404", "409"},
        )
        self.assertEqual(
            set(paths["/api/v1/jobs/{jobId}/run"]["post"]["responses"].keys()),
            {"200", "202", "404", "409", "502"},
        )
        self.assertEqual(
            paths["/api/v1/jobs/{jobId}"]["get"]["responses"]["404"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/NoLeakNotFoundError",
        )
        self.assertEqual(
            paths["/api/v1/jobs/{jobId}/confirm-upload"]["post"]["responses"]["409"]["content"]["application/json"]["schema"]["oneOf"],
            [
                {"$ref": "#/components/schemas/FsmTransitionError"},
                {"$ref": "#/components/schemas/VideoUriConflictError"},
            ],
        )
        self.assertEqual(
            paths["/api/v1/jobs/{jobId}/run"]["post"]["responses"]["409"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/FsmTransitionError",
        )
        self.assertEqual(
            paths["/api/v1/jobs/{jobId}/run"]["post"]["responses"]["502"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/UpstreamDispatchError",
        )
        self.assertEqual(
            set(paths["/api/v1/internal/jobs/{jobId}/status"]["post"]["responses"].keys()),
            {"200", "204", "401", "404", "409"},
        )
        self.assertEqual(
            paths["/api/v1/internal/jobs/{jobId}/status"]["post"]["responses"]["409"]["content"]["application/json"]["schema"]["oneOf"],
            [
                {"$ref": "#/components/schemas/FsmTransitionError"},
                {"$ref": "#/components/schemas/CallbackOrderingError"},
                {"$ref": "#/components/schemas/EventIdPayloadMismatchError"},
            ],
        )
        self.assertEqual(
            paths["/api/v1/internal/jobs/{jobId}/status"]["post"]["responses"]["404"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/NoLeakNotFoundError",
        )
        self.assertEqual(
            paths["/api/v1/projects/{projectId}"]["get"]["responses"]["404"]["content"]["application/json"]["schema"]["$ref"],
            "#/components/schemas/NoLeakNotFoundError",
        )
        callback_post = paths["/api/v1/internal/jobs/{jobId}/status"]["post"]
        request_schema_ref = callback_post["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        self.assertEqual(request_schema_ref, "#/components/schemas/StatusCallbackRequest")
        callback_schema = response.json()["components"]["schemas"]["StatusCallbackRequest"]
        self.assertIn("actor_type", callback_schema["properties"])
        self.assertIn("artifact_updates", callback_schema["properties"])
        self.assertIn("failure_code", callback_schema["properties"])
        self.assertIn("failure_message", callback_schema["properties"])
        self.assertIn("failed_stage", callback_schema["properties"])
        conflict_schema = callback_post["responses"]["409"]["content"]["application/json"]["schema"]
        conflict_variants = conflict_schema.get("oneOf") or conflict_schema.get("anyOf") or []
        conflict_refs = {item["$ref"] for item in conflict_variants}
        self.assertEqual(
            conflict_refs,
            {
                "#/components/schemas/FsmTransitionError",
                "#/components/schemas/CallbackOrderingError",
                "#/components/schemas/EventIdPayloadMismatchError",
            },
        )

    def test_missing_authorization_header_returns_401_and_no_project_side_effect(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.post("/api/v1/projects", json={"name": "Demo"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "UNAUTHORIZED")
        self.assertEqual(app.state.store.project_write_count, 0)

    def test_invalid_project_payload_returns_401_and_no_project_side_effect(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test:user-1:editor"},
            json={},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "UNAUTHORIZED")
        self.assertEqual(app.state.store.project_write_count, 0)

    def test_invalid_bearer_token_returns_401_and_no_job_side_effect(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/api/v1/projects/project-1/jobs",
            headers={"Authorization": "Bearer not-a-valid-token"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "UNAUTHORIZED")
        self.assertEqual(app.state.store.job_write_count, 0)

    def test_valid_bearer_token_resolves_user_id_for_downstream_handler(self) -> None:
        app = create_app()
        client = TestClient(app)

        capturing_service = _CapturingProjectService()
        app.dependency_overrides[get_project_service] = lambda: capturing_service

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test:user-123:editor"},
            json={"name": "Owned Project"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(capturing_service.calls), 1)
        self.assertEqual(capturing_service.calls[0][0], "user-123")
        self.assertEqual(capturing_service.calls[0][1], "Owned Project")

    def test_auth_principal_is_attached_to_request_state(self) -> None:
        app = create_app()
        client = TestClient(app)

        capturing_service = _CapturingProjectService()
        observed_user_id: dict[str, str] = {}

        def _override_project_service(request: Request) -> _CapturingProjectService:
            observed_user_id["value"] = request.state.auth_principal.user_id
            return capturing_service

        app.dependency_overrides[get_project_service] = _override_project_service

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test:user-state:editor"},
            json={"name": "State Project"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(observed_user_id.get("value"), "user-state")

    def test_internal_callback_uses_callback_secret_not_bearer(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)

        body = {
            "event_id": "evt-1",
            "status": "UPLOADING",
            "occurred_at": "2026-02-22T00:00:00Z",
            "correlation_id": "corr-1",
        }

        unauthorized = client.post(f"/api/v1/internal/jobs/{job.id}/status", json=body)
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(unauthorized.json()["code"], "UNAUTHORIZED")

        authorized = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json=body,
        )
        self.assertEqual(authorized.status_code, 204)
        self.assertEqual(store.jobs[job.id].status.value, "UPLOADING")

    def test_invalid_callback_secret_causes_no_mutation_side_effects(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)
        before_status = store.jobs[job.id].status
        before_job_writes = store.job_write_count

        body = {
            "event_id": "evt-2",
            "status": "CREATED",
            "occurred_at": "2026-02-22T00:00:00Z",
            "correlation_id": "corr-2",
        }

        response = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "wrong-secret"},
            json=body,
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "UNAUTHORIZED")
        self.assertEqual(store.jobs[job.id].status, before_status)
        self.assertEqual(store.job_write_count, before_job_writes)

    def test_invalid_callback_payload_returns_409_validation_error(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)

        response = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json={"event_id": "evt-1"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "VALIDATION_ERROR")

    def test_callback_with_valid_secret_and_missing_job_returns_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)

        body = {
            "event_id": "evt-3",
            "status": "CREATED",
            "occurred_at": "2026-02-22T00:00:00Z",
            "correlation_id": "corr-3",
        }

        response = client.post(
            "/api/v1/internal/jobs/missing-job/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json=body,
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "RESOURCE_NOT_FOUND")

    def test_callback_invalid_self_transition_returns_409_without_side_effects(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)
        before_status = store.jobs[job.id].status
        before_updated_at = store.jobs[job.id].updated_at
        before_job_writes = store.job_write_count
        before_callback_event_count = len(store.callback_events)
        before_transition_audit_count = len(store.transition_audit_events)
        before_latest = store.latest_callback_at_by_job.get(job.id)

        body = {
            "event_id": "evt-self-invalid-1",
            "status": "CREATED",
            "occurred_at": "2026-02-22T00:00:00Z",
            "correlation_id": "corr-self-invalid-1",
        }

        response = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json=body,
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "FSM_TRANSITION_INVALID")
        self.assertEqual(response.json()["details"]["current_status"], "CREATED")
        self.assertEqual(response.json()["details"]["attempted_status"], "CREATED")
        self.assertEqual(
            set(response.json()["details"]["allowed_next_statuses"]),
            {"UPLOADING", "UPLOADED", "CANCELLED"},
        )
        self.assertEqual(store.jobs[job.id].status, before_status)
        self.assertEqual(store.jobs[job.id].updated_at, before_updated_at)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(len(store.callback_events), before_callback_event_count)
        self.assertEqual(len(store.transition_audit_events), before_transition_audit_count)
        self.assertNotIn((job.id, "evt-self-invalid-1"), store.callback_events)
        self.assertEqual(store.latest_callback_at_by_job.get(job.id), before_latest)

    def test_callback_from_terminal_state_returns_409_without_side_effects(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)
        store.jobs[job.id].status = JobStatus.DONE

        before_status = store.jobs[job.id].status
        before_updated_at = store.jobs[job.id].updated_at
        before_job_writes = store.job_write_count
        before_callback_event_count = len(store.callback_events)
        before_transition_audit_count = len(store.transition_audit_events)
        before_latest = store.latest_callback_at_by_job.get(job.id)

        response = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json={
                "event_id": "evt-terminal-invalid-1",
                "status": "UPLOADING",
                "occurred_at": "2026-02-22T00:05:00Z",
                "correlation_id": "corr-terminal-invalid-1",
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "FSM_TERMINAL_IMMUTABLE")
        self.assertEqual(response.json()["details"]["current_status"], "DONE")
        self.assertEqual(response.json()["details"]["attempted_status"], "UPLOADING")
        self.assertEqual(response.json()["details"]["allowed_next_statuses"], [])
        self.assertEqual(store.jobs[job.id].status, before_status)
        self.assertEqual(store.jobs[job.id].updated_at, before_updated_at)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(len(store.callback_events), before_callback_event_count)
        self.assertEqual(len(store.transition_audit_events), before_transition_audit_count)
        self.assertNotIn((job.id, "evt-terminal-invalid-1"), store.callback_events)
        self.assertEqual(store.latest_callback_at_by_job.get(job.id), before_latest)

    def test_callback_replay_returns_200_and_replayed_payload(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)

        body = {
            "event_id": "evt-replay-1",
            "status": "UPLOADING",
            "occurred_at": "2026-02-22T00:00:00Z",
            "correlation_id": "corr-replay-1",
        }

        first = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json=body,
        )
        self.assertEqual(first.status_code, 204)
        self.assertIn((job.id, "evt-replay-1"), store.callback_events)
        first_status = store.jobs[job.id].status
        first_updated_at = store.jobs[job.id].updated_at
        first_job_writes = store.job_write_count
        first_callback_event_count = len(store.callback_events)
        first_transition_audit_count = len(store.transition_audit_events)
        first_latest = store.latest_callback_at_by_job[job.id]

        replay = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json=body,
        )
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["event_id"], "evt-replay-1")
        self.assertTrue(replay.json()["replayed"])
        self.assertEqual(replay.json()["current_status"], "UPLOADING")
        self.assertEqual(store.jobs[job.id].status, first_status)
        self.assertEqual(store.jobs[job.id].updated_at, first_updated_at)
        self.assertEqual(store.job_write_count, first_job_writes)
        self.assertEqual(len(store.callback_events), first_callback_event_count)
        self.assertEqual(len(store.transition_audit_events), first_transition_audit_count)
        self.assertEqual(store.latest_callback_at_by_job[job.id], first_latest)

    def test_callback_replay_payload_mismatch_returns_409(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)

        initial = {
            "event_id": "evt-replay-2",
            "status": "UPLOADING",
            "occurred_at": "2026-02-22T00:00:00Z",
            "actor_type": "orchestrator",
            "correlation_id": "corr-replay-2",
        }
        mismatch = {
            "event_id": "evt-replay-2",
            "status": "UPLOADING",
            "occurred_at": "2026-02-22T00:00:00Z",
            "actor_type": "system",
            "correlation_id": "corr-replay-2",
        }

        first = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json=initial,
        )
        self.assertEqual(first.status_code, 204)
        status_before_conflict = store.jobs[job.id].status
        updated_at_before_conflict = store.jobs[job.id].updated_at
        job_writes_before_conflict = store.job_write_count
        callback_event_count_before_conflict = len(store.callback_events)
        transition_audit_count_before_conflict = len(store.transition_audit_events)
        latest_before_conflict = store.latest_callback_at_by_job[job.id]

        second = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json=mismatch,
        )
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "EVENT_ID_PAYLOAD_MISMATCH")
        self.assertEqual(second.json()["details"]["event_id"], "evt-replay-2")
        self.assertEqual(store.jobs[job.id].status, status_before_conflict)
        self.assertEqual(store.jobs[job.id].updated_at, updated_at_before_conflict)
        self.assertEqual(store.job_write_count, job_writes_before_conflict)
        self.assertEqual(len(store.callback_events), callback_event_count_before_conflict)
        self.assertEqual(len(store.transition_audit_events), transition_audit_count_before_conflict)
        self.assertEqual(store.latest_callback_at_by_job[job.id], latest_before_conflict)

    def test_callback_out_of_order_returns_409(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)

        first = {
            "event_id": "evt-order-1",
            "status": "UPLOADING",
            "occurred_at": "2026-02-22T01:00:00Z",
            "correlation_id": "corr-order-1",
        }
        out_of_order = {
            "event_id": "evt-order-2",
            "status": "UPLOADED",
            "occurred_at": "2026-02-22T00:30:00Z",
            "correlation_id": "corr-order-2",
        }

        response1 = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json=first,
        )
        self.assertEqual(response1.status_code, 204)
        status_before_conflict = store.jobs[job.id].status
        updated_at_before_conflict = store.jobs[job.id].updated_at
        job_writes_before_conflict = store.job_write_count
        callback_event_count_before_conflict = len(store.callback_events)
        transition_audit_count_before_conflict = len(store.transition_audit_events)
        latest_before_conflict = store.latest_callback_at_by_job[job.id]

        response2 = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json=out_of_order,
        )
        self.assertEqual(response2.status_code, 409)
        self.assertEqual(response2.json()["code"], "CALLBACK_OUT_OF_ORDER")
        self.assertEqual(store.jobs[job.id].status, status_before_conflict)
        self.assertEqual(store.jobs[job.id].updated_at, updated_at_before_conflict)
        self.assertEqual(store.job_write_count, job_writes_before_conflict)
        self.assertEqual(len(store.callback_events), callback_event_count_before_conflict)
        self.assertEqual(len(store.transition_audit_events), transition_audit_count_before_conflict)
        self.assertEqual(store.latest_callback_at_by_job[job.id], latest_before_conflict)

    def test_callback_with_equal_occurred_at_returns_409(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)

        first = {
            "event_id": "evt-order-eq-1",
            "status": "UPLOADING",
            "occurred_at": "2026-02-22T01:00:00Z",
            "correlation_id": "corr-order-eq-1",
        }
        equal_timestamp = {
            "event_id": "evt-order-eq-2",
            "status": "UPLOADED",
            "occurred_at": "2026-02-22T01:00:00Z",
            "correlation_id": "corr-order-eq-2",
        }

        response1 = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json=first,
        )
        self.assertEqual(response1.status_code, 204)
        status_before_conflict = store.jobs[job.id].status
        updated_at_before_conflict = store.jobs[job.id].updated_at
        job_writes_before_conflict = store.job_write_count
        callback_event_count_before_conflict = len(store.callback_events)
        transition_audit_count_before_conflict = len(store.transition_audit_events)
        latest_before_conflict = store.latest_callback_at_by_job[job.id]

        response2 = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json=equal_timestamp,
        )
        self.assertEqual(response2.status_code, 409)
        self.assertEqual(response2.json()["code"], "CALLBACK_OUT_OF_ORDER")
        self.assertEqual(store.jobs[job.id].status, status_before_conflict)
        self.assertEqual(store.jobs[job.id].updated_at, updated_at_before_conflict)
        self.assertEqual(store.job_write_count, job_writes_before_conflict)
        self.assertEqual(len(store.callback_events), callback_event_count_before_conflict)
        self.assertEqual(len(store.transition_audit_events), transition_audit_count_before_conflict)
        self.assertEqual(store.latest_callback_at_by_job[job.id], latest_before_conflict)

    def test_auth_logging_exposes_correlation_metadata_without_token_leak(self) -> None:
        app = create_app()
        client = TestClient(app)

        leaked_token = "not-a-valid-token-sensitive-123"
        correlation_id = "corr-auth-log-1"

        with self.assertLogs("app.routes.dependencies", level="WARNING") as captured:
            response = client.post(
                "/api/v1/projects/project-1/jobs",
                headers={
                    "Authorization": f"Bearer {leaked_token}",
                    "X-Correlation-Id": correlation_id,
                },
            )

        self.assertEqual(response.status_code, 401)
        joined = "\n".join(captured.output)
        self.assertIn("correlation_id=", joined)
        self.assertRegex(joined, r"correlation_id=cid-[0-9a-f]{12}")
        self.assertNotIn(correlation_id, joined)
        self.assertNotIn(leaked_token, joined)
        self.assertNotIn("Authorization", joined)

    def test_callback_auth_logging_does_not_leak_callback_secret(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)

        leaked_secret = "wrong-secret-sensitive-789"
        correlation_id = "corr-callback-auth-log-1"
        body = {
            "event_id": "evt-callback-auth-log-1",
            "status": "CREATED",
            "occurred_at": "2026-02-22T00:00:00Z",
            "correlation_id": correlation_id,
        }

        with self.assertLogs("app.routes.dependencies", level="WARNING") as captured:
            response = client.post(
                f"/api/v1/internal/jobs/{job.id}/status",
                headers={
                    "X-Callback-Secret": leaked_secret,
                    "X-Correlation-Id": correlation_id,
                },
                json=body,
            )

        self.assertEqual(response.status_code, 401)
        joined = "\n".join(captured.output)
        self.assertIn("correlation_id=", joined)
        self.assertRegex(joined, r"correlation_id=cid-[0-9a-f]{12}")
        self.assertNotIn(correlation_id, joined)
        self.assertNotIn(leaked_secret, joined)
        self.assertNotIn("X-Callback-Secret", joined)

    def test_callback_processing_logging_redacts_sensitive_payload_content(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)

        sensitive_transcript = "TOP-SECRET-TRANSCRIPT-CONTENT"
        sensitive_prompt = "prompt-password-do-not-log"
        body = {
            "event_id": "evt-callback-log-1",
            "status": "UPLOADING",
            "occurred_at": "2026-02-22T00:00:00Z",
            "correlation_id": "corr-callback-log-1",
            "artifact_updates": {"transcript_text": sensitive_transcript},
            "failure_message": sensitive_prompt,
        }

        with self.assertLogs("app.services.internal_callbacks", level="INFO") as captured:
            response = client.post(
                f"/api/v1/internal/jobs/{job.id}/status",
                headers={"X-Callback-Secret": "test-callback-secret"},
                json=body,
            )

        self.assertEqual(response.status_code, 204)
        joined = "\n".join(captured.output)
        self.assertIn("correlation_id=", joined)
        self.assertIn("event_id=", joined)
        self.assertIn("job_id=", joined)
        self.assertRegex(joined, r"correlation_id=cid-[0-9a-f]{12}")
        self.assertRegex(joined, r"event_id=eid-[0-9a-f]{12}")
        self.assertNotIn("corr-callback-log-1", joined)
        self.assertNotIn("evt-callback-log-1", joined)
        self.assertNotIn(sensitive_transcript, joined)
        self.assertNotIn(sensitive_prompt, joined)
        self.assertNotIn("test-callback-secret", joined)

    def test_auth_logging_redacts_sensitive_content_inside_identifier_fields(self) -> None:
        app = create_app()
        client = TestClient(app)

        leaked_token = "not-a-valid-token-sensitive-456"
        correlation_id = "TOP-SECRET-TRANSCRIPT\\nPROMPT-CONTENT"

        with self.assertLogs("app.routes.dependencies", level="WARNING") as captured:
            response = client.post(
                "/api/v1/projects/project-1/jobs",
                headers={
                    "Authorization": f"Bearer {leaked_token}",
                    "X-Correlation-Id": correlation_id,
                },
            )

        self.assertEqual(response.status_code, 401)
        joined = "\n".join(captured.output)
        self.assertRegex(joined, r"correlation_id=cid-[0-9a-f]{12}")
        self.assertNotIn("TOP-SECRET-TRANSCRIPT", joined)
        self.assertNotIn("PROMPT-CONTENT", joined)
        self.assertNotIn(correlation_id, joined)
        self.assertNotIn(leaked_token, joined)

    def test_callback_logging_redacts_sensitive_content_inside_identifier_fields(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)

        raw_event_id = "evt-secret-transcript-prompt-999"
        raw_correlation_id = "corr-secret-transcript-prompt-888"
        body = {
            "event_id": raw_event_id,
            "status": "UPLOADING",
            "occurred_at": "2026-02-22T00:00:00Z",
            "correlation_id": raw_correlation_id,
        }

        with self.assertLogs("app.services.internal_callbacks", level="INFO") as captured:
            response = client.post(
                f"/api/v1/internal/jobs/{job.id}/status",
                headers={"X-Callback-Secret": "test-callback-secret"},
                json=body,
            )

        self.assertEqual(response.status_code, 204)
        joined = "\n".join(captured.output)
        self.assertRegex(joined, r"correlation_id=cid-[0-9a-f]{12}")
        self.assertRegex(joined, r"event_id=eid-[0-9a-f]{12}")
        self.assertNotIn(raw_event_id, joined)
        self.assertNotIn(raw_correlation_id, joined)
        self.assertNotIn("secret-transcript-prompt", joined)

    def test_run_logging_redacts_sensitive_dispatch_and_failure_values(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()

        success_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        sensitive_video_uri = "s3://bucket/TOP-SECRET-VIDEO-URI.mp4"
        client.post(
            f"/api/v1/jobs/{success_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": sensitive_video_uri},
        )

        with self.assertLogs("app.services.jobs", level="INFO") as dispatch_logs:
            run_success = client.post(f"/api/v1/jobs/{success_job['id']}/run", headers=owner_headers)

        self.assertEqual(run_success.status_code, 202)
        dispatch_joined = "\n".join(dispatch_logs.output)
        self.assertRegex(dispatch_joined, r"job_id=jid-[0-9a-f]{12}")
        self.assertRegex(dispatch_joined, r"dispatch_id=did-[0-9a-f]{12}")
        self.assertNotIn(sensitive_video_uri, dispatch_joined)
        self.assertNotIn("test-callback-secret", dispatch_joined)

        failing_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        failure_video_uri = "s3://bucket/ANOTHER-SENSITIVE-VIDEO-URI.mp4"
        client.post(
            f"/api/v1/jobs/{failing_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": failure_video_uri},
        )

        store.dispatch_failure_message = "UPSTREAM-SECRET-DISPATCH-DETAIL"
        with self.assertLogs("app.services.jobs", level="WARNING") as failure_logs:
            run_failure = client.post(f"/api/v1/jobs/{failing_job['id']}/run", headers=owner_headers)

        self.assertEqual(run_failure.status_code, 502)
        failure_joined = "\n".join(failure_logs.output)
        self.assertIn("code=ORCHESTRATOR_DISPATCH_FAILED", failure_joined)
        self.assertRegex(failure_joined, r"job_id=jid-[0-9a-f]{12}")
        self.assertNotIn("UPSTREAM-SECRET-DISPATCH-DETAIL", failure_joined)
        self.assertNotIn(failure_video_uri, failure_joined)


class AuthAdapterUnitTests(unittest.TestCase):
    def test_mock_token_verifier_normalizes_principal(self) -> None:
        verifier = MockTokenVerifier()

        principal = verifier.verify_token("test:user-999:editor")

        self.assertEqual(principal.user_id, "user-999")
        self.assertEqual(principal.role, "editor")

    def test_mock_token_verifier_rejects_invalid_token(self) -> None:
        verifier = MockTokenVerifier()

        with self.assertRaises(AuthVerificationError):
            verifier.verify_token("invalid")

    def test_dependency_selects_firebase_verifier(self) -> None:
        settings = Settings(
            auth_provider="firebase",
            callback_secret="secret",
            firebase_project_id="project-a",
            firebase_audience="aud-a",
        )

        verifier = get_token_verifier(settings)

        self.assertIsInstance(verifier, FirebaseTokenVerifier)


class FirebaseVerifierUnitTests(unittest.TestCase):
    @staticmethod
    def _fake_firebase_modules(decoded_token: dict[str, str]) -> dict[str, types.ModuleType]:
        fake_admin = types.ModuleType("firebase_admin")
        fake_auth = types.ModuleType("firebase_admin.auth")

        fake_admin._apps = []

        def initialize_app() -> object:
            app_handle = object()
            fake_admin._apps.append(app_handle)
            return app_handle

        def verify_id_token(token: str, check_revoked: bool = True) -> dict[str, str]:
            if token != "valid-jwt":
                raise ValueError("invalid token")
            if not check_revoked:
                raise ValueError("must validate revoked tokens")
            return decoded_token

        fake_admin.initialize_app = initialize_app
        fake_admin.auth = fake_auth
        fake_auth.verify_id_token = verify_id_token

        return {
            "firebase_admin": fake_admin,
            "firebase_admin.auth": fake_auth,
        }

    def test_firebase_verifier_normalizes_principal(self) -> None:
        fake_modules = self._fake_firebase_modules(
            {
                "uid": "firebase-user-1",
                "aud": "aud-a",
                "iss": "https://securetoken.google.com/project-a",
                "role": "editor",
            }
        )

        with patch.dict(sys.modules, fake_modules):
            verifier = FirebaseTokenVerifier(project_id="project-a", audience="aud-a")
            principal = verifier.verify_token("valid-jwt")

        self.assertEqual(principal.user_id, "firebase-user-1")
        self.assertEqual(principal.role, "editor")

    def test_firebase_verifier_rejects_invalid_audience(self) -> None:
        fake_modules = self._fake_firebase_modules(
            {
                "uid": "firebase-user-1",
                "aud": "unexpected-aud",
                "iss": "https://securetoken.google.com/project-a",
            }
        )

        with patch.dict(sys.modules, fake_modules):
            verifier = FirebaseTokenVerifier(project_id="project-a", audience="aud-a")
            with self.assertRaises(AuthVerificationError):
                verifier.verify_token("valid-jwt")


if __name__ == "__main__":
    unittest.main()
