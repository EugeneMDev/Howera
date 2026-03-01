"""Transactional callback side-effect tests for Story 3.3."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
import os
import unittest

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.routes.dependencies import get_internal_callback_service
from app.schemas.internal import StatusCallbackRequest
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


class CallbackTransactionTests(_SettingsEnvCase):
    def test_callback_can_progress_job_after_retry_acceptance(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        service = JobService(store)
        project = store.create_project(owner_id="owner-1", name="Project")
        job = service.create_job(owner_id="owner-1", project_id=project.id)
        service.confirm_upload(owner_id="owner-1", job_id=job.id, video_uri="s3://bucket/video-retry.mp4")
        service.run_job(owner_id="owner-1", job_id=job.id)
        store.jobs[job.id].status = JobStatus.FAILED

        retry_result = service.retry_job(
            owner_id="owner-1",
            job_id=job.id,
            model_profile="cloud-default",
            client_request_id="retry-callback-progress-1",
        )
        self.assertEqual(retry_result.status, JobStatus.FAILED)
        self.assertEqual(retry_result.resume_from_status, JobStatus.UPLOADED)

        response = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json={
                "event_id": "evt-retry-progress-1",
                "status": "AUDIO_EXTRACTING",
                "occurred_at": "2026-02-27T03:10:00Z",
                "correlation_id": "corr-retry-progress-1",
            },
        )

        self.assertEqual(response.status_code, 204)
        updated_job = store.jobs[job.id]
        self.assertEqual(updated_job.status, JobStatus.AUDIO_EXTRACTING)
        self.assertEqual(len(store.transition_audit_events), 1)
        self.assertEqual(store.transition_audit_events[0].prev_status, JobStatus.FAILED)
        self.assertEqual(store.transition_audit_events[0].new_status, JobStatus.AUDIO_EXTRACTING)

    def test_callback_applies_transactional_status_manifest_and_failure_updates(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)
        store.jobs[job.id].manifest = ArtifactManifest(
            video_uri="s3://bucket/video-original.mp4",
            audio_uri="s3://bucket/audio-original.wav",
            transcript_uri="s3://bucket/transcript-original.json",
            draft_uri="s3://bucket/draft-old.md",
            exports=["exp-old"],
        )

        response = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json={
                "event_id": "evt-txn-1",
                "status": "UPLOADING",
                "occurred_at": "2026-02-27T00:00:00Z",
                "artifact_updates": {
                    "video_uri": "s3://bucket/video-overwrite-attempt.mp4",
                    "audio_uri": "s3://bucket/audio-overwrite-attempt.wav",
                    "transcript_uri": None,
                    "draft_uri": "s3://bucket/draft-new.md",
                    "exports": ["exp-new-1", "exp-new-2"],
                    "unknown_key": "ignored",
                },
                "failure_code": "ORCH_STAGE_FAILED",
                "failure_message": "safe failure message",
                "failed_stage": "TRANSCRIBING",
                "correlation_id": "corr-txn-1",
            },
        )

        self.assertEqual(response.status_code, 204)
        updated_job = store.jobs[job.id]
        self.assertEqual(updated_job.status, JobStatus.UPLOADING)
        self.assertIsNotNone(updated_job.manifest)
        assert updated_job.manifest is not None
        self.assertEqual(updated_job.manifest.video_uri, "s3://bucket/video-original.mp4")
        self.assertEqual(updated_job.manifest.audio_uri, "s3://bucket/audio-original.wav")
        self.assertEqual(updated_job.manifest.transcript_uri, "s3://bucket/transcript-original.json")
        self.assertEqual(updated_job.manifest.draft_uri, "s3://bucket/draft-new.md")
        self.assertEqual(updated_job.manifest.exports, ["exp-new-1", "exp-new-2"])
        self.assertEqual(updated_job.failure_code, "ORCH_STAGE_FAILED")
        self.assertEqual(updated_job.failure_message, "safe failure message")
        self.assertEqual(updated_job.failed_stage, "TRANSCRIBING")
        self.assertIn((job.id, "evt-txn-1"), store.callback_events)
        self.assertEqual(len(store.transition_audit_events), 1)
        audit_event = store.transition_audit_events[0]
        self.assertEqual(audit_event.event_type, "JOB_STATUS_TRANSITION_APPLIED")
        self.assertEqual(audit_event.job_id, job.id)
        self.assertEqual(audit_event.project_id, project.id)
        self.assertEqual(audit_event.actor_type, "system")
        self.assertEqual(audit_event.prev_status, JobStatus.CREATED)
        self.assertEqual(audit_event.new_status, JobStatus.UPLOADING)
        self.assertEqual(audit_event.occurred_at, datetime(2026, 2, 27, 0, 0, tzinfo=UTC))
        self.assertIsInstance(audit_event.recorded_at, datetime)
        self.assertEqual(audit_event.recorded_at.tzinfo, UTC)
        self.assertEqual(audit_event.correlation_id, "corr-txn-1")
        self.assertEqual(
            store.latest_callback_at_by_job[job.id],
            datetime(2026, 2, 27, 0, 0, tzinfo=UTC),
        )

    def test_callback_transition_audit_keeps_supplied_actor_type(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)

        response = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json={
                "event_id": "evt-actor-1",
                "status": "UPLOADING",
                "occurred_at": "2026-02-27T00:05:00Z",
                "actor_type": "orchestrator",
                "correlation_id": "corr-actor-1",
            },
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(store.transition_audit_events), 1)
        self.assertEqual(store.transition_audit_events[0].actor_type, "orchestrator")

    def test_transition_audit_payload_excludes_sensitive_callback_payload_fields(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)
        sensitive_transcript = "TOP-SECRET-TRANSCRIPT-CONTENT"
        sensitive_prompt = "prompt-password-do-not-log"

        response = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json={
                "event_id": "evt-audit-sensitive-1",
                "status": "UPLOADING",
                "occurred_at": "2026-02-27T00:07:00Z",
                "artifact_updates": {
                    "draft_uri": "s3://bucket/draft-sensitive.md",
                    "transcript_text": sensitive_transcript,
                    "prompt_text": sensitive_prompt,
                },
                "correlation_id": "corr-audit-sensitive-1",
            },
        )

        self.assertEqual(response.status_code, 204)
        self.assertEqual(len(store.transition_audit_events), 1)
        audit_payload = asdict(store.transition_audit_events[0])
        self.assertEqual(
            set(audit_payload.keys()),
            {
                "event_type",
                "job_id",
                "project_id",
                "actor_type",
                "prev_status",
                "new_status",
                "occurred_at",
                "recorded_at",
                "correlation_id",
            },
        )
        self.assertNotIn(sensitive_transcript, str(audit_payload))
        self.assertNotIn(sensitive_prompt, str(audit_payload))

    def test_callback_failpoint_rolls_back_all_side_effects(self) -> None:
        for stage in ("after_status", "after_manifest", "after_failure_metadata", "after_callback_event"):
            with self.subTest(stage=stage):
                app = create_app()
                store = app.state.store
                project = store.create_project(owner_id="owner-1", name="Project")
                job = store.create_job(owner_id="owner-1", project_id=project.id)
                store.jobs[job.id].manifest = ArtifactManifest(
                    video_uri="s3://bucket/video-a.mp4",
                    audio_uri="s3://bucket/audio-a.wav",
                    transcript_uri="s3://bucket/transcript-a.json",
                    draft_uri="s3://bucket/draft-a.md",
                    exports=["exp-a"],
                )
                store.jobs[job.id].failure_code = "OLD_CODE"
                store.jobs[job.id].failure_message = "old message"
                store.jobs[job.id].failed_stage = "OLD_STAGE"
                store.set_transcript_segments_for_job(
                    job_id=job.id,
                    segments=[TranscriptSegment(start_ms=0, end_ms=250, text="old")],
                )

                before_job = store.jobs[job.id]
                before_status = before_job.status
                before_updated_at = before_job.updated_at
                before_manifest = before_job.manifest.model_dump() if before_job.manifest is not None else None
                before_failure_code = before_job.failure_code
                before_failure_message = before_job.failure_message
                before_failed_stage = before_job.failed_stage
                before_transcript_segments = [
                    segment.model_dump() for segment in store.list_transcript_segments_for_job(job_id=job.id)
                ]
                before_job_write_count = store.job_write_count
                before_callback_count = len(store.callback_events)
                before_audit_count = len(store.transition_audit_events)
                before_latest = store.latest_callback_at_by_job.get(job.id)

                event_id = f"evt-rollback-{stage}"
                store.callback_mutation_failpoint_event_id = event_id
                store.callback_mutation_failpoint_stage = stage
                store.callback_mutation_failpoint_message = "injected failure"

                callback_service = get_internal_callback_service(store=store)
                payload = StatusCallbackRequest(
                    event_id=event_id,
                    status=JobStatus.UPLOADING,
                    occurred_at=datetime(2026, 2, 27, 0, 10, tzinfo=UTC),
                    artifact_updates={
                        "draft_uri": "s3://bucket/draft-b.md",
                        "transcript_segments": [{"start_ms": 300, "end_ms": 600, "text": "new"}],
                    },
                    failure_code="NEW_CODE",
                    failure_message="new message",
                    failed_stage="NEW_STAGE",
                    correlation_id="corr-rollback-1",
                )

                with self.assertRaisesRegex(RuntimeError, "injected failure"):
                    callback_service.process_status_callback(job_id=job.id, payload=payload)

                rolled_back_job = store.jobs[job.id]
                self.assertEqual(rolled_back_job.status, before_status)
                self.assertEqual(rolled_back_job.updated_at, before_updated_at)
                self.assertEqual(
                    rolled_back_job.manifest.model_dump() if rolled_back_job.manifest is not None else None,
                    before_manifest,
                )
                self.assertEqual(rolled_back_job.failure_code, before_failure_code)
                self.assertEqual(rolled_back_job.failure_message, before_failure_message)
                self.assertEqual(rolled_back_job.failed_stage, before_failed_stage)
                self.assertEqual(
                    [segment.model_dump() for segment in store.list_transcript_segments_for_job(job_id=job.id)],
                    before_transcript_segments,
                )
                self.assertEqual(store.job_write_count, before_job_write_count)
                self.assertEqual(len(store.callback_events), before_callback_count)
                self.assertEqual(len(store.transition_audit_events), before_audit_count)
                self.assertNotIn((job.id, event_id), store.callback_events)
                self.assertEqual(store.latest_callback_at_by_job.get(job.id), before_latest)
                self.assertIsNone(store.callback_mutation_failpoint_event_id)
                self.assertIsNone(store.callback_mutation_failpoint_stage)

    def test_callback_allows_first_write_for_immutable_raw_manifest_keys(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)
        store.jobs[job.id].manifest = ArtifactManifest(video_uri="s3://bucket/video-original.mp4")

        response = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json={
                "event_id": "evt-first-write-1",
                "status": "UPLOADING",
                "occurred_at": "2026-02-27T00:30:00Z",
                "artifact_updates": {
                    "audio_uri": "s3://bucket/audio-new.wav",
                    "transcript_uri": "s3://bucket/transcript-new.json",
                    "video_uri": "s3://bucket/video-overwrite-attempt.mp4",
                },
                "correlation_id": "corr-first-write-1",
            },
        )

        self.assertEqual(response.status_code, 204)
        updated_job = store.jobs[job.id]
        self.assertIsNotNone(updated_job.manifest)
        assert updated_job.manifest is not None
        self.assertEqual(updated_job.manifest.video_uri, "s3://bucket/video-original.mp4")
        self.assertEqual(updated_job.manifest.audio_uri, "s3://bucket/audio-new.wav")
        self.assertEqual(updated_job.manifest.transcript_uri, "s3://bucket/transcript-new.json")

    def test_callback_merge_keeps_unrelated_manifest_keys_and_ignores_nulls(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)
        store.jobs[job.id].manifest = ArtifactManifest(
            video_uri="s3://bucket/video-a.mp4",
            audio_uri="s3://bucket/audio-a.wav",
            transcript_uri="s3://bucket/transcript-a.json",
            draft_uri="s3://bucket/draft-a.md",
            exports=["exp-a"],
        )

        response_1 = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json={
                "event_id": "evt-merge-1",
                "status": "UPLOADING",
                "occurred_at": "2026-02-27T01:00:00Z",
                "artifact_updates": {"draft_uri": "s3://bucket/draft-b.md"},
                "correlation_id": "corr-merge-1",
            },
        )
        self.assertEqual(response_1.status_code, 204)

        response_2 = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json={
                "event_id": "evt-merge-2",
                "status": "UPLOADED",
                "occurred_at": "2026-02-27T01:05:00Z",
                "artifact_updates": {"draft_uri": None},
                "correlation_id": "corr-merge-2",
            },
        )
        self.assertEqual(response_2.status_code, 204)

        updated_job = store.jobs[job.id]
        self.assertIsNotNone(updated_job.manifest)
        assert updated_job.manifest is not None
        self.assertEqual(updated_job.manifest.draft_uri, "s3://bucket/draft-b.md")
        self.assertEqual(updated_job.manifest.exports, ["exp-a"])
        self.assertEqual(updated_job.manifest.video_uri, "s3://bucket/video-a.mp4")
        self.assertEqual(updated_job.manifest.audio_uri, "s3://bucket/audio-a.wav")
        self.assertEqual(updated_job.manifest.transcript_uri, "s3://bucket/transcript-a.json")

    def test_non_failure_callback_does_not_erase_existing_failure_metadata(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)
        store.jobs[job.id].status = JobStatus.UPLOADING
        store.jobs[job.id].failure_code = "OLD_CODE"
        store.jobs[job.id].failure_message = "old failure"
        store.jobs[job.id].failed_stage = "OLD_STAGE"

        response = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json={
                "event_id": "evt-non-failure-1",
                "status": "UPLOADED",
                "occurred_at": "2026-02-27T02:00:00Z",
                "correlation_id": "corr-non-failure-1",
            },
        )
        self.assertEqual(response.status_code, 204)

        updated_job = store.jobs[job.id]
        self.assertEqual(updated_job.failure_code, "OLD_CODE")
        self.assertEqual(updated_job.failure_message, "old failure")
        self.assertEqual(updated_job.failed_stage, "OLD_STAGE")

    def test_failed_callback_updates_failure_metadata(self) -> None:
        app = create_app()
        client = TestClient(app)
        store = app.state.store
        project = store.create_project(owner_id="owner-1", name="Project")
        job = store.create_job(owner_id="owner-1", project_id=project.id)
        store.jobs[job.id].status = JobStatus.UPLOADING

        response = client.post(
            f"/api/v1/internal/jobs/{job.id}/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json={
                "event_id": "evt-failure-meta-1",
                "status": "FAILED",
                "occurred_at": "2026-02-27T03:00:00Z",
                "failure_code": "TRANSCRIPT_TIMEOUT",
                "failure_message": "safe timeout",
                "failed_stage": "TRANSCRIBING",
                "correlation_id": "corr-failure-meta-1",
            },
        )
        self.assertEqual(response.status_code, 204)

        updated_job = store.jobs[job.id]
        self.assertEqual(updated_job.failure_code, "TRANSCRIPT_TIMEOUT")
        self.assertEqual(updated_job.failure_message, "safe timeout")
        self.assertEqual(updated_job.failed_stage, "TRANSCRIBING")


if __name__ == "__main__":
    unittest.main()
