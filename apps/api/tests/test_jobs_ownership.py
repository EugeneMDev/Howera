"""Ownership and no-leak job API tests for Story 1.3."""

from __future__ import annotations

from datetime import UTC, datetime
import os
import unittest

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.errors import ApiError
from app.main import create_app
from app.repositories.memory import InMemoryStore
from app.schemas.job import ArtifactManifest, JobStatus, TranscriptSegment
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

    def test_confirm_upload_success_sets_uploaded_and_persists_video_uri(self) -> None:
        app = create_app()
        client = TestClient(app)
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()

        response = client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["replayed"])
        self.assertEqual(payload["job"]["status"], "UPLOADED")
        self.assertEqual(payload["job"]["manifest"]["video_uri"], "s3://bucket/video.mp4")

    def test_confirm_upload_invalid_payload_returns_409_validation_error_no_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}
        store = app.state.store

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        before_writes = store.job_write_count

        response = client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "VALIDATION_ERROR")
        self.assertEqual(store.job_write_count, before_writes)
        self.assertEqual(store.jobs[created_job["id"]].status.value, "CREATED")

    def test_confirm_upload_same_uri_replay_is_idempotent(self) -> None:
        app = create_app()
        client = TestClient(app)
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}
        store = app.state.store

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()

        first = client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )
        self.assertEqual(first.status_code, 200)
        writes_after_first = store.job_write_count

        replay = client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["replayed"])
        self.assertEqual(store.job_write_count, writes_after_first)

    def test_confirm_upload_conflicting_uri_returns_409_without_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}
        store = app.state.store

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()

        first = client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video-a.mp4"},
        )
        self.assertEqual(first.status_code, 200)
        writes_after_first = store.job_write_count

        conflict = client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video-b.mp4"},
        )
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["code"], "VIDEO_URI_CONFLICT")
        self.assertEqual(
            conflict.json()["details"],
            {
                "current_video_uri": "s3://bucket/video-a.mp4",
                "submitted_video_uri": "s3://bucket/video-b.mp4",
            },
        )
        self.assertEqual(store.job_write_count, writes_after_first)

    def test_confirm_upload_cross_owner_and_missing_job_are_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}
        other_headers = {"Authorization": "Bearer test:owner-2:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()

        cross_owner = client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=other_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing = client.post(
            "/api/v1/jobs/job-missing/confirm-upload",
            headers=other_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

    def test_run_job_first_call_dispatches_once_and_returns_202(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )
        before_dispatch_writes = store.dispatch_write_count

        response = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertFalse(payload["replayed"])
        self.assertEqual(payload["job_id"], created_job["id"])
        self.assertEqual(payload["status"], "AUDIO_EXTRACTING")
        self.assertTrue(payload["dispatch_id"].startswith("dispatch-"))
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes + 1)
        dispatch = store.get_dispatch_for_job(created_job["id"])
        self.assertIsNotNone(dispatch)
        self.assertEqual(
            dispatch.payload,
            {
                "job_id": created_job["id"],
                "project_id": project["id"],
                "video_uri": "s3://bucket/video.mp4",
                "callback_url": f"/api/v1/internal/jobs/{created_job['id']}/status",
            },
        )

    def test_run_job_replay_returns_200_without_duplicate_dispatch(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )

        first = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)
        self.assertEqual(first.status_code, 202)
        writes_after_first = store.dispatch_write_count
        dispatch_id = first.json()["dispatch_id"]

        replay = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["replayed"])
        self.assertEqual(replay.json()["dispatch_id"], dispatch_id)
        self.assertEqual(store.dispatch_write_count, writes_after_first)

    def test_run_job_from_non_uploaded_state_returns_409_without_dispatch(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        before_dispatch_writes = store.dispatch_write_count
        before_job_writes = store.job_write_count

        response = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "FSM_TRANSITION_INVALID")
        self.assertEqual(response.json()["details"]["current_status"], "CREATED")
        self.assertEqual(response.json()["details"]["attempted_status"], "AUDIO_EXTRACTING")
        self.assertEqual(
            set(response.json()["details"]["allowed_next_statuses"]),
            {"UPLOADING", "UPLOADED", "CANCELLED"},
        )
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.jobs[created_job["id"]].status.value, "CREATED")

    def test_run_job_cross_owner_and_missing_job_are_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}
        other_headers = {"Authorization": "Bearer test:owner-2:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )

        cross_owner = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=other_headers)
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing = client.post("/api/v1/jobs/job-missing/run", headers=other_headers)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

    def test_run_job_dispatch_failure_returns_502_without_state_advance(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )
        before_status = store.jobs[created_job["id"]].status
        before_job_writes = store.job_write_count
        before_dispatch_writes = store.dispatch_write_count

        store.dispatch_failure_message = "orchestrator unavailable"
        response = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["code"], "ORCHESTRATOR_DISPATCH_FAILED")
        self.assertEqual(store.jobs[created_job["id"]].status, before_status)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertIsNone(store.get_dispatch_for_job(created_job["id"]))

    def test_run_job_missing_dispatch_record_for_in_progress_state_returns_409(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )

        first = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)
        self.assertEqual(first.status_code, 202)
        store.workflow_dispatches_by_job.pop(created_job["id"], None)
        before_dispatch_writes = store.dispatch_write_count
        before_job_writes = store.job_write_count

        second = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)

        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["code"], "FSM_TRANSITION_INVALID")
        self.assertEqual(second.json()["details"]["current_status"], "AUDIO_EXTRACTING")
        self.assertEqual(second.json()["details"]["attempted_status"], "AUDIO_EXTRACTING")
        self.assertEqual(
            set(second.json()["details"]["allowed_next_statuses"]),
            {"AUDIO_EXTRACTING", "AUDIO_READY", "FAILED", "CANCELLED"},
        )
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertEqual(store.job_write_count, before_job_writes)

    def test_run_job_uploaded_without_video_uri_returns_409_without_dispatch(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()

        # Simulate state/manifest drift: status moved to UPLOADED without persisted video_uri.
        store.jobs[created_job["id"]].status = JobStatus.UPLOADED
        store.jobs[created_job["id"]].manifest = None
        before_dispatch_writes = store.dispatch_write_count
        before_job_writes = store.job_write_count

        response = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "FSM_TRANSITION_INVALID")
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertIsNone(store.get_dispatch_for_job(created_job["id"]))

    def test_run_job_terminal_states_return_409_terminal_immutable_without_dispatch(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        for terminal_status in ("FAILED", "CANCELLED", "DONE"):
            with self.subTest(terminal_status=terminal_status):
                created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
                store.jobs[created_job["id"]].status = JobStatus(terminal_status)
                before_dispatch_writes = store.dispatch_write_count
                before_job_writes = store.job_write_count

                response = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)

                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.json()["code"], "FSM_TERMINAL_IMMUTABLE")
                self.assertEqual(response.json()["details"]["current_status"], terminal_status)
                self.assertEqual(response.json()["details"]["attempted_status"], "AUDIO_EXTRACTING")
                self.assertEqual(response.json()["details"]["allowed_next_statuses"], [])
                self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
                self.assertEqual(store.job_write_count, before_job_writes)
                self.assertIsNone(store.get_dispatch_for_job(created_job["id"]))

    def test_run_job_does_not_replay_retry_dispatch_records(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )
        started = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)
        self.assertEqual(started.status_code, 202)

        store.jobs[created_job["id"]].status = JobStatus.FAILED
        retried = client.post(
            f"/api/v1/jobs/{created_job['id']}/retry",
            headers=owner_headers,
            json={"model_profile": "cloud-default", "client_request_id": "retry-run-guard-1"},
        )
        self.assertEqual(retried.status_code, 202)
        self.assertEqual(store.get_dispatch_for_job(created_job["id"]).dispatch_type, "retry")
        before_dispatch_writes = store.dispatch_write_count
        before_job_writes = store.job_write_count

        run_again = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)

        self.assertEqual(run_again.status_code, 409)
        self.assertEqual(run_again.json()["code"], "FSM_TERMINAL_IMMUTABLE")
        self.assertEqual(run_again.json()["details"]["current_status"], "FAILED")
        self.assertEqual(run_again.json()["details"]["attempted_status"], "AUDIO_EXTRACTING")
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertEqual(store.job_write_count, before_job_writes)

    def test_retry_job_valid_request_dispatches_and_persists_checkpoint_metadata(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )
        started = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)
        self.assertEqual(started.status_code, 202)

        job_record = store.jobs[created_job["id"]]
        job_record.status = JobStatus.FAILED
        job_record.manifest = job_record.manifest.model_copy(update={"audio_uri": "s3://bucket/audio.wav"})
        job_record.manifest = job_record.manifest.model_copy(update={"transcript_uri": "s3://bucket/transcript.json"})
        job_record.manifest = job_record.manifest.model_copy(update={"draft_uri": "s3://bucket/draft.md"})
        before_dispatch_writes = store.dispatch_write_count
        before_job_writes = store.job_write_count

        response = client.post(
            f"/api/v1/jobs/{created_job['id']}/retry",
            headers=owner_headers,
            json={"model_profile": "cloud-default", "client_request_id": "retry-1"},
        )

        self.assertEqual(response.status_code, 202)
        payload = response.json()
        self.assertFalse(payload["replayed"])
        self.assertEqual(payload["job_id"], created_job["id"])
        self.assertEqual(payload["status"], "FAILED")
        self.assertEqual(payload["resume_from_status"], "DRAFT_READY")
        self.assertEqual(payload["checkpoint_ref"], "s3://bucket/draft.md")
        self.assertEqual(payload["model_profile"], "cloud-default")
        self.assertTrue(payload["dispatch_id"].startswith("dispatch-"))
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes + 1)
        self.assertEqual(store.job_write_count, before_job_writes + 1)

        dispatch = store.get_dispatch_for_job(created_job["id"])
        self.assertIsNotNone(dispatch)
        self.assertEqual(dispatch.dispatch_type, "retry")
        self.assertEqual(
            dispatch.payload,
            {
                "job_id": created_job["id"],
                "project_id": project["id"],
                "video_uri": "s3://bucket/video.mp4",
                "callback_url": f"/api/v1/internal/jobs/{created_job['id']}/status",
                "resume_from_status": "DRAFT_READY",
                "checkpoint_ref": "s3://bucket/draft.md",
                "model_profile": "cloud-default",
            },
        )
        self.assertEqual(job_record.retry_resume_from_status, JobStatus.DRAFT_READY)
        self.assertEqual(job_record.retry_checkpoint_ref, "s3://bucket/draft.md")
        self.assertEqual(job_record.retry_model_profile, "cloud-default")
        self.assertEqual(job_record.retry_client_request_id, "retry-1")
        self.assertEqual(job_record.retry_dispatch_id, payload["dispatch_id"])

    def test_retry_job_replay_returns_200_without_duplicate_dispatch(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )
        started = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)
        self.assertEqual(started.status_code, 202)

        job_record = store.jobs[created_job["id"]]
        job_record.status = JobStatus.FAILED
        job_record.manifest = job_record.manifest.model_copy(update={"audio_uri": "s3://bucket/audio.wav"})

        first = client.post(
            f"/api/v1/jobs/{created_job['id']}/retry",
            headers=owner_headers,
            json={"model_profile": "cloud-default", "client_request_id": "retry-2"},
        )
        self.assertEqual(first.status_code, 202)
        dispatch_id = first.json()["dispatch_id"]
        writes_after_first = store.dispatch_write_count
        job_writes_after_first = store.job_write_count

        replay = client.post(
            f"/api/v1/jobs/{created_job['id']}/retry",
            headers=owner_headers,
            json={"model_profile": "cloud-default", "client_request_id": "retry-2"},
        )
        self.assertEqual(replay.status_code, 200)
        self.assertTrue(replay.json()["replayed"])
        self.assertEqual(replay.json()["dispatch_id"], dispatch_id)
        self.assertEqual(store.dispatch_write_count, writes_after_first)
        self.assertEqual(store.job_write_count, job_writes_after_first)

    def test_retry_job_non_failed_state_returns_409_without_side_effects(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.jobs[created_job["id"]].status = JobStatus.DRAFT_READY
        before_dispatch_writes = store.dispatch_write_count
        before_job_writes = store.job_write_count

        response = client.post(
            f"/api/v1/jobs/{created_job['id']}/retry",
            headers=owner_headers,
            json={"model_profile": "cloud-default", "client_request_id": "retry-non-failed"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "RETRY_NOT_ALLOWED_STATE")
        self.assertEqual(response.json()["details"]["current_status"], "DRAFT_READY")
        self.assertEqual(response.json()["details"]["attempted_status"], "REGENERATING")
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertIsNone(store.jobs[created_job["id"]].retry_dispatch_id)

    def test_retry_job_running_conflict_returns_409_job_already_running(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.jobs[created_job["id"]].status = JobStatus.GENERATING
        before_dispatch_writes = store.dispatch_write_count
        before_job_writes = store.job_write_count

        response = client.post(
            f"/api/v1/jobs/{created_job['id']}/retry",
            headers=owner_headers,
            json={"model_profile": "cloud-default", "client_request_id": "retry-running"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "JOB_ALREADY_RUNNING")
        self.assertEqual(response.json()["details"]["current_status"], "GENERATING")
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertEqual(store.job_write_count, before_job_writes)

    def test_retry_job_dispatch_failure_returns_502_without_state_advance_or_retry_metadata(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )
        started = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)
        self.assertEqual(started.status_code, 202)

        job_record = store.jobs[created_job["id"]]
        job_record.status = JobStatus.FAILED
        before_status = job_record.status
        before_dispatch_writes = store.dispatch_write_count
        before_job_writes = store.job_write_count

        store.dispatch_failure_message = "orchestrator unavailable"
        response = client.post(
            f"/api/v1/jobs/{created_job['id']}/retry",
            headers=owner_headers,
            json={"model_profile": "cloud-default", "client_request_id": "retry-fail-dispatch"},
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["code"], "ORCHESTRATOR_DISPATCH_FAILED")
        self.assertEqual(job_record.status, before_status)
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertIsNone(job_record.retry_dispatch_id)

    def test_retry_job_cross_owner_and_missing_job_are_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}
        other_headers = {"Authorization": "Bearer test:owner-2:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.jobs[created_job["id"]].status = JobStatus.FAILED
        before_dispatch_writes = store.dispatch_write_count
        before_job_writes = store.job_write_count

        cross_owner = client.post(
            f"/api/v1/jobs/{created_job['id']}/retry",
            headers=other_headers,
            json={"model_profile": "cloud-default", "client_request_id": "retry-cross-owner"},
        )
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertEqual(store.job_write_count, before_job_writes)

        missing = client.post(
            "/api/v1/jobs/job-missing/retry",
            headers=other_headers,
            json={"model_profile": "cloud-default", "client_request_id": "retry-missing"},
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertEqual(store.job_write_count, before_job_writes)

    def test_get_transcript_allowed_states_return_contract_page(self) -> None:
        allowed_statuses = (
            JobStatus.TRANSCRIPT_READY,
            JobStatus.GENERATING,
            JobStatus.DRAFT_READY,
            JobStatus.EDITING,
            JobStatus.EXPORTING,
            JobStatus.DONE,
            JobStatus.FAILED,
        )
        for allowed_status in allowed_statuses:
            with self.subTest(allowed_status=allowed_status):
                app = create_app()
                client = TestClient(app)
                store = app.state.store
                owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

                project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
                created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
                store.jobs[created_job["id"]].status = allowed_status
                store.set_transcript_segments_for_job(
                    job_id=created_job["id"],
                    segments=[
                        TranscriptSegment(start_ms=0, end_ms=500, text="segment"),
                    ],
                )

                response = client.get(
                    f"/api/v1/jobs/{created_job['id']}/transcript",
                    headers=owner_headers,
                )

                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["limit"], 200)
                self.assertEqual(payload["next_cursor"], None)
                self.assertEqual(
                    payload["items"],
                    [{"start_ms": 0, "end_ms": 500, "text": "segment"}],
                )

    def test_get_transcript_orders_by_start_ms_and_paginates(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.jobs[created_job["id"]].status = JobStatus.TRANSCRIPT_READY
        store.set_transcript_segments_for_job(
            job_id=created_job["id"],
            segments=[
                TranscriptSegment(start_ms=3000, end_ms=3500, text="third"),
                TranscriptSegment(start_ms=1000, end_ms=1500, text="first"),
                TranscriptSegment(start_ms=2000, end_ms=2500, text="second"),
            ],
        )

        first = client.get(
            f"/api/v1/jobs/{created_job['id']}/transcript?limit=2",
            headers=owner_headers,
        )
        self.assertEqual(first.status_code, 200)
        first_payload = first.json()
        self.assertEqual(first_payload["limit"], 2)
        self.assertEqual(first_payload["next_cursor"], "2")
        self.assertEqual(
            first_payload["items"],
            [
                {"start_ms": 1000, "end_ms": 1500, "text": "first"},
                {"start_ms": 2000, "end_ms": 2500, "text": "second"},
            ],
        )

        second = client.get(
            f"/api/v1/jobs/{created_job['id']}/transcript?limit=2&cursor={first_payload['next_cursor']}",
            headers=owner_headers,
        )
        self.assertEqual(second.status_code, 200)
        second_payload = second.json()
        self.assertEqual(second_payload["limit"], 2)
        self.assertEqual(second_payload["next_cursor"], None)
        self.assertEqual(
            second_payload["items"],
            [{"start_ms": 3000, "end_ms": 3500, "text": "third"}],
        )

    def test_get_transcript_invalid_limit_returns_409_validation_error_without_side_effects(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.jobs[created_job["id"]].status = JobStatus.TRANSCRIPT_READY
        before_job_writes = store.job_write_count
        before_dispatch_writes = store.dispatch_write_count

        too_small = client.get(
            f"/api/v1/jobs/{created_job['id']}/transcript?limit=0",
            headers=owner_headers,
        )
        self.assertEqual(too_small.status_code, 409)
        self.assertEqual(too_small.json()["code"], "VALIDATION_ERROR")
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)

        too_large = client.get(
            f"/api/v1/jobs/{created_job['id']}/transcript?limit=501",
            headers=owner_headers,
        )
        self.assertEqual(too_large.status_code, 409)
        self.assertEqual(too_large.json()["code"], "VALIDATION_ERROR")
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)

    def test_get_transcript_reads_segments_persisted_from_internal_callback(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.jobs[created_job["id"]].status = JobStatus.TRANSCRIBING

        callback = client.post(
            f"/api/v1/internal/jobs/{created_job['id']}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json={
                "event_id": "evt-transcript-segments-1",
                "status": "TRANSCRIPT_READY",
                "occurred_at": "2026-03-01T12:00:00Z",
                "actor_type": "orchestrator",
                "artifact_updates": {
                    "transcript_uri": "s3://bucket/transcript-segments.json",
                    "transcript_segments": [
                        {"start_ms": 3000, "end_ms": 3500, "text": "third"},
                        {"start_ms": 1000, "end_ms": 1500, "text": "first"},
                        {"start_ms": 2000, "end_ms": 2500, "text": "second"},
                    ],
                },
                "correlation_id": "corr-transcript-segments-1",
            },
        )
        self.assertEqual(callback.status_code, 204)
        self.assertEqual(store.jobs[created_job["id"]].status, JobStatus.TRANSCRIPT_READY)

        transcript = client.get(
            f"/api/v1/jobs/{created_job['id']}/transcript?limit=3",
            headers=owner_headers,
        )
        self.assertEqual(transcript.status_code, 200)
        payload = transcript.json()
        self.assertEqual(payload["next_cursor"], None)
        self.assertEqual(
            payload["items"],
            [
                {"start_ms": 1000, "end_ms": 1500, "text": "first"},
                {"start_ms": 2000, "end_ms": 2500, "text": "second"},
                {"start_ms": 3000, "end_ms": 3500, "text": "third"},
            ],
        )

    def test_get_transcript_cross_owner_and_missing_job_are_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}
        other_headers = {"Authorization": "Bearer test:owner-2:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.jobs[created_job["id"]].status = JobStatus.TRANSCRIPT_READY
        store.set_transcript_segments_for_job(
            job_id=created_job["id"],
            segments=[TranscriptSegment(start_ms=0, end_ms=500, text="segment")],
        )
        before_job_writes = store.job_write_count
        before_dispatch_writes = store.dispatch_write_count

        cross_owner = client.get(
            f"/api/v1/jobs/{created_job['id']}/transcript",
            headers=other_headers,
        )
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)

        missing = client.get("/api/v1/jobs/job-missing/transcript", headers=other_headers)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)

    def test_get_transcript_disallowed_state_returns_409_without_side_effects(self) -> None:
        disallowed_statuses = (
            JobStatus.CREATED,
            JobStatus.AUDIO_EXTRACTING,
            JobStatus.REGENERATING,
            JobStatus.CANCELLED,
        )
        for disallowed_status in disallowed_statuses:
            with self.subTest(disallowed_status=disallowed_status):
                app = create_app()
                client = TestClient(app)
                store = app.state.store
                owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

                project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
                created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
                store.jobs[created_job["id"]].status = disallowed_status
                before_job_writes = store.job_write_count
                before_dispatch_writes = store.dispatch_write_count

                response = client.get(
                    f"/api/v1/jobs/{created_job['id']}/transcript",
                    headers=owner_headers,
                )

                self.assertEqual(response.status_code, 409)
                self.assertEqual(response.json()["code"], "TRANSCRIPT_NOT_READY")
                self.assertEqual(response.json()["details"]["current_status"], disallowed_status.value)
                self.assertEqual(store.job_write_count, before_job_writes)
                self.assertEqual(store.dispatch_write_count, before_dispatch_writes)

    def test_cancel_job_success_returns_200_and_emits_transition_audit(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        client.post(
            f"/api/v1/jobs/{created_job['id']}/confirm-upload",
            headers=owner_headers,
            json={"video_uri": "s3://bucket/video.mp4"},
        )
        started = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)
        self.assertEqual(started.status_code, 202)

        before_job_writes = store.job_write_count
        before_transition_audit_count = len(store.transition_audit_events)
        cancel = client.post(
            f"/api/v1/jobs/{created_job['id']}/cancel",
            headers={**owner_headers, "X-Correlation-Id": "corr-cancel-1"},
        )

        self.assertEqual(cancel.status_code, 200)
        self.assertEqual(cancel.json()["status"], "CANCELLED")
        self.assertEqual(store.job_write_count, before_job_writes + 1)
        self.assertEqual(len(store.transition_audit_events), before_transition_audit_count + 1)
        audit = store.transition_audit_events[-1]
        self.assertEqual(audit.event_type, "JOB_STATUS_TRANSITION_APPLIED")
        self.assertEqual(audit.job_id, created_job["id"])
        self.assertEqual(audit.project_id, project["id"])
        self.assertEqual(audit.actor_type, "editor")
        self.assertEqual(audit.prev_status, JobStatus.AUDIO_EXTRACTING)
        self.assertEqual(audit.new_status, JobStatus.CANCELLED)
        self.assertIsInstance(audit.occurred_at, datetime)
        self.assertEqual(audit.occurred_at.tzinfo, UTC)
        self.assertIsInstance(audit.recorded_at, datetime)
        self.assertEqual(audit.recorded_at.tzinfo, UTC)
        self.assertEqual(audit.correlation_id, "corr-cancel-1")
        self.assertIsNone(store.get_dispatch_for_job(created_job["id"]))

        rerun = client.post(f"/api/v1/jobs/{created_job['id']}/run", headers=owner_headers)
        self.assertEqual(rerun.status_code, 409)
        self.assertEqual(rerun.json()["code"], "FSM_TERMINAL_IMMUTABLE")
        self.assertEqual(rerun.json()["details"]["current_status"], "CANCELLED")
        self.assertEqual(rerun.json()["details"]["attempted_status"], "AUDIO_EXTRACTING")
        self.assertEqual(rerun.json()["details"]["allowed_next_statuses"], [])

    def test_cancel_job_non_cancellable_state_returns_409_without_side_effects(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.jobs[created_job["id"]].status = JobStatus.DRAFT_READY
        before_job_writes = store.job_write_count
        before_transition_audit_count = len(store.transition_audit_events)

        response = client.post(f"/api/v1/jobs/{created_job['id']}/cancel", headers=owner_headers)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "FSM_TRANSITION_INVALID")
        self.assertEqual(response.json()["details"]["current_status"], "DRAFT_READY")
        self.assertEqual(response.json()["details"]["attempted_status"], "CANCELLED")
        self.assertEqual(
            set(response.json()["details"]["allowed_next_statuses"]),
            {"DONE", "EDITING", "EXPORTING", "REGENERATING"},
        )
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(len(store.transition_audit_events), before_transition_audit_count)
        self.assertEqual(store.jobs[created_job["id"]].status, JobStatus.DRAFT_READY)

    def test_cancel_job_terminal_state_returns_409_without_side_effects(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.jobs[created_job["id"]].status = JobStatus.DONE
        before_job_writes = store.job_write_count
        before_transition_audit_count = len(store.transition_audit_events)

        response = client.post(f"/api/v1/jobs/{created_job['id']}/cancel", headers=owner_headers)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "FSM_TERMINAL_IMMUTABLE")
        self.assertEqual(response.json()["details"]["current_status"], "DONE")
        self.assertEqual(response.json()["details"]["attempted_status"], "CANCELLED")
        self.assertEqual(response.json()["details"]["allowed_next_statuses"], [])
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(len(store.transition_audit_events), before_transition_audit_count)
        self.assertEqual(store.jobs[created_job["id"]].status, JobStatus.DONE)

    def test_cancel_job_cross_owner_and_missing_job_are_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}
        other_headers = {"Authorization": "Bearer test:owner-2:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        before_job_writes = store.job_write_count
        before_transition_audit_count = len(store.transition_audit_events)

        cross_owner = client.post(f"/api/v1/jobs/{created_job['id']}/cancel", headers=other_headers)
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(len(store.transition_audit_events), before_transition_audit_count)

        missing = client.post("/api/v1/jobs/job-missing/cancel", headers=other_headers)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(len(store.transition_audit_events), before_transition_audit_count)

    def test_cancel_job_without_correlation_header_generates_request_correlation_id_for_audit(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()

        response = client.post(f"/api/v1/jobs/{created_job['id']}/cancel", headers=owner_headers)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(store.transition_audit_events), 1)
        self.assertTrue(store.transition_audit_events[0].correlation_id.startswith("req-"))


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

    def test_confirm_upload_service_enforces_idempotency_and_conflict(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        service = JobService(store)
        job = service.create_job(owner_id="user-a", project_id=project.id)

        first = service.confirm_upload(owner_id="user-a", job_id=job.id, video_uri="s3://bucket/video-a.mp4")
        self.assertFalse(first.replayed)
        self.assertEqual(first.job.status, JobStatus.UPLOADED)
        self.assertEqual(first.job.manifest.video_uri, "s3://bucket/video-a.mp4")
        writes_after_first = store.job_write_count

        replay = service.confirm_upload(owner_id="user-a", job_id=job.id, video_uri="s3://bucket/video-a.mp4")
        self.assertTrue(replay.replayed)
        self.assertEqual(store.job_write_count, writes_after_first)

        with self.assertRaises(ApiError) as conflict:
            service.confirm_upload(owner_id="user-a", job_id=job.id, video_uri="s3://bucket/video-b.mp4")
        self.assertEqual(conflict.exception.status_code, 409)
        self.assertEqual(conflict.exception.payload.code, "VIDEO_URI_CONFLICT")
        self.assertEqual(
            conflict.exception.payload.details,
            {
                "current_video_uri": "s3://bucket/video-a.mp4",
                "submitted_video_uri": "s3://bucket/video-b.mp4",
            },
        )
        self.assertEqual(store.job_write_count, writes_after_first)

    def test_run_job_service_dispatches_once_and_replays(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        service = JobService(store)
        job = service.create_job(owner_id="user-a", project_id=project.id)
        service.confirm_upload(owner_id="user-a", job_id=job.id, video_uri="s3://bucket/video-a.mp4")

        first = service.run_job(owner_id="user-a", job_id=job.id)
        self.assertFalse(first.replayed)
        self.assertEqual(first.status, JobStatus.AUDIO_EXTRACTING)
        self.assertEqual(store.dispatch_write_count, 1)
        writes_after_first = store.job_write_count

        replay = service.run_job(owner_id="user-a", job_id=job.id)
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.dispatch_id, first.dispatch_id)
        self.assertEqual(store.dispatch_write_count, 1)
        self.assertEqual(store.job_write_count, writes_after_first)

    def test_run_job_service_rejects_non_uploaded_and_handles_dispatch_failure(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        service = JobService(store)
        created_job = service.create_job(owner_id="user-a", project_id=project.id)

        with self.assertRaises(ApiError) as invalid_state:
            service.run_job(owner_id="user-a", job_id=created_job.id)
        self.assertEqual(invalid_state.exception.status_code, 409)
        self.assertEqual(invalid_state.exception.payload.code, "FSM_TRANSITION_INVALID")
        self.assertEqual(invalid_state.exception.payload.details["current_status"], JobStatus.CREATED)
        self.assertEqual(
            set(invalid_state.exception.payload.details["allowed_next_statuses"]),
            {JobStatus.UPLOADING, JobStatus.UPLOADED, JobStatus.CANCELLED},
        )
        self.assertEqual(store.dispatch_write_count, 0)

        for terminal_status in (JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.DONE):
            with self.subTest(terminal_status=terminal_status):
                terminal_job = service.create_job(owner_id="user-a", project_id=project.id)
                store.jobs[terminal_job.id].status = terminal_status
                before_dispatch_writes = store.dispatch_write_count
                before_job_writes = store.job_write_count

                with self.assertRaises(ApiError) as terminal_error:
                    service.run_job(owner_id="user-a", job_id=terminal_job.id)
                self.assertEqual(terminal_error.exception.status_code, 409)
                self.assertEqual(terminal_error.exception.payload.code, "FSM_TERMINAL_IMMUTABLE")
                self.assertEqual(terminal_error.exception.payload.details["current_status"], terminal_status)
                self.assertEqual(
                    terminal_error.exception.payload.details["attempted_status"],
                    JobStatus.AUDIO_EXTRACTING,
                )
                self.assertEqual(terminal_error.exception.payload.details["allowed_next_statuses"], [])
                self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
                self.assertEqual(store.job_write_count, before_job_writes)

        uploaded_job = service.create_job(owner_id="user-a", project_id=project.id)
        service.confirm_upload(owner_id="user-a", job_id=uploaded_job.id, video_uri="s3://bucket/video-b.mp4")
        before_status = store.jobs[uploaded_job.id].status

        store.dispatch_failure_message = "dispatch down"
        with self.assertRaises(ApiError) as dispatch_error:
            service.run_job(owner_id="user-a", job_id=uploaded_job.id)
        self.assertEqual(dispatch_error.exception.status_code, 502)
        self.assertEqual(dispatch_error.exception.payload.code, "ORCHESTRATOR_DISPATCH_FAILED")
        self.assertEqual(store.jobs[uploaded_job.id].status, before_status)
        self.assertIsNone(store.get_dispatch_for_job(uploaded_job.id))

    def test_run_job_service_rejects_missing_dispatch_record_or_video_uri(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        service = JobService(store)

        job = service.create_job(owner_id="user-a", project_id=project.id)
        service.confirm_upload(owner_id="user-a", job_id=job.id, video_uri="s3://bucket/video-a.mp4")
        service.run_job(owner_id="user-a", job_id=job.id)
        store.workflow_dispatches_by_job.pop(job.id, None)
        before_dispatch_writes = store.dispatch_write_count

        with self.assertRaises(ApiError) as in_progress_retry:
            service.run_job(owner_id="user-a", job_id=job.id)
        self.assertEqual(in_progress_retry.exception.status_code, 409)
        self.assertEqual(in_progress_retry.exception.payload.code, "FSM_TRANSITION_INVALID")
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)

        drift_job = service.create_job(owner_id="user-a", project_id=project.id)
        store.jobs[drift_job.id].status = JobStatus.UPLOADED
        store.jobs[drift_job.id].manifest = None
        before_dispatch_writes = store.dispatch_write_count

        with self.assertRaises(ApiError) as missing_video_uri:
            service.run_job(owner_id="user-a", job_id=drift_job.id)
        self.assertEqual(missing_video_uri.exception.status_code, 409)
        self.assertEqual(missing_video_uri.exception.payload.code, "FSM_TRANSITION_INVALID")
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)

    def test_run_job_service_does_not_replay_retry_dispatch_records(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        service = JobService(store)
        job = service.create_job(owner_id="user-a", project_id=project.id)
        service.confirm_upload(owner_id="user-a", job_id=job.id, video_uri="s3://bucket/video-a.mp4")
        service.run_job(owner_id="user-a", job_id=job.id)
        store.jobs[job.id].status = JobStatus.FAILED
        service.retry_job(
            owner_id="user-a",
            job_id=job.id,
            model_profile="cloud-default",
            client_request_id="retry-unit-run-guard-1",
        )
        self.assertEqual(store.get_dispatch_for_job(job.id).dispatch_type, "retry")
        before_dispatch_writes = store.dispatch_write_count
        before_job_writes = store.job_write_count

        with self.assertRaises(ApiError) as rerun_error:
            service.run_job(owner_id="user-a", job_id=job.id)
        self.assertEqual(rerun_error.exception.status_code, 409)
        self.assertEqual(rerun_error.exception.payload.code, "FSM_TERMINAL_IMMUTABLE")
        self.assertEqual(rerun_error.exception.payload.details["current_status"], JobStatus.FAILED)
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertEqual(store.job_write_count, before_job_writes)

    def test_retry_job_service_dispatches_persists_and_replays(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        service = JobService(store)
        job = service.create_job(owner_id="user-a", project_id=project.id)
        service.confirm_upload(owner_id="user-a", job_id=job.id, video_uri="s3://bucket/video-a.mp4")
        service.run_job(owner_id="user-a", job_id=job.id)

        record = store.jobs[job.id]
        record.status = JobStatus.FAILED
        record.manifest = record.manifest.model_copy(update={"audio_uri": "s3://bucket/audio-a.wav"})
        record.manifest = record.manifest.model_copy(update={"transcript_uri": "s3://bucket/transcript-a.json"})

        first = service.retry_job(
            owner_id="user-a",
            job_id=job.id,
            model_profile="cloud-default",
            client_request_id="retry-unit-1",
        )
        self.assertFalse(first.replayed)
        self.assertEqual(first.status, JobStatus.FAILED)
        self.assertEqual(first.resume_from_status, JobStatus.TRANSCRIPT_READY)
        self.assertEqual(first.checkpoint_ref, "s3://bucket/transcript-a.json")
        self.assertEqual(first.model_profile, "cloud-default")
        self.assertEqual(store.dispatch_write_count, 2)
        self.assertEqual(store.jobs[job.id].retry_resume_from_status, JobStatus.TRANSCRIPT_READY)
        self.assertEqual(store.jobs[job.id].retry_checkpoint_ref, "s3://bucket/transcript-a.json")
        self.assertEqual(store.jobs[job.id].retry_model_profile, "cloud-default")
        self.assertEqual(store.jobs[job.id].retry_client_request_id, "retry-unit-1")
        self.assertEqual(store.jobs[job.id].retry_dispatch_id, first.dispatch_id)
        dispatch = store.get_dispatch_for_job(job.id)
        self.assertIsNotNone(dispatch)
        self.assertEqual(dispatch.dispatch_type, "retry")
        self.assertEqual(
            dispatch.payload,
            {
                "job_id": job.id,
                "project_id": project.id,
                "video_uri": "s3://bucket/video-a.mp4",
                "callback_url": f"/api/v1/internal/jobs/{job.id}/status",
                "resume_from_status": "TRANSCRIPT_READY",
                "checkpoint_ref": "s3://bucket/transcript-a.json",
                "model_profile": "cloud-default",
            },
        )

        writes_after_first = store.dispatch_write_count
        job_writes_after_first = store.job_write_count
        replay = service.retry_job(
            owner_id="user-a",
            job_id=job.id,
            model_profile="cloud-default",
            client_request_id="retry-unit-1",
        )
        self.assertTrue(replay.replayed)
        self.assertEqual(replay.dispatch_id, first.dispatch_id)
        self.assertEqual(store.dispatch_write_count, writes_after_first)
        self.assertEqual(store.job_write_count, job_writes_after_first)

    def test_retry_job_service_rejects_non_failed_or_running_and_handles_dispatch_failure(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        service = JobService(store)

        non_failed_job = service.create_job(owner_id="user-a", project_id=project.id)
        store.jobs[non_failed_job.id].status = JobStatus.DRAFT_READY
        before_dispatch_writes = store.dispatch_write_count
        before_job_writes = store.job_write_count
        with self.assertRaises(ApiError) as non_failed_error:
            service.retry_job(
                owner_id="user-a",
                job_id=non_failed_job.id,
                model_profile="cloud-default",
                client_request_id="retry-unit-non-failed",
            )
        self.assertEqual(non_failed_error.exception.status_code, 409)
        self.assertEqual(non_failed_error.exception.payload.code, "RETRY_NOT_ALLOWED_STATE")
        self.assertEqual(
            non_failed_error.exception.payload.details["attempted_status"],
            JobStatus.REGENERATING,
        )
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertEqual(store.job_write_count, before_job_writes)

        running_job = service.create_job(owner_id="user-a", project_id=project.id)
        store.jobs[running_job.id].status = JobStatus.GENERATING
        before_dispatch_writes = store.dispatch_write_count
        before_job_writes = store.job_write_count
        with self.assertRaises(ApiError) as running_error:
            service.retry_job(
                owner_id="user-a",
                job_id=running_job.id,
                model_profile="cloud-default",
                client_request_id="retry-unit-running",
            )
        self.assertEqual(running_error.exception.status_code, 409)
        self.assertEqual(running_error.exception.payload.code, "JOB_ALREADY_RUNNING")
        self.assertEqual(running_error.exception.payload.details["current_status"], JobStatus.GENERATING)
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertEqual(store.job_write_count, before_job_writes)

        failing_job = service.create_job(owner_id="user-a", project_id=project.id)
        service.confirm_upload(owner_id="user-a", job_id=failing_job.id, video_uri="s3://bucket/video-b.mp4")
        store.jobs[failing_job.id].status = JobStatus.FAILED
        before_dispatch_writes = store.dispatch_write_count
        before_job_writes = store.job_write_count
        store.dispatch_failure_message = "dispatch down"
        with self.assertRaises(ApiError) as dispatch_error:
            service.retry_job(
                owner_id="user-a",
                job_id=failing_job.id,
                model_profile="cloud-default",
                client_request_id="retry-unit-dispatch-failure",
            )
        self.assertEqual(dispatch_error.exception.status_code, 502)
        self.assertEqual(dispatch_error.exception.payload.code, "ORCHESTRATOR_DISPATCH_FAILED")
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertIsNone(store.jobs[failing_job.id].retry_dispatch_id)

    def test_retry_job_service_is_owner_scoped_with_no_leak_404(self) -> None:
        store = InMemoryStore()
        project_a = store.create_project(owner_id="user-a", name="Project A")
        service = JobService(store)
        job = service.create_job(owner_id="user-a", project_id=project_a.id)
        store.jobs[job.id].status = JobStatus.FAILED
        store.jobs[job.id].manifest = ArtifactManifest(video_uri="s3://bucket/video-a.mp4")

        with self.assertRaises(ApiError) as cross_owner_error:
            service.retry_job(
                owner_id="user-b",
                job_id=job.id,
                model_profile="cloud-default",
                client_request_id="retry-unit-cross-owner",
            )
        self.assertEqual(cross_owner_error.exception.status_code, 404)
        self.assertEqual(cross_owner_error.exception.payload.code, "RESOURCE_NOT_FOUND")

        with self.assertRaises(ApiError) as missing_job_error:
            service.retry_job(
                owner_id="user-a",
                job_id="missing-job",
                model_profile="cloud-default",
                client_request_id="retry-unit-missing",
            )
        self.assertEqual(missing_job_error.exception.status_code, 404)
        self.assertEqual(missing_job_error.exception.payload.code, "RESOURCE_NOT_FOUND")

    def test_get_transcript_service_orders_and_paginates_segments(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        service = JobService(store)
        job = service.create_job(owner_id="user-a", project_id=project.id)
        store.jobs[job.id].status = JobStatus.TRANSCRIPT_READY
        store.set_transcript_segments_for_job(
            job_id=job.id,
            segments=[
                TranscriptSegment(start_ms=3000, end_ms=3500, text="third"),
                TranscriptSegment(start_ms=1000, end_ms=1500, text="first"),
                TranscriptSegment(start_ms=2000, end_ms=2500, text="second"),
            ],
        )

        first = service.get_transcript(owner_id="user-a", job_id=job.id, limit=2, cursor=None)
        self.assertEqual(first.limit, 2)
        self.assertEqual(first.next_cursor, "2")
        self.assertEqual(
            [segment.start_ms for segment in first.items],
            [1000, 2000],
        )

        second = service.get_transcript(owner_id="user-a", job_id=job.id, limit=2, cursor=first.next_cursor)
        self.assertEqual(second.limit, 2)
        self.assertIsNone(second.next_cursor)
        self.assertEqual([segment.start_ms for segment in second.items], [3000])

        replay_from_invalid_cursor = service.get_transcript(owner_id="user-a", job_id=job.id, limit=2, cursor="bad")
        self.assertEqual([segment.start_ms for segment in replay_from_invalid_cursor.items], [1000, 2000])

    def test_get_transcript_service_rejects_disallowed_state_without_side_effects(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        service = JobService(store)
        job = service.create_job(owner_id="user-a", project_id=project.id)
        store.jobs[job.id].status = JobStatus.AUDIO_EXTRACTING
        before_job_writes = store.job_write_count
        before_dispatch_writes = store.dispatch_write_count

        with self.assertRaises(ApiError) as transcript_error:
            service.get_transcript(owner_id="user-a", job_id=job.id, limit=200, cursor=None)
        self.assertEqual(transcript_error.exception.status_code, 409)
        self.assertEqual(transcript_error.exception.payload.code, "TRANSCRIPT_NOT_READY")
        self.assertEqual(
            transcript_error.exception.payload.details["current_status"],
            JobStatus.AUDIO_EXTRACTING,
        )
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)

    def test_get_transcript_service_rejects_invalid_limit_without_side_effects(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        service = JobService(store)
        job = service.create_job(owner_id="user-a", project_id=project.id)
        store.jobs[job.id].status = JobStatus.TRANSCRIPT_READY
        before_job_writes = store.job_write_count
        before_dispatch_writes = store.dispatch_write_count

        with self.assertRaises(ApiError) as transcript_error:
            service.get_transcript(owner_id="user-a", job_id=job.id, limit=0, cursor=None)
        self.assertEqual(transcript_error.exception.status_code, 409)
        self.assertEqual(transcript_error.exception.payload.code, "VALIDATION_ERROR")
        self.assertEqual(
            transcript_error.exception.payload.details,
            {"limit": 0, "min_limit": 1, "max_limit": 500},
        )
        self.assertEqual(store.job_write_count, before_job_writes)
        self.assertEqual(store.dispatch_write_count, before_dispatch_writes)

    def test_get_transcript_service_is_owner_scoped_with_no_leak_404(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        service = JobService(store)
        job = service.create_job(owner_id="user-a", project_id=project.id)
        store.jobs[job.id].status = JobStatus.TRANSCRIPT_READY

        with self.assertRaises(ApiError) as cross_owner_error:
            service.get_transcript(owner_id="user-b", job_id=job.id, limit=200, cursor=None)
        self.assertEqual(cross_owner_error.exception.status_code, 404)
        self.assertEqual(cross_owner_error.exception.payload.code, "RESOURCE_NOT_FOUND")

        with self.assertRaises(ApiError) as missing_job_error:
            service.get_transcript(owner_id="user-a", job_id="missing-job", limit=200, cursor=None)
        self.assertEqual(missing_job_error.exception.status_code, 404)
        self.assertEqual(missing_job_error.exception.payload.code, "RESOURCE_NOT_FOUND")

    def test_cancel_job_service_enforces_fsm_and_emits_transition_audit(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        service = JobService(store)
        job = service.create_job(owner_id="user-a", project_id=project.id)
        service.confirm_upload(owner_id="user-a", job_id=job.id, video_uri="s3://bucket/video-a.mp4")
        service.run_job(owner_id="user-a", job_id=job.id)
        writes_before_cancel = store.job_write_count

        cancelled = service.cancel_job(owner_id="user-a", job_id=job.id, correlation_id="corr-cancel-unit-1")
        self.assertEqual(cancelled.status, JobStatus.CANCELLED)
        self.assertEqual(store.job_write_count, writes_before_cancel + 1)
        self.assertEqual(len(store.transition_audit_events), 1)
        self.assertEqual(store.transition_audit_events[0].actor_type, "editor")
        self.assertEqual(store.transition_audit_events[0].prev_status, JobStatus.AUDIO_EXTRACTING)
        self.assertEqual(store.transition_audit_events[0].new_status, JobStatus.CANCELLED)
        self.assertEqual(store.transition_audit_events[0].correlation_id, "corr-cancel-unit-1")
        self.assertIsNone(store.get_dispatch_for_job(job.id))

        with self.assertRaises(ApiError) as run_after_cancel:
            service.run_job(owner_id="user-a", job_id=job.id)
        self.assertEqual(run_after_cancel.exception.status_code, 409)
        self.assertEqual(run_after_cancel.exception.payload.code, "FSM_TERMINAL_IMMUTABLE")
        self.assertEqual(run_after_cancel.exception.payload.details["current_status"], JobStatus.CANCELLED)
        self.assertEqual(
            run_after_cancel.exception.payload.details["attempted_status"],
            JobStatus.AUDIO_EXTRACTING,
        )

        writes_after_cancel = store.job_write_count
        audits_after_cancel = len(store.transition_audit_events)
        with self.assertRaises(ApiError) as terminal_error:
            service.cancel_job(owner_id="user-a", job_id=job.id, correlation_id="corr-cancel-unit-2")
        self.assertEqual(terminal_error.exception.status_code, 409)
        self.assertEqual(terminal_error.exception.payload.code, "FSM_TERMINAL_IMMUTABLE")
        self.assertEqual(store.job_write_count, writes_after_cancel)
        self.assertEqual(len(store.transition_audit_events), audits_after_cancel)
