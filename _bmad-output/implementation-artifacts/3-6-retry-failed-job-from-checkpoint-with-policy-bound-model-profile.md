# Story 3.6: Retry Failed Job from Checkpoint with Policy-Bound Model Profile

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to retry a failed job from its latest valid checkpoint under allowed model policy,
so that recovery is efficient and controlled.

## Acceptance Criteria

1. Given retry request, when validation runs, then retry is allowed only from `FAILED`, and request is rejected otherwise with `409` and `error_code=RETRY_NOT_ALLOWED_STATE`.
2. Given job is already running, dispatched, or in-progress, when retry is requested, then API returns `409` with `error_code=JOB_ALREADY_RUNNING` and no new dispatch occurs.
3. Given valid retry, when accepted, then `resume_from_status` and checkpoint reference are resolved and persisted, and model profile selection is policy-validated and recorded with retry metadata.
4. Given repeated identical retry request, when processed, then retry dispatch is idempotent (no duplicate orchestrator execution), and previously created dispatch reference is returned.
5. Given dispatch payload is built, when sent to orchestrator, then it includes `job_id`, `project_id`, `video_uri`, `callback_url`, `resume_from_status`, `checkpoint_ref`, and `model_profile`.
6. Given orchestrator dispatch fails, when failure occurs, then job state is not advanced, and API returns contract-defined upstream error (`502 ORCHESTRATOR_DISPATCH_FAILED`).

## Tasks / Subtasks

- [x] Implement `POST /jobs/{jobId}/retry` route and service boundary (AC: 1, 2, 3, 4, 5, 6)
- [x] Add retry endpoint handler in jobs routes with authenticated owner-scoped behavior.
- [x] Preserve route thinness; retry orchestration and state logic must remain in service/repository boundaries.
- [x] Enforce retry state/conflict contract semantics (AC: 1, 2)
- [x] Allow retry only from `FAILED`; otherwise return `409 RETRY_NOT_ALLOWED_STATE` with `current_status` + `attempted_status` details.
- [x] Detect active-dispatch/running conflicts and return `409 JOB_ALREADY_RUNNING` without dispatch duplication.
- [x] Implement retry idempotency by `client_request_id` for same job and payload signature.
- [x] Persist and return checkpoint/model retry metadata (AC: 3, 4, 5)
- [x] Resolve `resume_from_status` and `checkpoint_ref` from artifact/checkpoint state deterministically.
- [x] Validate and persist `model_profile` policy decision with retry metadata.
- [x] Build orchestrator retry payload with required fields: `job_id`, `project_id`, `video_uri`, `callback_url`, `resume_from_status`, `checkpoint_ref`, `model_profile`.
- [x] Return `202` on first accepted retry and `200` on idempotent replay with existing dispatch reference.
- [x] Preserve dispatch safety and no-illegal-advance behavior (AC: 6)
- [x] Ensure dispatch failures return `502 ORCHESTRATOR_DISPATCH_FAILED` and do not illegally advance state.
- [x] Ensure failure/rejection paths do not mutate status, dispatch counters, or persisted retry metadata.
- [x] Add AC-mapped tests + contract assertions (AC: 1, 2, 3, 4, 5, 6)
- [x] Add API tests for retry success, replay idempotency, non-FAILED rejection, active-running conflict, and dispatch-failure rollback safety.
- [x] Add no-leak ownership tests for missing/non-owned retry target (`404 RESOURCE_NOT_FOUND`).
- [x] Add unit tests for checkpoint selection/model-policy validation behavior and no-side-effect conflict paths.
- [x] Update OpenAPI contract assertions for `/jobs/{jobId}/retry` response set (`200/202/404/409/502`) and schema refs.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] `run_job` replay scope narrowed to `dispatch_type == "run"` so retry dispatch records are not returned by `/run` replay paths. [apps/api/app/services/jobs.py:87]
- [x] [AI-Review][HIGH] Added explicit retry-resume transition path for callbacks from `FAILED` using persisted checkpoint status as FSM source, enabling post-retry progression while retaining `ensure_transition` validation. [apps/api/app/repositories/memory.py:180]
- [x] [AI-Review][MEDIUM] Added regression tests for (a) `/run` after retry dispatch and (b) callback progression path after accepted retry. [apps/api/tests/test_jobs_ownership.py:436, apps/api/tests/test_internal_callback_transactions.py:42]
- [x] [AI-Review][MEDIUM] Reconciled Story 3.6 `File List` with working-tree scope by including `apps/api/app/routes/dependencies.py`. [apps/api/app/routes/dependencies.py:56]

