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
        self.assertEqual(store.dispatch_write_count, 0)

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
