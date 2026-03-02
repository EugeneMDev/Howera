"""Ownership and no-leak job API tests for Story 1.3."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import os
import unittest
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.errors import ApiError
from app.main import create_app
from app.repositories.memory import InMemoryStore
from app.schemas.job import (
    AnchorAddress,
    AnchorAddressType,
    AttachUploadedAssetRequest,
    ArtifactManifest,
    ConfirmCustomUploadRequest,
    CreateCustomUploadRequest,
    JobStatus,
    ScreenshotExtractionRequest,
    ScreenshotFormat,
    ScreenshotAnchorCreateRequest,
    ScreenshotMimeType,
    ScreenshotReplaceRequest,
    ScreenshotStrategy,
    ScreenshotTaskStatus,
    TranscriptSegment,
)
from app.services.jobs import JobService


def _checksum(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


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

    def test_request_screenshot_extract_first_accepts_202_and_replays_canonical_request_as_200(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-s1:editor"}

        project = store.create_project(owner_id="owner-s1", name="Owned")
        job = store.create_job(owner_id="owner-s1", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-s1",
            instruction_id="inst-s1",
            job_id=job.id,
            version=1,
            markdown="# screenshot source",
        )
        payload = {
            "instruction_id": "inst-s1",
            "instruction_version_id": "1",
            "timestamp_ms": 12000,
            "offset_ms": 500,
            "strategy": "precise",
            "format": "png",
        }
        before_task_writes = store.screenshot_task_write_count

        first = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json=payload,
        )
        self.assertEqual(first.status_code, 202)
        first_payload = first.json()
        self.assertEqual(first_payload["status"], "PENDING")
        self.assertEqual(first_payload["operation"], "extract")
        self.assertEqual(store.screenshot_task_write_count, before_task_writes + 1)

        replay = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json=payload,
        )
        self.assertEqual(replay.status_code, 200)
        replay_payload = replay.json()
        self.assertEqual(replay_payload["task_id"], first_payload["task_id"])
        self.assertEqual(replay_payload["status"], "PENDING")
        self.assertEqual(replay_payload["operation"], "extract")
        self.assertEqual(store.screenshot_task_write_count, before_task_writes + 1)

    def test_request_screenshot_extract_duplicate_idempotency_key_with_different_payload_returns_400(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-s2:editor"}

        project = store.create_project(owner_id="owner-s2", name="Owned")
        job = store.create_job(owner_id="owner-s2", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-s2",
            instruction_id="inst-s2",
            job_id=job.id,
            version=1,
            markdown="# screenshot source",
        )

        first = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-s2",
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
                "offset_ms": 0,
                "strategy": "precise",
                "format": "png",
                "idempotency_key": "shot-req-2",
            },
        )
        self.assertEqual(first.status_code, 202)
        writes_after_first = store.screenshot_task_write_count

        mismatch = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-s2",
                "instruction_version_id": "1",
                "timestamp_ms": 12001,
                "offset_ms": 0,
                "strategy": "precise",
                "format": "png",
                "idempotency_key": "shot-req-2",
            },
        )
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(mismatch.json()["code"], "VALIDATION_ERROR")
        self.assertEqual(store.screenshot_task_write_count, writes_after_first)

    def test_request_screenshot_extract_invalid_payload_returns_400_without_side_effects(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-s3:editor"}

        project = store.create_project(owner_id="owner-s3", name="Owned")
        job = store.create_job(owner_id="owner-s3", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-s3",
            instruction_id="inst-s3",
            job_id=job.id,
            version=1,
            markdown="# screenshot source",
        )
        before_task_writes = store.screenshot_task_write_count
        before_job_writes = store.job_write_count

        response = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={"instruction_id": "inst-s3"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "VALIDATION_ERROR")
        self.assertEqual(store.screenshot_task_write_count, before_task_writes)
        self.assertEqual(store.job_write_count, before_job_writes)

    def test_request_screenshot_extract_cross_owner_or_missing_context_are_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-s4:editor"}
        other_headers = {"Authorization": "Bearer test:owner-s4-other:editor"}

        project = store.create_project(owner_id="owner-s4", name="Owned")
        job = store.create_job(owner_id="owner-s4", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-s4",
            instruction_id="inst-s4",
            job_id=job.id,
            version=1,
            markdown="# screenshot source",
        )
        before_task_writes = store.screenshot_task_write_count

        payload = {
            "instruction_id": "inst-s4",
            "instruction_version_id": "1",
            "timestamp_ms": 12000,
        }
        cross_owner = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=other_headers,
            json=payload,
        )
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing_job = client.post(
            "/api/v1/jobs/job-missing/screenshots/extract",
            headers=owner_headers,
            json=payload,
        )
        self.assertEqual(missing_job.status_code, 404)
        self.assertEqual(missing_job.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing_instruction = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-missing",
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
            },
        )
        self.assertEqual(missing_instruction.status_code, 404)
        self.assertEqual(missing_instruction.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(store.screenshot_task_write_count, before_task_writes)

    def test_create_screenshot_anchor_supports_block_id_and_char_range_addressing(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-a1:editor"}

        project = store.create_project(owner_id="owner-a1", name="Owned")
        job = store.create_job(owner_id="owner-a1", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-a1",
            instruction_id="inst-a1",
            job_id=job.id,
            version=1,
            markdown="# Intro {#intro}\n\nBody text",
        )

        before_anchor_count = len(store.screenshot_anchors_by_id)
        block_id_created = client.post(
            "/api/v1/instructions/inst-a1/anchors",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "addressing": {
                    "address_type": "block_id",
                    "block_id": "intro",
                    "strategy": "block_id_primary",
                },
            },
        )
        self.assertEqual(block_id_created.status_code, 201)
        block_payload = block_id_created.json()
        self.assertEqual(block_payload["instruction_id"], "inst-a1")
        self.assertEqual(block_payload["instruction_version_id"], "1")
        self.assertEqual(block_payload["addressing"]["address_type"], "block_id")
        self.assertEqual(block_payload["addressing"]["block_id"], "intro")
        self.assertEqual(block_payload["addressing"]["strategy"], "block_id_primary")
        self.assertIsNone(block_payload["active_asset_id"])
        self.assertEqual(len(store.screenshot_anchors_by_id), before_anchor_count + 1)

        char_range_created = client.post(
            "/api/v1/instructions/inst-a1/anchors",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "addressing": {
                    "address_type": "char_range",
                    "char_range": {"start_offset": 0, "end_offset": 5},
                },
            },
        )
        self.assertEqual(char_range_created.status_code, 201)
        char_range_payload = char_range_created.json()
        self.assertEqual(char_range_payload["addressing"]["address_type"], "char_range")
        self.assertEqual(char_range_payload["addressing"]["char_range"], {"start_offset": 0, "end_offset": 5})
        self.assertEqual(char_range_payload["addressing"]["strategy"], "char_range_fallback")
        self.assertEqual(len(store.screenshot_anchors_by_id), before_anchor_count + 2)

    def test_create_screenshot_anchor_invalid_addressing_or_context_returns_404_without_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-a2:editor"}
        other_headers = {"Authorization": "Bearer test:owner-a2-other:editor"}

        project = store.create_project(owner_id="owner-a2", name="Owned")
        job = store.create_job(owner_id="owner-a2", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-a2",
            instruction_id="inst-a2",
            job_id=job.id,
            version=1,
            markdown="# Intro {#intro}",
        )

        before_anchor_count = len(store.screenshot_anchors_by_id)
        invalid_addressing = client.post(
            "/api/v1/instructions/inst-a2/anchors",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "addressing": {
                    "address_type": "block_id",
                    "char_range": {"start_offset": 0, "end_offset": 5},
                },
            },
        )
        self.assertEqual(invalid_addressing.status_code, 404)
        self.assertEqual(invalid_addressing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        invalid_version = client.post(
            "/api/v1/instructions/inst-a2/anchors",
            headers=owner_headers,
            json={
                "instruction_version_id": "v0",
                "addressing": {"address_type": "block_id", "block_id": "intro"},
            },
        )
        self.assertEqual(invalid_version.status_code, 404)
        self.assertEqual(invalid_version.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing_block_reference = client.post(
            "/api/v1/instructions/inst-a2/anchors",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "addressing": {"address_type": "block_id", "block_id": "missing-block-id"},
            },
        )
        self.assertEqual(missing_block_reference.status_code, 404)
        self.assertEqual(
            missing_block_reference.json(),
            {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"},
        )

        out_of_bounds_char_range = client.post(
            "/api/v1/instructions/inst-a2/anchors",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "addressing": {
                    "address_type": "char_range",
                    "char_range": {"start_offset": 99, "end_offset": 120},
                },
            },
        )
        self.assertEqual(out_of_bounds_char_range.status_code, 404)
        self.assertEqual(
            out_of_bounds_char_range.json(),
            {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"},
        )

        cross_owner = client.post(
            "/api/v1/instructions/inst-a2/anchors",
            headers=other_headers,
            json={
                "instruction_version_id": "1",
                "addressing": {"address_type": "block_id", "block_id": "intro"},
            },
        )
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(len(store.screenshot_anchors_by_id), before_anchor_count)

    def test_list_screenshot_anchors_applies_instruction_version_and_deleted_asset_filters(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-a3:editor"}

        project = store.create_project(owner_id="owner-a3", name="Owned")
        job = store.create_job(owner_id="owner-a3", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-a3",
            instruction_id="inst-a3",
            job_id=job.id,
            version=1,
            markdown="# Intro {#intro}\n\nText",
        )
        store.create_instruction_version(
            owner_id="owner-a3",
            instruction_id="inst-a3",
            job_id=job.id,
            version=2,
            markdown="# Intro v2 {#intro-v2}\n\nText",
        )

        created_v1 = client.post(
            "/api/v1/instructions/inst-a3/anchors",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "addressing": {"address_type": "block_id", "block_id": "intro"},
            },
        )
        self.assertEqual(created_v1.status_code, 201)
        first_anchor_id = created_v1.json()["id"]

        created_v2 = client.post(
            "/api/v1/instructions/inst-a3/anchors",
            headers=owner_headers,
            json={
                "instruction_version_id": "2",
                "addressing": {"address_type": "block_id", "block_id": "intro-v2"},
            },
        )
        self.assertEqual(created_v2.status_code, 201)

        extract = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-a3",
                "instruction_version_id": "1",
                "anchor_id": first_anchor_id,
                "timestamp_ms": 1000,
            },
        )
        self.assertEqual(extract.status_code, 202)
        completed_extract = store.complete_screenshot_task_success(
            task_id=extract.json()["task_id"],
            image_uri="s3://bucket/screenshots/a3-base.png",
            width=1000,
            height=500,
        )
        base_asset_id = completed_extract.asset_id
        assert base_asset_id is not None

        replace = client.post(
            f"/api/v1/anchors/{first_anchor_id}/replace",
            headers=owner_headers,
            json={"instruction_version_id": "1", "timestamp_ms": 1500},
        )
        self.assertEqual(replace.status_code, 202)
        completed_replace = store.complete_screenshot_task_success(
            task_id=replace.json()["task_id"],
            image_uri="s3://bucket/screenshots/a3-replace.png",
            width=1000,
            height=500,
        )
        replaced_asset_id = completed_replace.asset_id
        assert replaced_asset_id is not None

        deleted = client.delete(
            f"/api/v1/anchors/{first_anchor_id}/assets/{replaced_asset_id}",
            headers=owner_headers,
        )
        self.assertEqual(deleted.status_code, 200)

        listed_default = client.get("/api/v1/instructions/inst-a3/anchors", headers=owner_headers)
        self.assertEqual(listed_default.status_code, 200)
        listed_default_payload = listed_default.json()
        self.assertEqual(len(listed_default_payload), 2)
        listed_default_first = next(anchor for anchor in listed_default_payload if anchor["id"] == first_anchor_id)
        self.assertEqual(len(listed_default_first["assets"]), 1)
        self.assertEqual(listed_default_first["assets"][0]["id"], base_asset_id)
        self.assertFalse(listed_default_first["assets"][0]["is_deleted"])

        listed_with_deleted = client.get(
            "/api/v1/instructions/inst-a3/anchors?instruction_version_id=1&include_deleted_assets=true",
            headers=owner_headers,
        )
        self.assertEqual(listed_with_deleted.status_code, 200)
        listed_with_deleted_payload = listed_with_deleted.json()
        self.assertEqual(len(listed_with_deleted_payload), 1)
        asset_ids = {asset["id"] for asset in listed_with_deleted_payload[0]["assets"]}
        self.assertEqual(asset_ids, {base_asset_id, replaced_asset_id})
        self.assertEqual(sum(1 for asset in listed_with_deleted_payload[0]["assets"] if asset["is_deleted"]), 1)

    def test_get_screenshot_anchor_supports_resolution_projection_and_no_leak(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-a4:editor"}
        other_headers = {"Authorization": "Bearer test:owner-a4-other:editor"}

        project = store.create_project(owner_id="owner-a4", name="Owned")
        job = store.create_job(owner_id="owner-a4", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-a4",
            instruction_id="inst-a4",
            job_id=job.id,
            version=1,
            markdown="# Intro {#intro}\n## Details {#details}",
        )
        store.create_instruction_version(
            owner_id="owner-a4",
            instruction_id="inst-a4",
            job_id=job.id,
            version=2,
            markdown="# Intro updated {#intro-renamed}\n## Details {#details}",
        )
        store.create_instruction_version(
            owner_id="owner-a4",
            instruction_id="inst-a4",
            job_id=job.id,
            version=3,
            markdown="# Intro without explicit id",
        )

        created = client.post(
            "/api/v1/instructions/inst-a4/anchors",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "addressing": {"address_type": "block_id", "block_id": "intro"},
            },
        )
        self.assertEqual(created.status_code, 201)
        anchor_id = created.json()["id"]

        retained = client.get(
            f"/api/v1/anchors/{anchor_id}?target_instruction_version_id=1",
            headers=owner_headers,
        )
        self.assertEqual(retained.status_code, 200)
        retained_resolution = retained.json()["resolution"]
        self.assertEqual(retained_resolution["resolution_state"], "retain")
        self.assertEqual(retained_resolution["source_instruction_version_id"], "1")
        self.assertEqual(retained_resolution["target_instruction_version_id"], "1")

        remapped = client.get(
            f"/api/v1/anchors/{anchor_id}?target_instruction_version_id=2",
            headers=owner_headers,
        )
        self.assertEqual(remapped.status_code, 200)
        remapped_resolution = remapped.json()["resolution"]
        self.assertEqual(remapped_resolution["resolution_state"], "remap")
        self.assertEqual(remapped_resolution["trace"]["method"], "block_index_remap")
        self.assertEqual(remapped_resolution["trace"]["evidence"]["remapped_block_id"], "intro-renamed")

        unresolved = client.get(
            f"/api/v1/anchors/{anchor_id}?target_instruction_version_id=3",
            headers=owner_headers,
        )
        self.assertEqual(unresolved.status_code, 200)
        unresolved_resolution = unresolved.json()["resolution"]
        self.assertEqual(unresolved_resolution["resolution_state"], "unresolved")
        self.assertEqual(unresolved_resolution["trace"]["method"], "block_index_remap")

        cross_owner = client.get(f"/api/v1/anchors/{anchor_id}", headers=other_headers)
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing_target = client.get(
            f"/api/v1/anchors/{anchor_id}?target_instruction_version_id=99",
            headers=owner_headers,
        )
        self.assertEqual(missing_target.status_code, 404)
        self.assertEqual(missing_target.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

    def test_request_screenshot_replace_first_accepts_202_and_replays_as_200(self) -> None:
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
            markdown="# screenshot source",
        )
        extracted = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-r1",
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
            },
        )
        self.assertEqual(extracted.status_code, 202)
        extracted_task_id = extracted.json()["task_id"]
        completed_extract = store.complete_screenshot_task_success(
            task_id=extracted_task_id,
            image_uri="s3://bucket/screenshots/r1-base.png",
            width=1280,
            height=720,
        )
        anchor_id = completed_extract.anchor_id
        assert anchor_id is not None

        payload = {
            "instruction_version_id": "1",
            "timestamp_ms": 12800,
            "offset_ms": 100,
            "strategy": "precise",
            "format": "png",
        }
        before_task_writes = store.screenshot_task_write_count
        before_asset_count = len(store.screenshot_asset_ids_by_anchor.get(anchor_id, []))

        first = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=owner_headers,
            json=payload,
        )
        self.assertEqual(first.status_code, 202)
        first_payload = first.json()
        self.assertEqual(first_payload["operation"], "replace")
        self.assertEqual(first_payload["status"], "PENDING")
        self.assertEqual(store.screenshot_task_write_count, before_task_writes + 1)
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_asset_count)

        replay = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=owner_headers,
            json=payload,
        )
        self.assertEqual(replay.status_code, 200)
        replay_payload = replay.json()
        self.assertEqual(replay_payload["task_id"], first_payload["task_id"])
        self.assertEqual(replay_payload["operation"], "replace")
        self.assertEqual(store.screenshot_task_write_count, before_task_writes + 1)
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_asset_count)

    def test_request_screenshot_replace_duplicate_idempotency_key_with_different_payload_returns_400(self) -> None:
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
            markdown="# screenshot source",
        )
        extracted = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-r2",
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
            },
        )
        self.assertEqual(extracted.status_code, 202)
        extracted_task_id = extracted.json()["task_id"]
        completed_extract = store.complete_screenshot_task_success(
            task_id=extracted_task_id,
            image_uri="s3://bucket/screenshots/r2-base.png",
            width=1280,
            height=720,
        )
        anchor_id = completed_extract.anchor_id
        assert anchor_id is not None

        first = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "timestamp_ms": 12500,
                "idempotency_key": "replace-req-2",
            },
        )
        self.assertEqual(first.status_code, 202)
        writes_after_first = store.screenshot_task_write_count

        mismatch = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "timestamp_ms": 12501,
                "idempotency_key": "replace-req-2",
            },
        )
        self.assertEqual(mismatch.status_code, 400)
        self.assertEqual(mismatch.json()["code"], "VALIDATION_ERROR")
        self.assertEqual(store.screenshot_task_write_count, writes_after_first)

    def test_request_screenshot_replace_no_leak_and_version_context_validation(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-r3:editor"}
        other_headers = {"Authorization": "Bearer test:owner-r3-other:editor"}

        project = store.create_project(owner_id="owner-r3", name="Owned")
        job = store.create_job(owner_id="owner-r3", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r3",
            instruction_id="inst-r3",
            job_id=job.id,
            version=1,
            markdown="# screenshot source",
        )
        extracted = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-r3",
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
            },
        )
        self.assertEqual(extracted.status_code, 202)
        extracted_task_id = extracted.json()["task_id"]
        completed_extract = store.complete_screenshot_task_success(
            task_id=extracted_task_id,
            image_uri="s3://bucket/screenshots/r3-base.png",
            width=1280,
            height=720,
        )
        anchor_id = completed_extract.anchor_id
        assert anchor_id is not None

        before_task_writes = store.screenshot_task_write_count
        before_job_writes = store.job_write_count

        cross_owner = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=other_headers,
            json={"instruction_version_id": "1", "timestamp_ms": 12800},
        )
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing_anchor = client.post(
            "/api/v1/anchors/anchor-missing-r3/replace",
            headers=owner_headers,
            json={"instruction_version_id": "1", "timestamp_ms": 12800},
        )
        self.assertEqual(missing_anchor.status_code, 404)
        self.assertEqual(missing_anchor.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        mismatched_version = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=owner_headers,
            json={"instruction_version_id": "2", "timestamp_ms": 12800},
        )
        self.assertEqual(mismatched_version.status_code, 404)
        self.assertEqual(mismatched_version.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        invalid_payload = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=owner_headers,
            json={"instruction_version_id": "1"},
        )
        self.assertEqual(invalid_payload.status_code, 400)
        self.assertEqual(invalid_payload.json()["code"], "VALIDATION_ERROR")

        self.assertEqual(store.screenshot_task_write_count, before_task_writes)
        self.assertEqual(store.job_write_count, before_job_writes)

    def test_request_screenshot_replace_matching_active_canonical_key_is_idempotent_no_new_version(self) -> None:
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
            markdown="# screenshot source",
        )
        extracted = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-r4",
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
                "offset_ms": 250,
                "strategy": "nearest_keyframe",
                "format": "jpg",
            },
        )
        self.assertEqual(extracted.status_code, 202)
        extracted_task_id = extracted.json()["task_id"]
        completed_extract = store.complete_screenshot_task_success(
            task_id=extracted_task_id,
            image_uri="s3://bucket/screenshots/r4-base.jpg",
            width=1280,
            height=720,
        )
        anchor_id = completed_extract.anchor_id
        base_asset_id = completed_extract.asset_id
        assert anchor_id is not None
        assert base_asset_id is not None
        before_asset_count = len(store.screenshot_asset_ids_by_anchor.get(anchor_id, []))
        before_task_writes = store.screenshot_task_write_count

        no_op = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
                "offset_ms": 250,
                "strategy": "nearest_keyframe",
                "format": "jpg",
            },
        )
        self.assertEqual(no_op.status_code, 200)
        no_op_payload = no_op.json()
        self.assertEqual(no_op_payload["operation"], "replace")
        self.assertEqual(no_op_payload["status"], "SUCCEEDED")
        self.assertEqual(no_op_payload["asset_id"], base_asset_id)
        self.assertEqual(store.screenshot_task_write_count, before_task_writes + 1)
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_asset_count)

        anchor = store.get_screenshot_anchor_for_owner(owner_id="owner-r4", anchor_id=anchor_id)
        self.assertIsNotNone(anchor)
        assert anchor is not None
        self.assertEqual(anchor.active_asset_id, base_asset_id)

        replay = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
                "offset_ms": 250,
                "strategy": "nearest_keyframe",
                "format": "jpg",
            },
        )
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["task_id"], no_op_payload["task_id"])
        self.assertEqual(store.screenshot_task_write_count, before_task_writes + 1)
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_asset_count)

        switch = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "timestamp_ms": 12222,
                "offset_ms": 0,
                "strategy": "precise",
                "format": "png",
            },
        )
        self.assertEqual(switch.status_code, 202)
        switch_task_id = switch.json()["task_id"]
        store.complete_screenshot_task_success(
            task_id=switch_task_id,
            image_uri="s3://bucket/screenshots/r4-switch.png",
            width=1280,
            height=720,
        )

        back_to_historical = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
                "offset_ms": 250,
                "strategy": "nearest_keyframe",
                "format": "jpg",
            },
        )
        self.assertEqual(back_to_historical.status_code, 202)
        self.assertNotEqual(back_to_historical.json()["task_id"], no_op_payload["task_id"])

    def test_screenshot_replace_completion_updates_version_chain_and_polling_operation(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-r5:editor"}
        other_headers = {"Authorization": "Bearer test:owner-r5-other:editor"}

        project = store.create_project(owner_id="owner-r5", name="Owned")
        job = store.create_job(owner_id="owner-r5", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r5",
            instruction_id="inst-r5",
            job_id=job.id,
            version=1,
            markdown="# screenshot source",
        )
        extracted = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-r5",
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
            },
        )
        self.assertEqual(extracted.status_code, 202)
        extracted_task_id = extracted.json()["task_id"]
        completed_extract = store.complete_screenshot_task_success(
            task_id=extracted_task_id,
            image_uri="s3://bucket/screenshots/r5-base.png",
            width=1280,
            height=720,
        )
        anchor_id = completed_extract.anchor_id
        base_asset_id = completed_extract.asset_id
        assert anchor_id is not None
        assert base_asset_id is not None

        replace = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=owner_headers,
            json={
                "instruction_version_id": "1",
                "timestamp_ms": 18000,
                "offset_ms": 300,
            },
        )
        self.assertEqual(replace.status_code, 202)
        replace_task_id = replace.json()["task_id"]

        completed_replace = store.complete_screenshot_task_success(
            task_id=replace_task_id,
            image_uri="s3://bucket/screenshots/r5-replace.png",
            width=640,
            height=360,
        )
        self.assertEqual(completed_replace.status, ScreenshotTaskStatus.SUCCEEDED)
        replaced_asset_id = completed_replace.asset_id
        assert replaced_asset_id is not None

        owner_poll = client.get(f"/api/v1/screenshot-tasks/{replace_task_id}", headers=owner_headers)
        self.assertEqual(owner_poll.status_code, 200)
        owner_payload = owner_poll.json()
        self.assertEqual(owner_payload["operation"], "replace")
        self.assertEqual(owner_payload["status"], "SUCCEEDED")
        self.assertEqual(owner_payload["anchor_id"], anchor_id)
        self.assertEqual(owner_payload["asset_id"], replaced_asset_id)

        cross_owner_poll = client.get(f"/api/v1/screenshot-tasks/{replace_task_id}", headers=other_headers)
        self.assertEqual(cross_owner_poll.status_code, 404)
        self.assertEqual(cross_owner_poll.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        base_asset = store.get_screenshot_asset_for_owner(owner_id="owner-r5", asset_id=base_asset_id)
        replaced_asset = store.get_screenshot_asset_for_owner(owner_id="owner-r5", asset_id=replaced_asset_id)
        anchor = store.get_screenshot_anchor_for_owner(owner_id="owner-r5", anchor_id=anchor_id)
        self.assertIsNotNone(base_asset)
        self.assertIsNotNone(replaced_asset)
        self.assertIsNotNone(anchor)
        assert base_asset is not None
        assert replaced_asset is not None
        assert anchor is not None
        self.assertEqual(replaced_asset.previous_asset_id, base_asset_id)
        self.assertEqual(replaced_asset.version, base_asset.version + 1)
        self.assertEqual(anchor.active_asset_id, replaced_asset_id)

    def test_soft_delete_screenshot_asset_resolves_active_fallback_and_preserves_history(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-d1:editor"}

        project = store.create_project(owner_id="owner-d1", name="Owned")
        job = store.create_job(owner_id="owner-d1", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-d1",
            instruction_id="inst-d1",
            job_id=job.id,
            version=1,
            markdown="# screenshot source",
        )
        extracted = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-d1",
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
            },
        )
        self.assertEqual(extracted.status_code, 202)
        base_completed = store.complete_screenshot_task_success(
            task_id=extracted.json()["task_id"],
            image_uri="s3://bucket/screenshots/d1-base.png",
            width=1280,
            height=720,
        )
        anchor_id = base_completed.anchor_id
        base_asset_id = base_completed.asset_id
        assert anchor_id is not None
        assert base_asset_id is not None

        replace_mid = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=owner_headers,
            json={"instruction_version_id": "1", "timestamp_ms": 12500},
        )
        self.assertEqual(replace_mid.status_code, 202)
        mid_completed = store.complete_screenshot_task_success(
            task_id=replace_mid.json()["task_id"],
            image_uri="s3://bucket/screenshots/d1-mid.png",
            width=1280,
            height=720,
        )
        mid_asset_id = mid_completed.asset_id
        assert mid_asset_id is not None

        replace_top = client.post(
            f"/api/v1/anchors/{anchor_id}/replace",
            headers=owner_headers,
            json={"instruction_version_id": "1", "timestamp_ms": 13000},
        )
        self.assertEqual(replace_top.status_code, 202)
        top_completed = store.complete_screenshot_task_success(
            task_id=replace_top.json()["task_id"],
            image_uri="s3://bucket/screenshots/d1-top.png",
            width=1280,
            height=720,
        )
        top_asset_id = top_completed.asset_id
        assert top_asset_id is not None

        before_task_writes = store.screenshot_task_write_count

        delete_mid = client.delete(
            f"/api/v1/anchors/{anchor_id}/assets/{mid_asset_id}",
            headers=owner_headers,
        )
        self.assertEqual(delete_mid.status_code, 200)
        self.assertEqual(
            delete_mid.json(),
            {
                "anchor_id": anchor_id,
                "deleted_asset_id": mid_asset_id,
                "active_asset_id": top_asset_id,
            },
        )
        self.assertEqual(store.screenshot_task_write_count, before_task_writes)

        delete_top = client.delete(
            f"/api/v1/anchors/{anchor_id}/assets/{top_asset_id}",
            headers=owner_headers,
        )
        self.assertEqual(delete_top.status_code, 200)
        self.assertEqual(
            delete_top.json(),
            {
                "anchor_id": anchor_id,
                "deleted_asset_id": top_asset_id,
                "active_asset_id": base_asset_id,
            },
        )

        repeat_delete_top = client.delete(
            f"/api/v1/anchors/{anchor_id}/assets/{top_asset_id}",
            headers=owner_headers,
        )
        self.assertEqual(repeat_delete_top.status_code, 200)
        self.assertEqual(
            repeat_delete_top.json(),
            {
                "anchor_id": anchor_id,
                "deleted_asset_id": top_asset_id,
                "active_asset_id": base_asset_id,
            },
        )

        delete_base = client.delete(
            f"/api/v1/anchors/{anchor_id}/assets/{base_asset_id}",
            headers=owner_headers,
        )
        self.assertEqual(delete_base.status_code, 200)
        self.assertEqual(
            delete_base.json(),
            {
                "anchor_id": anchor_id,
                "deleted_asset_id": base_asset_id,
                "active_asset_id": None,
            },
        )

        repeat_delete_base = client.delete(
            f"/api/v1/anchors/{anchor_id}/assets/{base_asset_id}",
            headers=owner_headers,
        )
        self.assertEqual(repeat_delete_base.status_code, 200)
        self.assertEqual(
            repeat_delete_base.json(),
            {
                "anchor_id": anchor_id,
                "deleted_asset_id": base_asset_id,
                "active_asset_id": None,
            },
        )

        anchor_after = store.get_screenshot_anchor_for_owner(owner_id="owner-d1", anchor_id=anchor_id)
        self.assertIsNotNone(anchor_after)
        assert anchor_after is not None
        self.assertIsNone(anchor_after.active_asset_id)

        for asset_id in (base_asset_id, mid_asset_id, top_asset_id):
            deleted_asset = store.get_screenshot_asset_for_owner(owner_id="owner-d1", asset_id=asset_id)
            self.assertIsNotNone(deleted_asset)
            assert deleted_asset is not None
            self.assertTrue(deleted_asset.is_deleted)

    def test_soft_delete_screenshot_asset_no_leak_for_cross_owner_or_missing_asset(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-d2:editor"}
        other_headers = {"Authorization": "Bearer test:owner-d2-other:editor"}

        project = store.create_project(owner_id="owner-d2", name="Owned")
        job = store.create_job(owner_id="owner-d2", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-d2",
            instruction_id="inst-d2",
            job_id=job.id,
            version=1,
            markdown="# screenshot source",
        )
        extracted = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-d2",
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
            },
        )
        self.assertEqual(extracted.status_code, 202)
        completed = store.complete_screenshot_task_success(
            task_id=extracted.json()["task_id"],
            image_uri="s3://bucket/screenshots/d2-base.png",
            width=1000,
            height=600,
        )
        anchor_id = completed.anchor_id
        asset_id = completed.asset_id
        assert anchor_id is not None
        assert asset_id is not None
        before_task_writes = store.screenshot_task_write_count

        cross_owner = client.delete(
            f"/api/v1/anchors/{anchor_id}/assets/{asset_id}",
            headers=other_headers,
        )
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing_anchor = client.delete(
            f"/api/v1/anchors/anchor-missing-d2/assets/{asset_id}",
            headers=owner_headers,
        )
        self.assertEqual(missing_anchor.status_code, 404)
        self.assertEqual(missing_anchor.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing_asset = client.delete(
            f"/api/v1/anchors/{anchor_id}/assets/asset-missing-d2",
            headers=owner_headers,
        )
        self.assertEqual(missing_asset.status_code, 404)
        self.assertEqual(missing_asset.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(store.screenshot_task_write_count, before_task_writes)

        existing_asset = store.get_screenshot_asset_for_owner(owner_id="owner-d2", asset_id=asset_id)
        self.assertIsNotNone(existing_asset)
        assert existing_asset is not None
        self.assertFalse(existing_asset.is_deleted)

    def test_get_screenshot_task_polling_returns_owned_task_and_enforces_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-s5:editor"}
        other_headers = {"Authorization": "Bearer test:owner-s5-other:editor"}

        project = store.create_project(owner_id="owner-s5", name="Owned")
        job = store.create_job(owner_id="owner-s5", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-s5",
            instruction_id="inst-s5",
            job_id=job.id,
            version=1,
            markdown="# screenshot source",
        )
        created = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-s5",
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
                "offset_ms": 250,
                "strategy": "nearest_keyframe",
                "format": "jpg",
            },
        )
        self.assertEqual(created.status_code, 202)
        task_id = created.json()["task_id"]

        completed = store.complete_screenshot_task_success(
            task_id=task_id,
            image_uri="s3://bucket/screenshots/s5.jpg",
            width=1280,
            height=720,
        )
        self.assertEqual(completed.status, ScreenshotTaskStatus.SUCCEEDED)
        before_task_writes = store.screenshot_task_write_count
        before_job_writes = store.job_write_count

        owned = client.get(f"/api/v1/screenshot-tasks/{task_id}", headers=owner_headers)
        self.assertEqual(owned.status_code, 200)
        owned_payload = owned.json()
        self.assertEqual(owned_payload["task_id"], task_id)
        self.assertEqual(owned_payload["status"], "SUCCEEDED")
        self.assertEqual(owned_payload["operation"], "extract")
        self.assertEqual(owned_payload["anchor_id"], completed.anchor_id)
        self.assertEqual(owned_payload["asset_id"], completed.asset_id)
        self.assertEqual(store.screenshot_task_write_count, before_task_writes)
        self.assertEqual(store.job_write_count, before_job_writes)

        asset_record = store.get_screenshot_asset_for_owner(owner_id="owner-s5", asset_id=completed.asset_id)
        self.assertIsNotNone(asset_record)
        assert asset_record is not None
        self.assertEqual(asset_record.image_uri, "s3://bucket/screenshots/s5.jpg")
        self.assertEqual(asset_record.width, 1280)
        self.assertEqual(asset_record.height, 720)
        self.assertEqual(asset_record.extraction_parameters["timestamp_ms"], 12000)
        self.assertEqual(asset_record.extraction_parameters["offset_ms"], 250)
        self.assertEqual(asset_record.extraction_parameters["strategy"], "nearest_keyframe")
        self.assertEqual(asset_record.extraction_parameters["format"], "jpg")
        self.assertIsNone(
            store.get_screenshot_asset_for_owner(owner_id="owner-s5-other", asset_id=completed.asset_id),
        )

        cross_owner = client.get(f"/api/v1/screenshot-tasks/{task_id}", headers=other_headers)
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing = client.get("/api/v1/screenshot-tasks/task-missing-s5", headers=other_headers)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

    def test_request_screenshot_extract_invalid_instruction_version_id_returns_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-s6:editor"}

        project = store.create_project(owner_id="owner-s6", name="Owned")
        job = store.create_job(owner_id="owner-s6", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-s6",
            instruction_id="inst-s6",
            job_id=job.id,
            version=1,
            markdown="# screenshot source",
        )
        before_task_writes = store.screenshot_task_write_count

        invalid_version = client.post(
            f"/api/v1/jobs/{job.id}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-s6",
                "instruction_version_id": "ver-1",
                "timestamp_ms": 12000,
            },
        )

        self.assertEqual(invalid_version.status_code, 404)
        self.assertEqual(invalid_version.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(store.screenshot_task_write_count, before_task_writes)

    def test_create_custom_upload_ticket_returns_201_and_enforces_no_leak_404(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-u1:editor"}
        other_headers = {"Authorization": "Bearer test:owner-u1-other:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        payload = {
            "filename": "custom.png",
            "mime_type": "image/png",
            "size_bytes": 2048,
            "checksum_sha256": _checksum("u1"),
        }

        created = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads",
            headers=owner_headers,
            json=payload,
        )
        self.assertEqual(created.status_code, 201)
        created_payload = created.json()
        self.assertIn("upload_id", created_payload)
        self.assertIn("upload_url", created_payload)
        self.assertIn("expires_at", created_payload)
        self.assertEqual(created_payload["max_size_bytes"], 10 * 1024 * 1024)
        self.assertEqual(created_payload["allowed_mime_types"], ["image/png", "image/jpeg", "image/webp"])
        upload_id = created_payload["upload_id"]
        parsed_upload_url = urlparse(created_payload["upload_url"])
        self.assertEqual(parsed_upload_url.scheme, "https")
        self.assertEqual(parsed_upload_url.netloc, "uploads.howera.local")
        self.assertEqual(parsed_upload_url.path, f"/{upload_id}")
        signed_query = parse_qs(parsed_upload_url.query)
        self.assertIn("expires", signed_query)
        self.assertIn("sig", signed_query)
        self.assertEqual(len(signed_query["sig"][0]), 64)
        self.assertIn(upload_id, store.custom_uploads_by_id)
        self.assertEqual(store.custom_uploads_by_id[upload_id].owner_id, "owner-u1")
        self.assertEqual(store.custom_uploads_by_id[upload_id].job_id, created_job["id"])

        cross_owner = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads",
            headers=other_headers,
            json=payload,
        )
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing = client.post(
            "/api/v1/jobs/job-missing/screenshots/uploads",
            headers=owner_headers,
            json=payload,
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

    def test_confirm_custom_upload_persists_asset_metadata_and_replays_idempotently(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-u2:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        created_ticket = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads",
            headers=owner_headers,
            json={
                "filename": "custom.webp",
                "mime_type": "image/webp",
                "size_bytes": 4096,
                "checksum_sha256": _checksum("u2"),
            },
        )
        self.assertEqual(created_ticket.status_code, 201)
        upload_id = created_ticket.json()["upload_id"]
        before_asset_count = len(store.screenshot_assets_by_id)

        confirm_payload = {
            "mime_type": "image/webp",
            "size_bytes": 4096,
            "checksum_sha256": _checksum("u2"),
            "width": 900,
            "height": 600,
        }
        confirmed = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads/{upload_id}/confirm",
            headers=owner_headers,
            json=confirm_payload,
        )
        self.assertEqual(confirmed.status_code, 200)
        confirmed_asset = confirmed.json()["asset"]
        self.assertEqual(confirmed_asset["kind"], "UPLOADED")
        self.assertEqual(confirmed_asset["mime_type"], "image/webp")
        self.assertEqual(confirmed_asset["checksum_sha256"], _checksum("u2"))
        self.assertEqual(confirmed_asset["upload_id"], upload_id)
        self.assertEqual(confirmed_asset["width"], 900)
        self.assertEqual(confirmed_asset["height"], 600)
        self.assertNotIn("custom.webp", confirmed_asset["image_uri"])
        self.assertFalse(confirmed_asset["is_deleted"])
        self.assertNotIn("extraction_key", confirmed_asset)
        self.assertNotIn("ops_hash", confirmed_asset)
        self.assertNotIn("rendered_from_asset_id", confirmed_asset)
        self.assertEqual(len(store.screenshot_assets_by_id), before_asset_count + 1)

        upload_record = store.custom_uploads_by_id[upload_id]
        self.assertTrue(upload_record.confirmed)
        self.assertEqual(upload_record.confirmed_mime_type, "image/webp")
        self.assertEqual(upload_record.confirmed_size_bytes, 4096)
        self.assertEqual(upload_record.confirmed_checksum_sha256, _checksum("u2"))
        self.assertEqual(upload_record.confirmed_width, 900)
        self.assertEqual(upload_record.confirmed_height, 600)

        replay = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads/{upload_id}/confirm",
            headers=owner_headers,
            json=confirm_payload,
        )
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["asset"]["id"], confirmed_asset["id"])
        self.assertEqual(len(store.screenshot_assets_by_id), before_asset_count + 1)

    def test_confirm_custom_upload_rejects_svg_and_invalid_payload_without_side_effects(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-u3:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        created_ticket = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads",
            headers=owner_headers,
            json={
                "filename": "custom.png",
                "mime_type": "image/png",
                "size_bytes": 1024,
                "checksum_sha256": _checksum("u3"),
            },
        )
        self.assertEqual(created_ticket.status_code, 201)
        upload_id = created_ticket.json()["upload_id"]
        before_asset_count = len(store.screenshot_assets_by_id)

        svg = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads/{upload_id}/confirm",
            headers=owner_headers,
            json={
                "mime_type": "image/svg+xml",
                "size_bytes": 1024,
                "checksum_sha256": _checksum("u3"),
                "width": 800,
                "height": 600,
            },
        )
        self.assertEqual(svg.status_code, 404)
        self.assertEqual(svg.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(len(store.screenshot_assets_by_id), before_asset_count)
        self.assertFalse(store.custom_uploads_by_id[upload_id].confirmed)

        mismatch = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads/{upload_id}/confirm",
            headers=owner_headers,
            json={
                "mime_type": "image/png",
                "size_bytes": 2048,
                "checksum_sha256": _checksum("u3"),
                "width": 800,
                "height": 600,
            },
        )
        self.assertEqual(mismatch.status_code, 404)
        self.assertEqual(mismatch.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(len(store.screenshot_assets_by_id), before_asset_count)
        self.assertFalse(store.custom_uploads_by_id[upload_id].confirmed)

    def test_confirm_custom_upload_rejects_expired_unconfirmed_ticket(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-u3-expired:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        created_ticket = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads",
            headers=owner_headers,
            json={
                "filename": "custom.png",
                "mime_type": "image/png",
                "size_bytes": 1024,
                "checksum_sha256": _checksum("u3-expired"),
            },
        )
        self.assertEqual(created_ticket.status_code, 201)
        upload_id = created_ticket.json()["upload_id"]
        store.custom_uploads_by_id[upload_id].expires_at = datetime.now(UTC) - timedelta(seconds=1)
        before_asset_count = len(store.screenshot_assets_by_id)

        expired = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads/{upload_id}/confirm",
            headers=owner_headers,
            json={
                "mime_type": "image/png",
                "size_bytes": 1024,
                "checksum_sha256": _checksum("u3-expired"),
                "width": 800,
                "height": 600,
            },
        )
        self.assertEqual(expired.status_code, 404)
        self.assertEqual(expired.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(len(store.screenshot_assets_by_id), before_asset_count)
        self.assertFalse(store.custom_uploads_by_id[upload_id].confirmed)

    def test_confirm_custom_upload_rejects_tampered_upload_url_signature(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-u3-signature:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        created_ticket = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads",
            headers=owner_headers,
            json={
                "filename": "custom.png",
                "mime_type": "image/png",
                "size_bytes": 1024,
                "checksum_sha256": _checksum("u3-signature"),
            },
        )
        self.assertEqual(created_ticket.status_code, 201)
        upload_id = created_ticket.json()["upload_id"]
        before_asset_count = len(store.screenshot_assets_by_id)
        upload_record = store.custom_uploads_by_id[upload_id]
        upload_record.upload_url = upload_record.upload_url.replace("sig=", "sig=deadbeef")

        tampered = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads/{upload_id}/confirm",
            headers=owner_headers,
            json={
                "mime_type": "image/png",
                "size_bytes": 1024,
                "checksum_sha256": _checksum("u3-signature"),
                "width": 800,
                "height": 600,
            },
        )
        self.assertEqual(tampered.status_code, 404)
        self.assertEqual(tampered.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(len(store.screenshot_assets_by_id), before_asset_count)
        self.assertFalse(store.custom_uploads_by_id[upload_id].confirmed)

    def test_attach_uploaded_asset_updates_version_chain_and_replays_by_idempotency_key(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-u4:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.create_instruction_version(
            owner_id="owner-u4",
            instruction_id="inst-u4",
            job_id=created_job["id"],
            version=1,
            markdown="# screenshot source",
        )
        store.create_instruction_version(
            owner_id="owner-u4",
            instruction_id="inst-u4",
            job_id=created_job["id"],
            version=2,
            markdown="# screenshot source updated",
        )
        extracted = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-u4",
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
            },
        )
        self.assertEqual(extracted.status_code, 202)
        completed_extract = store.complete_screenshot_task_success(
            task_id=extracted.json()["task_id"],
            image_uri="s3://bucket/screenshots/u4-base.png",
            width=1200,
            height=700,
        )
        anchor_id = completed_extract.anchor_id
        base_asset_id = completed_extract.asset_id
        assert anchor_id is not None
        assert base_asset_id is not None

        ticket = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads",
            headers=owner_headers,
            json={
                "filename": "custom.png",
                "mime_type": "image/png",
                "size_bytes": 3072,
                "checksum_sha256": _checksum("u4"),
            },
        )
        self.assertEqual(ticket.status_code, 201)
        upload_id = ticket.json()["upload_id"]
        confirmed = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads/{upload_id}/confirm",
            headers=owner_headers,
            json={
                "mime_type": "image/png",
                "size_bytes": 3072,
                "checksum_sha256": _checksum("u4"),
                "width": 640,
                "height": 360,
            },
        )
        self.assertEqual(confirmed.status_code, 200)

        before_anchor_asset_count = len(store.screenshot_asset_ids_by_anchor.get(anchor_id, []))
        attached = client.post(
            f"/api/v1/anchors/{anchor_id}/attach-upload",
            headers=owner_headers,
            json={
                "upload_id": upload_id,
                "instruction_version_id": "1",
                "idempotency_key": "attach-u4-1",
            },
        )
        self.assertEqual(attached.status_code, 200)
        attached_payload = attached.json()
        attached_asset_id = attached_payload["active_asset_id"]
        self.assertNotEqual(attached_asset_id, base_asset_id)
        self.assertEqual(attached_payload["id"], anchor_id)
        self.assertEqual(attached_payload["instruction_version_id"], "1")
        self.assertNotIn("assets", attached_payload)
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_anchor_asset_count + 1)

        attached_asset = store.get_screenshot_asset_for_owner(owner_id="owner-u4", asset_id=attached_asset_id)
        self.assertIsNotNone(attached_asset)
        assert attached_asset is not None
        self.assertEqual(attached_asset.kind, "UPLOADED")
        self.assertEqual(attached_asset.previous_asset_id, base_asset_id)
        self.assertEqual(attached_asset.upload_id, upload_id)

        replay = client.post(
            f"/api/v1/anchors/{anchor_id}/attach-upload",
            headers=owner_headers,
            json={
                "upload_id": upload_id,
                "instruction_version_id": "1",
                "idempotency_key": "attach-u4-1",
            },
        )
        self.assertEqual(replay.status_code, 200)
        self.assertEqual(replay.json()["active_asset_id"], attached_asset_id)
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_anchor_asset_count + 1)

        second_attach = client.post(
            f"/api/v1/anchors/{anchor_id}/attach-upload",
            headers=owner_headers,
            json={
                "upload_id": upload_id,
                "instruction_version_id": "2",
                "idempotency_key": "attach-u4-2",
            },
        )
        self.assertEqual(second_attach.status_code, 200)
        second_payload = second_attach.json()
        self.assertEqual(second_payload["instruction_version_id"], "2")
        self.assertNotEqual(second_payload["active_asset_id"], attached_asset_id)
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_anchor_asset_count + 2)

        replay_after_anchor_changes = client.post(
            f"/api/v1/anchors/{anchor_id}/attach-upload",
            headers=owner_headers,
            json={
                "upload_id": upload_id,
                "instruction_version_id": "1",
                "idempotency_key": "attach-u4-1",
            },
        )
        self.assertEqual(replay_after_anchor_changes.status_code, 200)
        self.assertEqual(replay_after_anchor_changes.json(), attached_payload)
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_anchor_asset_count + 2)

    def test_attach_uploaded_asset_enforces_no_leak_404_for_cross_owner_and_missing_context(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-u5:editor"}
        other_headers = {"Authorization": "Bearer test:owner-u5-other:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.create_instruction_version(
            owner_id="owner-u5",
            instruction_id="inst-u5",
            job_id=created_job["id"],
            version=1,
            markdown="# screenshot source",
        )
        extracted = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/extract",
            headers=owner_headers,
            json={
                "instruction_id": "inst-u5",
                "instruction_version_id": "1",
                "timestamp_ms": 12000,
            },
        )
        self.assertEqual(extracted.status_code, 202)
        completed_extract = store.complete_screenshot_task_success(
            task_id=extracted.json()["task_id"],
            image_uri="s3://bucket/screenshots/u5-base.png",
            width=1200,
            height=700,
        )
        anchor_id = completed_extract.anchor_id
        base_asset_id = completed_extract.asset_id
        assert anchor_id is not None
        assert base_asset_id is not None

        ticket = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads",
            headers=owner_headers,
            json={
                "filename": "custom.png",
                "mime_type": "image/png",
                "size_bytes": 2048,
                "checksum_sha256": _checksum("u5"),
            },
        )
        self.assertEqual(ticket.status_code, 201)
        upload_id = ticket.json()["upload_id"]
        confirmed = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/uploads/{upload_id}/confirm",
            headers=owner_headers,
            json={
                "mime_type": "image/png",
                "size_bytes": 2048,
                "checksum_sha256": _checksum("u5"),
                "width": 640,
                "height": 360,
            },
        )
        self.assertEqual(confirmed.status_code, 200)
        before_anchor_asset_count = len(store.screenshot_asset_ids_by_anchor.get(anchor_id, []))

        cross_owner = client.post(
            f"/api/v1/anchors/{anchor_id}/attach-upload",
            headers=other_headers,
            json={"upload_id": upload_id, "instruction_version_id": "1"},
        )
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing_anchor = client.post(
            "/api/v1/anchors/anchor-missing-u5/attach-upload",
            headers=owner_headers,
            json={"upload_id": upload_id, "instruction_version_id": "1"},
        )
        self.assertEqual(missing_anchor.status_code, 404)
        self.assertEqual(missing_anchor.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing_upload = client.post(
            f"/api/v1/anchors/{anchor_id}/attach-upload",
            headers=owner_headers,
            json={"upload_id": "upload-missing-u5", "instruction_version_id": "1"},
        )
        self.assertEqual(missing_upload.status_code, 404)
        self.assertEqual(missing_upload.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        invalid_version = client.post(
            f"/api/v1/anchors/{anchor_id}/attach-upload",
            headers=owner_headers,
            json={"upload_id": upload_id, "instruction_version_id": "2"},
        )
        self.assertEqual(invalid_version.status_code, 404)
        self.assertEqual(invalid_version.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_anchor_asset_count)
        anchor_after = store.get_screenshot_anchor_for_owner(owner_id="owner-u5", anchor_id=anchor_id)
        self.assertIsNotNone(anchor_after)
        assert anchor_after is not None
        self.assertEqual(anchor_after.active_asset_id, base_asset_id)

    def test_annotate_screenshot_creates_annotated_asset_and_updates_active_asset(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-a1:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.create_instruction_version(
            owner_id="owner-a1",
            instruction_id="inst-a1",
            job_id=created_job["id"],
            version=1,
            markdown="# screenshot source",
        )
        extracted = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/extract",
            headers=owner_headers,
            json={"instruction_id": "inst-a1", "instruction_version_id": "1", "timestamp_ms": 12000},
        )
        self.assertEqual(extracted.status_code, 202)
        completed_extract = store.complete_screenshot_task_success(
            task_id=extracted.json()["task_id"],
            image_uri="s3://bucket/screenshots/a1-base.png",
            width=1200,
            height=700,
        )
        anchor_id = completed_extract.anchor_id
        base_asset_id = completed_extract.asset_id
        assert anchor_id is not None
        assert base_asset_id is not None
        before_asset_count = len(store.screenshot_assets_by_id)

        annotated = client.post(
            f"/api/v1/anchors/{anchor_id}/annotations",
            headers=owner_headers,
            json={
                "base_asset_id": base_asset_id,
                "operations": [
                    {
                        "op_type": "arrow",
                        "geometry": {"x1": 10, "y1": 20, "x2": 100, "y2": 200},
                        "style": {"color": "#ff0000", "width": 4},
                    },
                    {
                        "op_type": "blur",
                        "geometry": {"x": 300, "y": 160, "width": 240, "height": 120},
                        "style": {"radius": 8},
                    },
                ],
            },
        )
        self.assertEqual(annotated.status_code, 200)
        payload = annotated.json()
        self.assertEqual(payload["anchor_id"], anchor_id)
        self.assertEqual(payload["base_asset_id"], base_asset_id)
        self.assertEqual(payload["active_asset_id"], payload["rendered_asset_id"])
        self.assertRegex(payload["ops_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(len(store.screenshot_assets_by_id), before_asset_count + 1)

        rendered_asset = store.get_screenshot_asset_for_owner(owner_id="owner-a1", asset_id=payload["rendered_asset_id"])
        self.assertIsNotNone(rendered_asset)
        assert rendered_asset is not None
        self.assertEqual(rendered_asset.kind, "ANNOTATED")
        self.assertEqual(rendered_asset.rendered_from_asset_id, base_asset_id)
        self.assertEqual(rendered_asset.ops_hash, payload["ops_hash"])
        self.assertEqual(rendered_asset.previous_asset_id, base_asset_id)

        anchor_after = store.get_screenshot_anchor_for_owner(owner_id="owner-a1", anchor_id=anchor_id)
        self.assertIsNotNone(anchor_after)
        assert anchor_after is not None
        self.assertEqual(anchor_after.active_asset_id, payload["rendered_asset_id"])

    def test_annotate_screenshot_replays_identical_normalized_operations_without_duplicate_asset(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-a2:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.create_instruction_version(
            owner_id="owner-a2",
            instruction_id="inst-a2",
            job_id=created_job["id"],
            version=1,
            markdown="# screenshot source",
        )
        extracted = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/extract",
            headers=owner_headers,
            json={"instruction_id": "inst-a2", "instruction_version_id": "1", "timestamp_ms": 12000},
        )
        self.assertEqual(extracted.status_code, 202)
        completed_extract = store.complete_screenshot_task_success(
            task_id=extracted.json()["task_id"],
            image_uri="s3://bucket/screenshots/a2-base.png",
            width=1200,
            height=700,
        )
        anchor_id = completed_extract.anchor_id
        base_asset_id = completed_extract.asset_id
        assert anchor_id is not None
        assert base_asset_id is not None
        before_asset_count = len(store.screenshot_assets_by_id)

        first = client.post(
            f"/api/v1/anchors/{anchor_id}/annotations",
            headers=owner_headers,
            json={
                "base_asset_id": base_asset_id,
                "operations": [
                    {
                        "op_type": "marker",
                        "geometry": {"points": [{"x": 10, "y": 10}, {"x": 30, "y": 30}]},
                        "style": {"opacity": 0.4, "color": "#00ff88"},
                    },
                    {
                        "op_type": "arrow",
                        "geometry": {"x1": 20, "y1": 30, "x2": 120, "y2": 130},
                        "style": {"width": 3, "color": "#111111"},
                    },
                ],
            },
        )
        self.assertEqual(first.status_code, 200)
        first_payload = first.json()
        self.assertEqual(len(store.screenshot_assets_by_id), before_asset_count + 1)

        replay = client.post(
            f"/api/v1/anchors/{anchor_id}/annotations",
            headers=owner_headers,
            json={
                "base_asset_id": base_asset_id,
                "operations": [
                    {
                        "op_type": "arrow",
                        "geometry": {"y2": 130, "x2": 120, "y1": 30, "x1": 20},
                        "style": {"color": "#111111", "width": 3},
                    },
                    {
                        "op_type": "marker",
                        "geometry": {"points": [{"x": 10, "y": 10}, {"x": 30, "y": 30}]},
                        "style": {"color": "#00ff88", "opacity": 0.4},
                    },
                ],
            },
        )
        self.assertEqual(replay.status_code, 200)
        replay_payload = replay.json()
        self.assertEqual(replay_payload["ops_hash"], first_payload["ops_hash"])
        self.assertEqual(replay_payload["rendered_asset_id"], first_payload["rendered_asset_id"])
        self.assertEqual(replay_payload["active_asset_id"], first_payload["active_asset_id"])
        self.assertEqual(len(store.screenshot_assets_by_id), before_asset_count + 1)

    def test_annotate_screenshot_invalid_payload_returns_400_without_mutation(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-a3:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.create_instruction_version(
            owner_id="owner-a3",
            instruction_id="inst-a3",
            job_id=created_job["id"],
            version=1,
            markdown="# screenshot source",
        )
        extracted = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/extract",
            headers=owner_headers,
            json={"instruction_id": "inst-a3", "instruction_version_id": "1", "timestamp_ms": 12000},
        )
        self.assertEqual(extracted.status_code, 202)
        completed_extract = store.complete_screenshot_task_success(
            task_id=extracted.json()["task_id"],
            image_uri="s3://bucket/screenshots/a3-base.png",
            width=1200,
            height=700,
        )
        anchor_id = completed_extract.anchor_id
        base_asset_id = completed_extract.asset_id
        assert anchor_id is not None
        assert base_asset_id is not None

        before_asset_count = len(store.screenshot_assets_by_id)
        before_anchor = store.get_screenshot_anchor_for_owner(owner_id="owner-a3", anchor_id=anchor_id)
        assert before_anchor is not None
        before_active_asset_id = before_anchor.active_asset_id

        invalid = client.post(
            f"/api/v1/anchors/{anchor_id}/annotations",
            headers=owner_headers,
            json={"base_asset_id": base_asset_id, "operations": []},
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["code"], "VALIDATION_ERROR")
        self.assertEqual(invalid.json()["message"], "Invalid annotation payload")
        self.assertEqual(len(store.screenshot_assets_by_id), before_asset_count)
        anchor_after = store.get_screenshot_anchor_for_owner(owner_id="owner-a3", anchor_id=anchor_id)
        self.assertIsNotNone(anchor_after)
        assert anchor_after is not None
        self.assertEqual(anchor_after.active_asset_id, before_active_asset_id)

    def test_annotate_screenshot_enforces_no_leak_404_for_cross_owner_missing_and_context_mismatch(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        owner_headers = {"Authorization": "Bearer test:owner-a4:editor"}
        other_headers = {"Authorization": "Bearer test:owner-a4-other:editor"}

        project = client.post("/api/v1/projects", headers=owner_headers, json={"name": "Owned"}).json()
        created_job = client.post(f"/api/v1/projects/{project['id']}/jobs", headers=owner_headers).json()
        store.create_instruction_version(
            owner_id="owner-a4",
            instruction_id="inst-a4",
            job_id=created_job["id"],
            version=1,
            markdown="# screenshot source",
        )

        extracted_one = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/extract",
            headers=owner_headers,
            json={"instruction_id": "inst-a4", "instruction_version_id": "1", "timestamp_ms": 12000},
        )
        self.assertEqual(extracted_one.status_code, 202)
        completed_one = store.complete_screenshot_task_success(
            task_id=extracted_one.json()["task_id"],
            image_uri="s3://bucket/screenshots/a4-base-1.png",
            width=1200,
            height=700,
        )
        anchor_id = completed_one.anchor_id
        base_asset_id = completed_one.asset_id
        assert anchor_id is not None
        assert base_asset_id is not None

        extracted_two = client.post(
            f"/api/v1/jobs/{created_job['id']}/screenshots/extract",
            headers=owner_headers,
            json={"instruction_id": "inst-a4", "instruction_version_id": "1", "timestamp_ms": 13000},
        )
        self.assertEqual(extracted_two.status_code, 202)
        completed_two = store.complete_screenshot_task_success(
            task_id=extracted_two.json()["task_id"],
            image_uri="s3://bucket/screenshots/a4-base-2.png",
            width=1200,
            height=700,
        )
        other_anchor_asset_id = completed_two.asset_id
        assert other_anchor_asset_id is not None
        before_asset_count = len(store.screenshot_assets_by_id)

        cross_owner = client.post(
            f"/api/v1/anchors/{anchor_id}/annotations",
            headers=other_headers,
            json={
                "base_asset_id": base_asset_id,
                "operations": [{"op_type": "blur", "geometry": {"x": 1}, "style": {"radius": 3}}],
            },
        )
        self.assertEqual(cross_owner.status_code, 404)
        self.assertEqual(cross_owner.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        missing_anchor = client.post(
            "/api/v1/anchors/anchor-missing-a4/annotations",
            headers=owner_headers,
            json={
                "base_asset_id": base_asset_id,
                "operations": [{"op_type": "blur", "geometry": {"x": 1}, "style": {"radius": 3}}],
            },
        )
        self.assertEqual(missing_anchor.status_code, 404)
        self.assertEqual(missing_anchor.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})

        context_mismatch = client.post(
            f"/api/v1/anchors/{anchor_id}/annotations",
            headers=owner_headers,
            json={
                "base_asset_id": other_anchor_asset_id,
                "operations": [{"op_type": "blur", "geometry": {"x": 1}, "style": {"radius": 3}}],
            },
        )
        self.assertEqual(context_mismatch.status_code, 404)
        self.assertEqual(context_mismatch.json(), {"code": "RESOURCE_NOT_FOUND", "message": "Resource not found"})
        self.assertEqual(len(store.screenshot_assets_by_id), before_asset_count)


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

    def test_build_screenshot_canonical_key_is_deterministic(self) -> None:
        canonical_key = InMemoryStore.build_screenshot_extraction_canonical_key(
            job_id="job-1",
            instruction_version_id="1",
            timestamp_ms=12000,
            offset_ms=250,
            strategy=ScreenshotStrategy.NEAREST_KEYFRAME,
            image_format=ScreenshotFormat.JPG,
        )

        self.assertEqual(
            canonical_key,
            "job-1|1|12000|250|nearest_keyframe|jpg",
        )

    def test_build_annotation_ops_hash_is_deterministic_across_semantic_payload_orderings(self) -> None:
        store = InMemoryStore()
        operations_a = [
            {
                "op_type": "arrow",
                "geometry": {"x1": 10, "y1": 20, "x2": 100, "y2": 200},
                "style": {"color": "#ff0000", "width": 2},
            },
            {
                "op_type": "marker",
                "geometry": {"points": [{"x": 5, "y": 5}, {"x": 25, "y": 30}]},
                "style": {"opacity": 0.5, "color": "#00ff00"},
            },
        ]
        operations_b = [
            {
                "op_type": "marker",
                "geometry": {"points": [{"x": 5, "y": 5}, {"x": 25, "y": 30}]},
                "style": {"color": "#00ff00", "opacity": 0.5},
            },
            {
                "op_type": "arrow",
                "geometry": {"y2": 200, "x2": 100, "y1": 20, "x1": 10},
                "style": {"width": 2, "color": "#ff0000"},
            },
        ]

        normalized_a = store._normalize_annotation_operations(operations=operations_a)
        normalized_b = store._normalize_annotation_operations(operations=operations_b)
        self.assertEqual(normalized_a, normalized_b)

        hash_a = store.build_annotation_ops_hash(
            anchor_id="anchor-1",
            base_asset_id="asset-1",
            normalized_operations=normalized_a,
        )
        hash_b = store.build_annotation_ops_hash(
            anchor_id="anchor-1",
            base_asset_id="asset-1",
            normalized_operations=normalized_b,
        )
        self.assertEqual(hash_a, hash_b)

    def test_apply_screenshot_annotations_render_failure_preserves_state(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="owner-a-unit-1", name="Project")
        job = store.create_job(owner_id="owner-a-unit-1", project_id=project.id)

        extracted_task, _ = store.create_screenshot_extraction_task(
            owner_id="owner-a-unit-1",
            job_id=job.id,
            payload=ScreenshotExtractionRequest(
                instruction_id="inst-a-unit-1",
                instruction_version_id="1",
                timestamp_ms=12000,
            ),
        )
        completed_extract = store.complete_screenshot_task_success(
            task_id=extracted_task.id,
            image_uri="s3://bucket/screenshots/a-unit-1-base.png",
            width=1000,
            height=500,
        )
        anchor_id = completed_extract.anchor_id
        base_asset_id = completed_extract.asset_id
        assert anchor_id is not None
        assert base_asset_id is not None

        anchor_before = store.get_screenshot_anchor_for_owner(owner_id="owner-a-unit-1", anchor_id=anchor_id)
        assert anchor_before is not None
        before_active_asset_id = anchor_before.active_asset_id
        before_latest_version = anchor_before.latest_asset_version
        before_asset_count = len(store.screenshot_assets_by_id)

        store.annotation_render_failure_message = "forced render failure"
        with self.assertRaises(ValueError):
            store.apply_screenshot_annotations(
                owner_id="owner-a-unit-1",
                anchor_id=anchor_id,
                base_asset_id=base_asset_id,
                operations=[{"op_type": "blur", "geometry": {"x": 10}, "style": {"radius": 4}}],
                idempotency_key=None,
            )

        anchor_after = store.get_screenshot_anchor_for_owner(owner_id="owner-a-unit-1", anchor_id=anchor_id)
        self.assertIsNotNone(anchor_after)
        assert anchor_after is not None
        self.assertEqual(anchor_after.active_asset_id, before_active_asset_id)
        self.assertEqual(anchor_after.latest_asset_version, before_latest_version)
        self.assertEqual(len(store.screenshot_assets_by_id), before_asset_count)

    def test_create_screenshot_extraction_task_applies_idempotency_and_canonical_replay(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="owner-s-unit-1", name="Project")
        job = store.create_job(owner_id="owner-s-unit-1", project_id=project.id)
        payload = ScreenshotExtractionRequest(
            instruction_id="inst-s-unit-1",
            instruction_version_id="1",
            timestamp_ms=12000,
            offset_ms=0,
            strategy=ScreenshotStrategy.PRECISE,
            format=ScreenshotFormat.PNG,
            idempotency_key="shot-unit-1",
        )

        first_task, replayed = store.create_screenshot_extraction_task(
            owner_id="owner-s-unit-1",
            job_id=job.id,
            payload=payload,
        )
        self.assertFalse(replayed)
        writes_after_first = store.screenshot_task_write_count

        replay_by_idempotency, replayed_again = store.create_screenshot_extraction_task(
            owner_id="owner-s-unit-1",
            job_id=job.id,
            payload=payload,
        )
        self.assertTrue(replayed_again)
        self.assertEqual(replay_by_idempotency.id, first_task.id)
        self.assertEqual(store.screenshot_task_write_count, writes_after_first)

        replay_by_canonical, replayed_canonical = store.create_screenshot_extraction_task(
            owner_id="owner-s-unit-1",
            job_id=job.id,
            payload=payload.model_copy(update={"idempotency_key": "shot-unit-2"}),
        )
        self.assertTrue(replayed_canonical)
        self.assertEqual(replay_by_canonical.id, first_task.id)
        self.assertEqual(store.screenshot_task_write_count, writes_after_first)

        with self.assertRaises(ValueError):
            store.create_screenshot_extraction_task(
                owner_id="owner-s-unit-1",
                job_id=job.id,
                payload=payload.model_copy(update={"timestamp_ms": 12001}),
            )
        self.assertEqual(store.screenshot_task_write_count, writes_after_first)

        canonical_replay_with_new_key, canonical_replayed = store.create_screenshot_extraction_task(
            owner_id="owner-s-unit-1",
            job_id=job.id,
            payload=payload.model_copy(update={"anchor_id": "anchor-variant", "idempotency_key": "shot-unit-3"}),
        )
        self.assertTrue(canonical_replayed)
        self.assertEqual(canonical_replay_with_new_key.id, first_task.id)
        self.assertEqual(store.screenshot_task_write_count, writes_after_first)

        canonical_replay_repeat_key, canonical_replayed_repeat = store.create_screenshot_extraction_task(
            owner_id="owner-s-unit-1",
            job_id=job.id,
            payload=payload.model_copy(update={"anchor_id": "anchor-variant", "idempotency_key": "shot-unit-3"}),
        )
        self.assertTrue(canonical_replayed_repeat)
        self.assertEqual(canonical_replay_repeat_key.id, first_task.id)
        self.assertEqual(store.screenshot_task_write_count, writes_after_first)

    def test_create_screenshot_replace_task_applies_idempotency_and_canonical_noop(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="owner-r-unit-1", name="Project")
        job = store.create_job(owner_id="owner-r-unit-1", project_id=project.id)

        extract_payload = ScreenshotExtractionRequest(
            instruction_id="inst-r-unit-1",
            instruction_version_id="1",
            timestamp_ms=12000,
            offset_ms=0,
            strategy=ScreenshotStrategy.PRECISE,
            format=ScreenshotFormat.PNG,
        )
        extracted_task, _ = store.create_screenshot_extraction_task(
            owner_id="owner-r-unit-1",
            job_id=job.id,
            payload=extract_payload,
        )
        completed_extract = store.complete_screenshot_task_success(
            task_id=extracted_task.id,
            image_uri="s3://bucket/screenshots/r-unit-1-base.png",
            width=1000,
            height=500,
        )
        anchor_id = completed_extract.anchor_id
        assert anchor_id is not None

        replace_payload = ScreenshotReplaceRequest(
            instruction_version_id="1",
            timestamp_ms=12500,
            offset_ms=50,
            strategy=ScreenshotStrategy.PRECISE,
            format=ScreenshotFormat.PNG,
            idempotency_key="replace-unit-1",
        )

        first_replace, replayed = store.create_screenshot_replace_task(
            owner_id="owner-r-unit-1",
            anchor_id=anchor_id,
            job_id=job.id,
            instruction_id="inst-r-unit-1",
            payload=replace_payload,
        )
        self.assertFalse(replayed)
        writes_after_first = store.screenshot_task_write_count

        replay_by_idempotency, replayed_again = store.create_screenshot_replace_task(
            owner_id="owner-r-unit-1",
            anchor_id=anchor_id,
            job_id=job.id,
            instruction_id="inst-r-unit-1",
            payload=replace_payload,
        )
        self.assertTrue(replayed_again)
        self.assertEqual(replay_by_idempotency.id, first_replace.id)
        self.assertEqual(store.screenshot_task_write_count, writes_after_first)

        with self.assertRaises(ValueError):
            store.create_screenshot_replace_task(
                owner_id="owner-r-unit-1",
                anchor_id=anchor_id,
                job_id=job.id,
                instruction_id="inst-r-unit-1",
                payload=replace_payload.model_copy(update={"timestamp_ms": 12600}),
            )
        self.assertEqual(store.screenshot_task_write_count, writes_after_first)

        same_as_active_payload = ScreenshotReplaceRequest(
            instruction_version_id="1",
            timestamp_ms=12000,
            offset_ms=0,
            strategy=ScreenshotStrategy.PRECISE,
            format=ScreenshotFormat.PNG,
            idempotency_key="replace-unit-2",
        )
        no_op_task, no_op_replayed = store.create_screenshot_replace_task(
            owner_id="owner-r-unit-1",
            anchor_id=anchor_id,
            job_id=job.id,
            instruction_id="inst-r-unit-1",
            payload=same_as_active_payload,
        )
        self.assertTrue(no_op_replayed)
        self.assertEqual(no_op_task.operation.value, "replace")
        self.assertEqual(no_op_task.status, ScreenshotTaskStatus.SUCCEEDED)
        self.assertEqual(no_op_task.asset_id, completed_extract.asset_id)

        replay_no_op, replay_no_op_again = store.create_screenshot_replace_task(
            owner_id="owner-r-unit-1",
            anchor_id=anchor_id,
            job_id=job.id,
            instruction_id="inst-r-unit-1",
            payload=same_as_active_payload,
        )
        self.assertTrue(replay_no_op_again)
        self.assertEqual(replay_no_op.id, no_op_task.id)

        changed_active_task, changed_active_replayed = store.create_screenshot_replace_task(
            owner_id="owner-r-unit-1",
            anchor_id=anchor_id,
            job_id=job.id,
            instruction_id="inst-r-unit-1",
            payload=ScreenshotReplaceRequest(
                instruction_version_id="1",
                timestamp_ms=12600,
                offset_ms=0,
                strategy=ScreenshotStrategy.PRECISE,
                format=ScreenshotFormat.PNG,
            ),
        )
        self.assertFalse(changed_active_replayed)
        store.complete_screenshot_task_success(
            task_id=changed_active_task.id,
            image_uri="s3://bucket/screenshots/r-unit-1-switch.png",
            width=1000,
            height=500,
        )

        historical_again, historical_replayed = store.create_screenshot_replace_task(
            owner_id="owner-r-unit-1",
            anchor_id=anchor_id,
            job_id=job.id,
            instruction_id="inst-r-unit-1",
            payload=same_as_active_payload.model_copy(update={"idempotency_key": "replace-unit-3"}),
        )
        self.assertFalse(historical_replayed)
        self.assertNotEqual(historical_again.id, no_op_task.id)

    def test_soft_delete_screenshot_asset_applies_fallback_traversal_and_idempotency(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="owner-d-unit-1", name="Project")
        job = store.create_job(owner_id="owner-d-unit-1", project_id=project.id)

        extracted_task, _ = store.create_screenshot_extraction_task(
            owner_id="owner-d-unit-1",
            job_id=job.id,
            payload=ScreenshotExtractionRequest(
                instruction_id="inst-d-unit-1",
                instruction_version_id="1",
                timestamp_ms=12000,
                offset_ms=0,
                strategy=ScreenshotStrategy.PRECISE,
                format=ScreenshotFormat.PNG,
            ),
        )
        base_completed = store.complete_screenshot_task_success(
            task_id=extracted_task.id,
            image_uri="s3://bucket/screenshots/d-unit-1-base.png",
            width=1000,
            height=500,
        )
        anchor_id = base_completed.anchor_id
        base_asset_id = base_completed.asset_id
        assert anchor_id is not None
        assert base_asset_id is not None

        replace_mid, _ = store.create_screenshot_replace_task(
            owner_id="owner-d-unit-1",
            anchor_id=anchor_id,
            job_id=job.id,
            instruction_id="inst-d-unit-1",
            payload=ScreenshotReplaceRequest(
                instruction_version_id="1",
                timestamp_ms=12500,
            ),
        )
        mid_completed = store.complete_screenshot_task_success(
            task_id=replace_mid.id,
            image_uri="s3://bucket/screenshots/d-unit-1-mid.png",
            width=1000,
            height=500,
        )
        mid_asset_id = mid_completed.asset_id
        assert mid_asset_id is not None

        replace_top, _ = store.create_screenshot_replace_task(
            owner_id="owner-d-unit-1",
            anchor_id=anchor_id,
            job_id=job.id,
            instruction_id="inst-d-unit-1",
            payload=ScreenshotReplaceRequest(
                instruction_version_id="1",
                timestamp_ms=13000,
            ),
        )
        top_completed = store.complete_screenshot_task_success(
            task_id=replace_top.id,
            image_uri="s3://bucket/screenshots/d-unit-1-top.png",
            width=1000,
            height=500,
        )
        top_asset_id = top_completed.asset_id
        assert top_asset_id is not None

        anchor_after_mid_delete, mid_deleted, mid_replayed = store.soft_delete_screenshot_asset(
            owner_id="owner-d-unit-1",
            anchor_id=anchor_id,
            asset_id=mid_asset_id,
        )
        self.assertFalse(mid_replayed)
        self.assertTrue(mid_deleted.is_deleted)
        self.assertEqual(anchor_after_mid_delete.active_asset_id, top_asset_id)

        anchor_after_top_delete, top_deleted, top_replayed = store.soft_delete_screenshot_asset(
            owner_id="owner-d-unit-1",
            anchor_id=anchor_id,
            asset_id=top_asset_id,
        )
        self.assertFalse(top_replayed)
        self.assertTrue(top_deleted.is_deleted)
        self.assertEqual(anchor_after_top_delete.active_asset_id, base_asset_id)

        anchor_after_repeat, top_repeat, repeat_replayed = store.soft_delete_screenshot_asset(
            owner_id="owner-d-unit-1",
            anchor_id=anchor_id,
            asset_id=top_asset_id,
        )
        self.assertTrue(repeat_replayed)
        self.assertTrue(top_repeat.is_deleted)
        self.assertEqual(anchor_after_repeat.active_asset_id, base_asset_id)

        anchor_after_base_delete, base_deleted, base_replayed = store.soft_delete_screenshot_asset(
            owner_id="owner-d-unit-1",
            anchor_id=anchor_id,
            asset_id=base_asset_id,
        )
        self.assertFalse(base_replayed)
        self.assertTrue(base_deleted.is_deleted)
        self.assertIsNone(anchor_after_base_delete.active_asset_id)

        for deleted_id in (base_asset_id, mid_asset_id, top_asset_id):
            asset = store.get_screenshot_asset_for_owner(owner_id="owner-d-unit-1", asset_id=deleted_id)
            self.assertIsNotNone(asset)
            assert asset is not None
            self.assertTrue(asset.is_deleted)

        with self.assertRaises(ValueError):
            store.soft_delete_screenshot_asset(
                owner_id="owner-d-unit-1",
                anchor_id=anchor_id,
                asset_id="asset-missing-d-unit-1",
            )

    def test_screenshot_replace_service_validates_anchor_instruction_version_context(self) -> None:
        store = InMemoryStore()
        service = JobService(store)
        project = store.create_project(owner_id="owner-r-unit-2", name="Project")
        job = store.create_job(owner_id="owner-r-unit-2", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-r-unit-2",
            instruction_id="inst-r-unit-2",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        requested = service.request_screenshot_extraction(
            owner_id="owner-r-unit-2",
            job_id=job.id,
            payload=ScreenshotExtractionRequest(
                instruction_id="inst-r-unit-2",
                instruction_version_id="1",
                timestamp_ms=12000,
            ),
        )
        completed = store.complete_screenshot_task_success(
            task_id=requested.task.task_id,
            image_uri="s3://bucket/screenshots/r-unit-2-base.png",
            width=1000,
            height=500,
        )
        anchor_id = completed.anchor_id
        assert anchor_id is not None

        with self.assertRaises(ApiError) as mismatch:
            service.request_screenshot_replacement(
                owner_id="owner-r-unit-2",
                anchor_id=anchor_id,
                payload=ScreenshotReplaceRequest(
                    instruction_version_id="2",
                    timestamp_ms=12500,
                ),
            )
        self.assertEqual(mismatch.exception.status_code, 404)
        self.assertEqual(mismatch.exception.payload.code, "RESOURCE_NOT_FOUND")

    def test_get_screenshot_anchor_service_resolves_char_range_retain_and_remap(self) -> None:
        store = InMemoryStore()
        service = JobService(store)
        project = store.create_project(owner_id="owner-a-unit-3", name="Project")
        job = store.create_job(owner_id="owner-a-unit-3", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-a-unit-3",
            instruction_id="inst-a-unit-3",
            job_id=job.id,
            version=1,
            markdown="# Title\n01234567890123456789",
        )
        store.create_instruction_version(
            owner_id="owner-a-unit-3",
            instruction_id="inst-a-unit-3",
            job_id=job.id,
            version=2,
            markdown="# Title\n012345",
        )

        created = service.create_screenshot_anchor(
            owner_id="owner-a-unit-3",
            instruction_id="inst-a-unit-3",
            payload=ScreenshotAnchorCreateRequest(
                instruction_version_id="1",
                addressing=AnchorAddress(
                    address_type=AnchorAddressType.CHAR_RANGE,
                    char_range={"start_offset": 10, "end_offset": 18},
                ),
            ),
        )

        retained = service.get_screenshot_anchor(
            owner_id="owner-a-unit-3",
            anchor_id=created.id,
            target_instruction_version_id="1",
        )
        assert retained.resolution is not None
        self.assertEqual(retained.resolution.resolution_state.value, "retain")
        self.assertEqual(retained.resolution.source_instruction_version_id, "1")
        self.assertEqual(retained.resolution.target_instruction_version_id, "1")

        remapped = service.get_screenshot_anchor(
            owner_id="owner-a-unit-3",
            anchor_id=created.id,
            target_instruction_version_id="2",
        )
        assert remapped.resolution is not None
        self.assertEqual(remapped.resolution.resolution_state.value, "remap")
        self.assertEqual(remapped.resolution.trace["method"], "char_range_scale")
        self.assertIn("remapped_range", remapped.resolution.trace["evidence"])

    def test_create_screenshot_anchor_service_rejects_unknown_block_and_out_of_bounds_char_range(self) -> None:
        store = InMemoryStore()
        service = JobService(store)
        project = store.create_project(owner_id="owner-a-unit-4", name="Project")
        job = store.create_job(owner_id="owner-a-unit-4", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-a-unit-4",
            instruction_id="inst-a-unit-4",
            job_id=job.id,
            version=1,
            markdown="# Intro {#intro}\nBody",
        )

        before_anchor_count = len(store.screenshot_anchors_by_id)
        with self.assertRaises(ApiError) as missing_block:
            service.create_screenshot_anchor(
                owner_id="owner-a-unit-4",
                instruction_id="inst-a-unit-4",
                payload=ScreenshotAnchorCreateRequest(
                    instruction_version_id="1",
                    addressing=AnchorAddress(
                        address_type=AnchorAddressType.BLOCK_ID,
                        block_id="missing",
                    ),
                ),
            )
        self.assertEqual(missing_block.exception.status_code, 404)
        self.assertEqual(missing_block.exception.payload.code, "RESOURCE_NOT_FOUND")

        with self.assertRaises(ApiError) as out_of_bounds:
            service.create_screenshot_anchor(
                owner_id="owner-a-unit-4",
                instruction_id="inst-a-unit-4",
                payload=ScreenshotAnchorCreateRequest(
                    instruction_version_id="1",
                    addressing=AnchorAddress(
                        address_type=AnchorAddressType.CHAR_RANGE,
                        char_range={"start_offset": 0, "end_offset": 1000},
                    ),
                ),
            )
        self.assertEqual(out_of_bounds.exception.status_code, 404)
        self.assertEqual(out_of_bounds.exception.payload.code, "RESOURCE_NOT_FOUND")
        self.assertEqual(len(store.screenshot_anchors_by_id), before_anchor_count)

    def test_get_screenshot_task_for_owner_is_scoped_and_read_only(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="owner-s-unit-2", name="Project")
        job = store.create_job(owner_id="owner-s-unit-2", project_id=project.id)
        payload = ScreenshotExtractionRequest(
            instruction_id="inst-s-unit-2",
            instruction_version_id="1",
            timestamp_ms=8000,
        )
        task, _ = store.create_screenshot_extraction_task(
            owner_id="owner-s-unit-2",
            job_id=job.id,
            payload=payload,
        )
        writes_before = store.screenshot_task_write_count

        owned = store.get_screenshot_task_for_owner(owner_id="owner-s-unit-2", task_id=task.id)
        self.assertIsNotNone(owned)
        assert owned is not None
        owned.status = ScreenshotTaskStatus.FAILED

        fetched_again = store.get_screenshot_task_for_owner(owner_id="owner-s-unit-2", task_id=task.id)
        self.assertIsNotNone(fetched_again)
        assert fetched_again is not None
        self.assertEqual(fetched_again.status, ScreenshotTaskStatus.PENDING)
        self.assertIsNone(store.get_screenshot_task_for_owner(owner_id="owner-other", task_id=task.id))
        self.assertEqual(store.screenshot_task_write_count, writes_before)

    def test_screenshot_polling_service_is_owner_scoped_and_read_only(self) -> None:
        store = InMemoryStore()
        service = JobService(store)
        project = store.create_project(owner_id="owner-s-unit-3", name="Project")
        job = store.create_job(owner_id="owner-s-unit-3", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-s-unit-3",
            instruction_id="inst-s-unit-3",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        requested = service.request_screenshot_extraction(
            owner_id="owner-s-unit-3",
            job_id=job.id,
            payload=ScreenshotExtractionRequest(
                instruction_id="inst-s-unit-3",
                instruction_version_id="1",
                timestamp_ms=12000,
            ),
        )
        self.assertFalse(requested.replayed)
        writes_before_poll = store.screenshot_task_write_count

        polled = service.get_screenshot_task(owner_id="owner-s-unit-3", task_id=requested.task.task_id)
        self.assertEqual(polled.task_id, requested.task.task_id)
        self.assertEqual(polled.status, ScreenshotTaskStatus.PENDING)
        self.assertEqual(store.screenshot_task_write_count, writes_before_poll)

        with self.assertRaises(ApiError) as cross_owner:
            service.get_screenshot_task(owner_id="owner-other", task_id=requested.task.task_id)
        self.assertEqual(cross_owner.exception.status_code, 404)
        self.assertEqual(cross_owner.exception.payload.code, "RESOURCE_NOT_FOUND")

    def test_custom_upload_repository_enforces_confirm_constraints_and_attach_idempotency(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="owner-u-unit-1", name="Project")
        job = store.create_job(owner_id="owner-u-unit-1", project_id=project.id)
        extracted, _ = store.create_screenshot_extraction_task(
            owner_id="owner-u-unit-1",
            job_id=job.id,
            payload=ScreenshotExtractionRequest(
                instruction_id="inst-u-unit-1",
                instruction_version_id="1",
                timestamp_ms=12000,
            ),
        )
        completed_extract = store.complete_screenshot_task_success(
            task_id=extracted.id,
            image_uri="s3://bucket/screenshots/u-unit-1-base.png",
            width=1000,
            height=500,
        )
        anchor_id = completed_extract.anchor_id
        base_asset_id = completed_extract.asset_id
        assert anchor_id is not None
        assert base_asset_id is not None

        ticket = store.create_custom_upload_ticket(
            owner_id="owner-u-unit-1",
            job_id=job.id,
            payload=CreateCustomUploadRequest(
                filename="custom.png",
                mime_type=ScreenshotMimeType.PNG,
                size_bytes=1024,
                checksum_sha256=_checksum("u-unit-1"),
            ),
        )
        before_asset_count = len(store.screenshot_assets_by_id)
        with self.assertRaises(ValueError):
            store.confirm_custom_upload(
                owner_id="owner-u-unit-1",
                job_id=job.id,
                upload_id=ticket.upload_id,
                payload=ConfirmCustomUploadRequest(
                    mime_type=ScreenshotMimeType.PNG,
                    size_bytes=2048,
                    checksum_sha256=_checksum("u-unit-1"),
                    width=640,
                    height=360,
                ),
            )
        self.assertEqual(len(store.screenshot_assets_by_id), before_asset_count)
        self.assertFalse(store.custom_uploads_by_id[ticket.upload_id].confirmed)

        ticket_expired = store.create_custom_upload_ticket(
            owner_id="owner-u-unit-1",
            job_id=job.id,
            payload=CreateCustomUploadRequest(
                filename="expired.png",
                mime_type=ScreenshotMimeType.PNG,
                size_bytes=512,
                checksum_sha256=_checksum("u-unit-expired"),
            ),
        )
        store.custom_uploads_by_id[ticket_expired.upload_id].expires_at = datetime.now(UTC) - timedelta(seconds=1)
        with self.assertRaises(ValueError):
            store.confirm_custom_upload(
                owner_id="owner-u-unit-1",
                job_id=job.id,
                upload_id=ticket_expired.upload_id,
                payload=ConfirmCustomUploadRequest(
                    mime_type=ScreenshotMimeType.PNG,
                    size_bytes=512,
                    checksum_sha256=_checksum("u-unit-expired"),
                    width=640,
                    height=360,
                ),
            )

        confirmed_asset, replayed_confirm = store.confirm_custom_upload(
            owner_id="owner-u-unit-1",
            job_id=job.id,
            upload_id=ticket.upload_id,
            payload=ConfirmCustomUploadRequest(
                mime_type=ScreenshotMimeType.PNG,
                size_bytes=1024,
                checksum_sha256=_checksum("u-unit-1"),
                width=640,
                height=360,
            ),
        )
        self.assertFalse(replayed_confirm)
        self.assertEqual(confirmed_asset.kind, "UPLOADED")
        self.assertTrue(store.custom_uploads_by_id[ticket.upload_id].confirmed)

        before_anchor_asset_count = len(store.screenshot_asset_ids_by_anchor.get(anchor_id, []))
        first_attach, first_replayed = store.attach_confirmed_upload_to_anchor(
            owner_id="owner-u-unit-1",
            anchor_id=anchor_id,
            instruction_version_id="1",
            upload_id=ticket.upload_id,
            idempotency_key="attach-u-unit-1",
            payload_signature="sig-u-unit-1",
        )
        self.assertFalse(first_replayed)
        self.assertNotEqual(first_attach.active_asset_id, base_asset_id)
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_anchor_asset_count + 1)
        attached_asset_id = first_attach.active_asset_id
        assert attached_asset_id is not None

        replay_attach, replayed = store.attach_confirmed_upload_to_anchor(
            owner_id="owner-u-unit-1",
            anchor_id=anchor_id,
            instruction_version_id="1",
            upload_id=ticket.upload_id,
            idempotency_key="attach-u-unit-1",
            payload_signature="sig-u-unit-1",
        )
        self.assertTrue(replayed)
        self.assertEqual(replay_attach.active_asset_id, attached_asset_id)
        self.assertEqual(replay_attach.instruction_version_id, "1")
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_anchor_asset_count + 1)

        second_attach, second_replayed = store.attach_confirmed_upload_to_anchor(
            owner_id="owner-u-unit-1",
            anchor_id=anchor_id,
            instruction_version_id="2",
            upload_id=ticket.upload_id,
            idempotency_key="attach-u-unit-2",
            payload_signature="sig-u-unit-2",
        )
        self.assertFalse(second_replayed)
        self.assertEqual(second_attach.instruction_version_id, "2")
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_anchor_asset_count + 2)

        replay_attach_after_second, replayed_after_second = store.attach_confirmed_upload_to_anchor(
            owner_id="owner-u-unit-1",
            anchor_id=anchor_id,
            instruction_version_id="1",
            upload_id=ticket.upload_id,
            idempotency_key="attach-u-unit-1",
            payload_signature="sig-u-unit-1",
        )
        self.assertTrue(replayed_after_second)
        self.assertEqual(replay_attach_after_second.active_asset_id, attached_asset_id)
        self.assertEqual(replay_attach_after_second.instruction_version_id, "1")
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_anchor_asset_count + 2)

        with self.assertRaises(ValueError):
            store.attach_confirmed_upload_to_anchor(
                owner_id="owner-u-unit-1",
                anchor_id=anchor_id,
                instruction_version_id="1",
                upload_id=ticket.upload_id,
                idempotency_key="attach-u-unit-1",
                payload_signature="sig-u-unit-1-different",
            )
        self.assertEqual(len(store.screenshot_asset_ids_by_anchor.get(anchor_id, [])), before_anchor_asset_count + 2)

    def test_custom_upload_service_enforces_instruction_context_and_no_leak(self) -> None:
        store = InMemoryStore()
        service = JobService(store)
        project = store.create_project(owner_id="owner-u-unit-2", name="Project")
        job = store.create_job(owner_id="owner-u-unit-2", project_id=project.id)
        store.create_instruction_version(
            owner_id="owner-u-unit-2",
            instruction_id="inst-u-unit-2",
            job_id=job.id,
            version=1,
            markdown="# baseline",
        )
        requested = service.request_screenshot_extraction(
            owner_id="owner-u-unit-2",
            job_id=job.id,
            payload=ScreenshotExtractionRequest(
                instruction_id="inst-u-unit-2",
                instruction_version_id="1",
                timestamp_ms=12000,
            ),
        )
        completed = store.complete_screenshot_task_success(
            task_id=requested.task.task_id,
            image_uri="s3://bucket/screenshots/u-unit-2-base.png",
            width=1000,
            height=500,
        )
        anchor_id = completed.anchor_id
        assert anchor_id is not None

        ticket = service.create_custom_upload_ticket(
            owner_id="owner-u-unit-2",
            job_id=job.id,
            payload=CreateCustomUploadRequest(
                filename="custom.webp",
                mime_type=ScreenshotMimeType.WEBP,
                size_bytes=3072,
                checksum_sha256=_checksum("u-unit-2"),
            ),
        )
        service.confirm_custom_upload(
            owner_id="owner-u-unit-2",
            job_id=job.id,
            upload_id=ticket.upload_id,
            payload=ConfirmCustomUploadRequest(
                mime_type=ScreenshotMimeType.WEBP,
                size_bytes=3072,
                checksum_sha256=_checksum("u-unit-2"),
                width=640,
                height=360,
            ),
        )

        with self.assertRaises(ApiError) as missing_instruction_version:
            service.attach_uploaded_asset(
                owner_id="owner-u-unit-2",
                anchor_id=anchor_id,
                payload=AttachUploadedAssetRequest(
                    upload_id=ticket.upload_id,
                    instruction_version_id="2",
                ),
            )
        self.assertEqual(missing_instruction_version.exception.status_code, 404)
        self.assertEqual(missing_instruction_version.exception.payload.code, "RESOURCE_NOT_FOUND")

        with self.assertRaises(ApiError) as cross_owner:
            service.attach_uploaded_asset(
                owner_id="owner-u-unit-2-other",
                anchor_id=anchor_id,
                payload=AttachUploadedAssetRequest(
                    upload_id=ticket.upload_id,
                    instruction_version_id="1",
                ),
            )
        self.assertEqual(cross_owner.exception.status_code, 404)
        self.assertEqual(cross_owner.exception.payload.code, "RESOURCE_NOT_FOUND")

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