## Dev Notes

### Developer Context Section

- Story 2.2 established run dispatch semantics: first dispatch `202`, replay `200`, no duplicate dispatch, and `502` upstream failure rollback behavior.
- Story 3.1 established FSM invariants and terminal immutability behavior through `ensure_transition`.
- Story 3.5 finalized cancel behavior and dispatch cleanup for terminal states; retry logic must not regress run/cancel invariants or terminal semantics.

### Technical Requirements

- Endpoint in scope: `POST /jobs/{jobId}/retry`.
- Request contract: `RetryJobRequest` with required `model_profile` and `client_request_id`.
- Response contract:
  - `202 RetryJobResponse` on first accepted retry.
  - `200 RetryJobResponse` on idempotent replay.
  - `404 NoLeakNotFoundError` for missing/non-owned job.
  - `409 RetryStateConflictError` (`RETRY_NOT_ALLOWED_STATE` or `JOB_ALREADY_RUNNING`).
  - `502 UpstreamDispatchError` when orchestrator dispatch fails and state is not advanced.
- Retry response must include `job_id`, `status`, `resume_from_status`, `checkpoint_ref`, `model_profile`, `dispatch_id`, `replayed`.
- Dispatch payload for retry must include `job_id`, `project_id`, `video_uri`, `callback_url`, `resume_from_status`, `checkpoint_ref`, `model_profile`.

### Architecture Compliance

- `spec/` is read-only source of truth.
- Retry entry point from FSM guidance is `FAILED` only; re-run/retry must not delete existing artifacts.
- Maintain single active pipeline semantics and no duplicate dispatch side effects.
- Keep route handlers thin and business rules in service/repository layers.
- Preserve no-existence-leak behavior and structured error payloads.

### Library & Framework Requirements

- FastAPI + Pydantic schema contracts remain authoritative.
- Reuse existing error/dispatch patterns (`ApiError`, `UpstreamDispatchError`, no-leak 404 shape).
- No new external dependencies expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/job.py` (only if contract-safe retry metadata structures need internal persistence helpers)
- `apps/api/app/main.py` (if runtime OpenAPI response filtering needs extension)
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py` (OpenAPI response contract assertions)

### Testing Requirements

- Validate retry only from `FAILED` and `RETRY_NOT_ALLOWED_STATE` for all non-FAILED states.
- Validate running/active-dispatch conflict returns `JOB_ALREADY_RUNNING` and no duplicate dispatch occurs.
- Validate accepted retry resolves/persists `resume_from_status`, `checkpoint_ref`, and `model_profile` with correct dispatch payload fields.
- Validate idempotent replay by `client_request_id` returns existing dispatch with `200` and no duplicate side effects.
- Validate dispatch failure returns `502 ORCHESTRATOR_DISPATCH_FAILED` and does not advance state.
- Validate ownership no-leak behavior (`404`) and no-side-effect guarantees on reject paths.
- Validate `/openapi.json` contains `/jobs/{jobId}/retry` with `200/202/404/409/502` and expected schema references.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Existing run-path tests already cover dispatch write counters and replay behavior; mirror these assertions for retry.
- Existing cancellation fixes removed stale dispatch replay on terminal states; retry must explicitly handle active-dispatch checks to avoid semantic drift.
- OpenAPI response-shape drift has been a repeated review issue; keep retry response docs/refs aligned with contract.

### Git Intelligence Summary

- Current implementation has mature patterns for:
  - owner-scoped lookup/no-leak 404s
  - dispatch create/replay/failure handling
  - FSM error shaping
  - transition auditing
- Retry should extend those patterns with minimal diff rather than introducing new parallel state machinery.

### Project Structure Notes

- No dedicated architecture artifact exists in `_bmad-output/planning-artifacts/`; use `spec/api/openapi.yaml`, `spec/domain/job_fsm.md`, and completed Story 2/3 implementation artifacts for guardrails.
- Keep changes tightly scoped to retry logic + tests; avoid unrelated refactors.

### References

