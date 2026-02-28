"""FSM transition invariant tests for Story 3.1."""

from __future__ import annotations

import unittest

from app.domain.job_fsm import ensure_transition
from app.errors import ApiError
from app.repositories.memory import InMemoryStore
from app.schemas.job import JobStatus


class JobFsmUnitTests(unittest.TestCase):
    def test_allowed_transition_examples_across_lifecycle(self) -> None:
        allowed_pairs = [
            (JobStatus.CREATED, JobStatus.UPLOADING),
            (JobStatus.UPLOADING, JobStatus.UPLOADED),
            (JobStatus.UPLOADED, JobStatus.AUDIO_EXTRACTING),
            (JobStatus.AUDIO_EXTRACTING, JobStatus.AUDIO_EXTRACTING),
            (JobStatus.AUDIO_EXTRACTING, JobStatus.AUDIO_READY),
            (JobStatus.AUDIO_READY, JobStatus.TRANSCRIBING),
            (JobStatus.TRANSCRIBING, JobStatus.TRANSCRIBING),
            (JobStatus.TRANSCRIPT_READY, JobStatus.GENERATING),
            (JobStatus.GENERATING, JobStatus.GENERATING),
            (JobStatus.DRAFT_READY, JobStatus.EDITING),
            (JobStatus.EDITING, JobStatus.EXPORTING),
            (JobStatus.EXPORTING, JobStatus.DONE),
        ]
        for old_status, new_status in allowed_pairs:
            with self.subTest(old_status=old_status, new_status=new_status):
                ensure_transition(old_status, new_status)

    def test_forbidden_transitions_return_contract_shape(self) -> None:
        invalid_pairs = [
            (JobStatus.CREATED, JobStatus.TRANSCRIBING),
            (JobStatus.UPLOADING, JobStatus.GENERATING),
            (JobStatus.DRAFT_READY, JobStatus.UPLOADED),
        ]
        for old_status, new_status in invalid_pairs:
            with self.subTest(old_status=old_status, new_status=new_status):
                with self.assertRaises(ApiError) as context:
                    ensure_transition(old_status, new_status)
                self.assertEqual(context.exception.status_code, 409)
                self.assertEqual(context.exception.payload.code, "FSM_TRANSITION_INVALID")
                details = context.exception.payload.details
                self.assertEqual(details["current_status"], old_status)
                self.assertEqual(details["attempted_status"], new_status)
                self.assertIn("allowed_next_statuses", details)

    def test_terminal_states_are_immutable(self) -> None:
        for terminal_status in (JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.DONE):
            with self.subTest(terminal_status=terminal_status):
                with self.assertRaises(ApiError) as context:
                    ensure_transition(terminal_status, JobStatus.CREATED)
                self.assertEqual(context.exception.status_code, 409)
                self.assertEqual(context.exception.payload.code, "FSM_TERMINAL_IMMUTABLE")
                details = context.exception.payload.details
                self.assertEqual(details["current_status"], terminal_status)
                self.assertEqual(details["attempted_status"], JobStatus.CREATED)
                self.assertEqual(details["allowed_next_statuses"], [])

    def test_self_transition_outside_retry_states_is_rejected(self) -> None:
        for state in (JobStatus.CREATED, JobStatus.UPLOADING, JobStatus.AUDIO_READY):
            with self.subTest(state=state):
                with self.assertRaises(ApiError) as context:
                    ensure_transition(state, state)
                self.assertEqual(context.exception.status_code, 409)
                self.assertEqual(context.exception.payload.code, "FSM_TRANSITION_INVALID")
                self.assertEqual(context.exception.payload.details["current_status"], state)
                self.assertEqual(context.exception.payload.details["attempted_status"], state)

    def test_store_transition_helper_applies_valid_transition_with_consistent_writes(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        job = store.create_job(owner_id="user-a", project_id=project.id)
        before_updated_at = job.updated_at
        before_writes = store.job_write_count

        store.transition_job_status(job=job, new_status=JobStatus.UPLOADING)

        self.assertEqual(job.status, JobStatus.UPLOADING)
        self.assertIsNotNone(job.updated_at)
        self.assertGreaterEqual(job.updated_at, before_updated_at)
        self.assertEqual(store.job_write_count, before_writes + 1)

    def test_store_transition_helper_has_no_mutation_on_invalid_transition(self) -> None:
        store = InMemoryStore()
        project = store.create_project(owner_id="user-a", name="Project A")
        job = store.create_job(owner_id="user-a", project_id=project.id)
        before_status = job.status
        before_updated_at = job.updated_at
        before_writes = store.job_write_count

        with self.assertRaises(ApiError) as context:
            store.transition_job_status(job=job, new_status=JobStatus.TRANSCRIBING)

        self.assertEqual(context.exception.status_code, 409)
        self.assertEqual(context.exception.payload.code, "FSM_TRANSITION_INVALID")
        self.assertEqual(job.status, before_status)
        self.assertEqual(job.updated_at, before_updated_at)
        self.assertEqual(store.job_write_count, before_writes)


if __name__ == "__main__":
    unittest.main()