- `spec/api/openapi.yaml` (`/jobs/{jobId}/retry`, `RetryJobRequest`, `RetryJobResponse`, `RetryStateConflictError`)
- `spec/domain/job_fsm.md` (retry entry from `FAILED`, checkpoint resume policy, artifact immutability)
- `spec/acceptance/tasks_codex_v1.md` (Task 06 run/cancel/retry + dispatch safety)
- `_bmad-output/planning-artifacts/epics.md` (Epic 3, Story 3.6)
- `_bmad-output/project-context.md` (FSM/idempotency/security invariants)
- `_bmad-output/implementation-artifacts/2-2-start-workflow-run-for-an-upload-confirmed-job.md`
- `_bmad-output/implementation-artifacts/3-5-cancel-running-job-via-fsm-governed-rules.md`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `spec/api/openapi.yaml`
- `spec/domain/job_fsm.md`
- `spec/acceptance/tasks_codex_v1.md`
- `_bmad-output/project-context.md`
- `_bmad-output/implementation-artifacts/2-2-start-workflow-run-for-an-upload-confirmed-job.md`
- `_bmad-output/implementation-artifacts/3-5-cancel-running-job-via-fsm-governed-rules.md`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`

### Completion Notes List

- 2026-02-28: Created Story 3.6 artifact with contract-accurate retry requirements, AC-mapped tasks, implementation guardrails, and verification expectations.
- 2026-02-28: Implemented `POST /jobs/{jobId}/retry` with owner-scoped no-leak behavior, retry conflict semantics, checkpoint/model metadata persistence, idempotent replay by `client_request_id`, and orchestrator payload enforcement.
- 2026-02-28: Added retry API/unit test coverage (success, replay, non-FAILED rejection, active-running conflict, dispatch-failure rollback safety, and ownership 404 no-leak), and updated OpenAPI contract assertions.
- 2026-02-28: Verified in `apps/api` with `make lint`, `make test`, and `make check`.
- 2026-02-28: Senior code review produced follow-up findings; story moved back to `in-progress` with AI review action items.
- 2026-02-28: Resolved all AI review follow-ups (run/retry dispatch separation, retry callback progression path, and regression coverage), reran `make check`, and advanced story to `done`.

### File List

- `_bmad-output/implementation-artifacts/3-6-retry-failed-job-from-checkpoint-with-policy-bound-model-profile.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/main.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/routes/dependencies.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/schemas/error.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/services/jobs.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_internal_callback_transactions.py`
- `apps/api/tests/test_jobs_ownership.py`

### Change Log

- 2026-02-28: Created Story 3.6 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-02-28: Implemented retry endpoint/service/repository flow with checkpoint + model-profile retry metadata, idempotent replay behavior, conflict handling, and dispatch safety; added contract and behavioral tests; moved status to `review`.
- 2026-02-28: Senior code review completed with changes requested; added AI review follow-up tasks and moved status to `in-progress`.
- 2026-02-28: Applied all code-review fixes, added regression tests, reran quality gates, and moved status to `done`.

## Senior Developer Review (AI)

### Review Date

2026-02-28

### Reviewer

GPT-5.3-Codex

### Outcome

Approve

### Findings Summary

- 0 High, 0 Medium, 0 Low remaining.

### Findings and Resolutions

- [x] [HIGH] `/run` replayed retry dispatch records because replay logic did not check dispatch type.
  - Resolution: `run_job` replay now requires `dispatch_type == "run"`, so retry dispatch records do not satisfy `/run` replay.
  - Evidence: `apps/api/app/services/jobs.py:87-101`, `apps/api/tests/test_jobs_ownership.py` (`test_run_job_does_not_replay_retry_dispatch_records`, unit equivalent).
- [x] [HIGH] Retry acceptance path was terminally blocked because callbacks from `FAILED` were validated directly against terminal immutability.
  - Resolution: Added repository retry-resume transition path validating callback transitions from persisted `retry_resume_from_status` through `ensure_transition`.
  - Evidence: `apps/api/app/repositories/memory.py` (`transition_job_status_from_retry_checkpoint`, retry branch in `apply_callback_mutation`), `apps/api/tests/test_internal_callback_transactions.py` (`test_callback_can_progress_job_after_retry_acceptance`).
- [x] [MEDIUM] Regression coverage was missing for run/retry interaction and callback continuation after retry.
  - Resolution: Added API and unit regressions for `/run` vs retry dispatch replay and callback progression after accepted retry.
  - Evidence: `apps/api/tests/test_jobs_ownership.py`, `apps/api/tests/test_internal_callback_transactions.py`.
- [x] [MEDIUM] Story file list was out of sync with changed files in working tree.
  - Resolution: Updated Story 3.6 file list to include `apps/api/app/routes/dependencies.py` and new callback regression test file.
