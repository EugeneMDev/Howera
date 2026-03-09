# Story 2.2: Start Workflow Run for an Upload-Confirmed Job

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to trigger processing for my upload-confirmed job,
so that draft generation begins asynchronously.

## Acceptance Criteria

1. Given an authenticated editor with an owned job in `UPLOADED` state, when `POST /jobs/{jobId}/run` is called, then the API accepts the request and exactly one workflow execution is dispatched to the orchestrator.
2. Given the job is not in `UPLOADED` state, when `POST /jobs/{jobId}/run` is called, then the API returns a contract-defined error and no dispatch occurs.
3. Given repeated run calls are made for the same eligible job, when requests are processed, then the endpoint behaves idempotently and duplicate orchestrator executions are not created.
4. Given a dispatch is performed, when the orchestrator payload is built, then it includes `job_id`, `project_id`, `video_uri`, and `callback_url`.
5. Given orchestrator dispatch fails, when failure is detected, then job state is not advanced and a contract-defined upstream error is returned.
6. Given run dispatch and failure handling paths execute, when logs are emitted, then no secrets or raw transcript content are logged.

## Tasks / Subtasks

- [x] Implement run endpoint contract path and response schema wiring (AC: 1, 2, 3, 5)
- [x] Add `POST /jobs/{jobId}/run` route with auth principal dependency and no route-level business logic.
- [x] Add/align `RunJobResponse` schema usage for route responses (`202` first dispatch, `200` idempotent replay).
- [x] Add/align contract error schema usage for `404` (`NoLeakNotFoundError`), `409` (`FsmTransitionError`), and `502` (`UpstreamDispatchError`).
- [x] Ensure runtime OpenAPI includes `/jobs/{jobId}/run` with `200/202/404/409/502` response set exactly as defined in `spec/api/openapi.yaml`.
- [x] Implement FSM-gated, owner-scoped, idempotent run dispatch behavior (AC: 1, 2, 3, 4)
- [x] Enforce owner-scoped job lookup with no-leak `404` parity for unauthorized vs missing jobs.
- [x] Validate run eligibility from `UPLOADED` via FSM (`domain/job_fsm.ensure_transition`) before any state mutation.
- [x] Persist a single dispatch reference for the job and reuse it for replayed run calls.
- [x] Build orchestrator payload with required fields: `job_id`, `project_id`, `video_uri`, `callback_url`.
- [x] Prevent duplicate dispatch calls under repeated run requests for the same job.
- [x] Implement upstream failure handling and secure observability (AC: 5, 6)
- [x] Return `502 ORCHESTRATOR_DISPATCH_FAILED` when dispatch fails and ensure no illegal status advance occurs.
- [x] Keep artifact/state writes logically consistent when dispatch fails (no partial dispatch artifacts committed as success).
- [x] Emit safe logs with correlation metadata only; never log callback secret, auth token, or raw transcript/prompt-like payload values.
- [x] Add regression tests for run behavior, idempotency, and failure safety (AC: 1, 2, 3, 4, 5, 6)
- [x] Test first run on `UPLOADED` returns `202`, includes `dispatch_id`, and performs exactly one dispatch.
- [x] Test run replay returns `200` with `replayed=true` and does not create a second dispatch.
- [x] Test run from non-`UPLOADED` states returns contract `409` and performs no dispatch.
- [x] Test cross-owner and nonexistent job parity returns no-leak `404 RESOURCE_NOT_FOUND`.
- [x] Test upstream dispatch failure returns `502 ORCHESTRATOR_DISPATCH_FAILED` with no illegal state advance.
- [x] Test run and failure logs do not include secrets/raw transcript-like content while preserving safe correlation metadata.
- [x] Verify quality gates and contract safety (AC: 1, 2, 3, 4, 5, 6)
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.
- [x] Validate `/openapi.json` includes `/jobs/{jobId}/run` and schema alignment with `spec/api/openapi.yaml`.

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Enforce strict run precondition that first-time dispatch is allowed only from `UPLOADED`; current logic can dispatch again from `AUDIO_EXTRACTING` when dispatch record state is missing, violating AC-2 and contract no-dispatch rule for non-`UPLOADED` jobs. [apps/api/app/services/jobs.py:91]
- [x] [AI-Review][MEDIUM] Prevent dispatch payloads with empty `video_uri`; current payload builder falls back to empty string and can send invalid upstream inputs when job state and manifest drift out of sync. [apps/api/app/services/jobs.py:109]

## Dev Notes

### Developer Context Section

- Story 2.1 now guarantees `confirm-upload` stores `artifact_manifest.video_uri` and transitions the job to `UPLOADED`.
- Story 1.4 established callback idempotency/FSM enforcement patterns for async workflow status updates.
- Story 1.5 established secure logging boundaries that must remain intact for run dispatch/failure paths.

### Technical Requirements

- Endpoint in scope: `POST /jobs/{jobId}/run`.
- No request body; response model is `RunJobResponse` (`job_id`, `status`, `dispatch_id`, `replayed`).
- First successful dispatch returns `202`; idempotent replay returns `200`.
- Job must be in `UPLOADED` for initial run acceptance; invalid transitions return contract `409`.
- Dispatch payload must include `job_id`, `project_id`, `video_uri`, `callback_url`.
- Dispatch failures must return contract `502 ORCHESTRATOR_DISPATCH_FAILED` and must not advance job state.

### Architecture Compliance

- `spec/` is source of truth and read-only.
- All status transitions must go through `domain/job_fsm.ensure_transition`.
- Preserve owner-scoped no-leak semantics for editor-facing job lookup.
- Keep routes thin; place orchestration/dispatch behavior in service/repository boundaries.
- Maintain deterministic idempotency guarantees for repeated run requests.

### Library & Framework Requirements

- FastAPI + Pydantic response models for route contract compliance.
- Reuse existing `ApiError` patterns and contract error schema mapping.
- Avoid direct provider SDK coupling in business logic; keep integrations isolated to adapter/service boundaries.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/schemas/error.py`
- `apps/api/app/routes/dependencies.py` (if callback URL or dispatch dependency wiring is needed)
- `apps/api/app/core/config.py` (if run dispatch configuration is introduced)
- `apps/api/tests/test_jobs_ownership.py` and/or `apps/api/tests/test_auth_middleware.py`

### Testing Requirements

- Add AC-mapped tests for first dispatch acceptance (`202`) and replay idempotency (`200`).
- Assert non-eligible state attempts return contract `409` with no dispatch side effects.
- Assert upstream dispatch failure returns contract `502` with no illegal state advance.
- Validate no-leak behavior for unauthorized and nonexistent job access (`404` parity).
- Validate secure logging assertions for run dispatch and failure paths.
- Final verification gate: `make lint`, `make test`, `make check` in `apps/api`.

### Previous Story Intelligence

- Runtime OpenAPI response drift has appeared in prior stories; explicitly verify response codes and schema refs for the run endpoint.
- Existing ownership/no-leak behavior should be reused, not re-implemented in route handlers.
- Secure logging controls from Story 1.5 should be reused for any new run-path logs.

### Git Intelligence Summary

- Epic 2 now has upload confirmation in place (Story 2.1 done) and this story should focus narrowly on run dispatch semantics.
- Keep this change set focused on run endpoint contract behavior, idempotent dispatch safety, and tests only.

### Project Structure Notes

- No standalone architecture artifact exists in `_bmad-output/planning-artifacts/`; use OpenAPI + PRD + FSM spec + acceptance tasks + existing implementation patterns.
- Continue using the established `routes/services/repositories/schemas/tests` structure in `apps/api`.

### References

- `spec/api/openapi.yaml` (`/jobs/{jobId}/run`, `RunJobResponse`, `UpstreamDispatchError`)
- `spec/domain/job_fsm.md` (run eligibility from `UPLOADED`, transition invariants, single active pipeline intent)
- `spec/acceptance/tasks_codex_v1.md` (Task 06 run/cancel/retry + dispatch safety)
- `_bmad-output/planning-artifacts/epics.md` (Epic 2, Story 2.2)
- `_bmad-output/planning-artifacts/prd.md` (FR-009, FR-010, FR-032, NFR-011)
- `_bmad-output/implementation-artifacts/2-1-confirm-job-upload-with-video-uri.md`
- `_bmad-output/implementation-artifacts/1-5-enforce-secure-logging-boundaries.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `spec/api/openapi.yaml`
- `spec/domain/job_fsm.md`
- `spec/acceptance/tasks_codex_v1.md`

### Completion Notes List

- Implemented `POST /jobs/{jobId}/run` with owner-scoped lookup, FSM eligibility enforcement from `UPLOADED`, and idempotent replay semantics (`202` first dispatch, `200` replay).
- Added in-memory workflow dispatch records to enforce single dispatch creation per job and deterministic replay by returning stored `dispatch_id`.
- Added orchestrator payload construction with required fields: `job_id`, `project_id`, `video_uri`, `callback_url`.
- Added upstream dispatch failure handling returning contract `502 ORCHESTRATOR_DISPATCH_FAILED` with no illegal status/state advance.
- Added secure run-path logging that preserves hashed correlation identifiers while avoiding sensitive payload/secret leakage.
- Extended OpenAPI/runtime contract verification to include `/jobs/{jobId}/run` response set (`200/202/404/409/502`) and schema refs.
- Added API/unit regression coverage for run success, replay idempotency, invalid-state conflict, no-leak ownership parity, failure rollback safety, and run log redaction.
- Verification completed in `apps/api` on 2026-02-26: `make lint`, `make test`, and `make check` all passed.
- ✅ Resolved review finding [HIGH]: first-time run dispatch now hard-requires `UPLOADED` status, preventing re-dispatch when dispatch state is missing for in-progress statuses.
- ✅ Resolved review finding [MEDIUM]: run dispatch now fails fast on missing/empty `video_uri` instead of dispatching invalid upstream payload values.
- Added regression tests for both review scenarios (in-progress-without-dispatch-record and uploaded-without-video-uri).

### File List

- `_bmad-output/implementation-artifacts/2-2-start-workflow-run-for-an-upload-confirmed-job.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/main.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/schemas/error.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/services/jobs.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py`

### Change Log

- 2026-02-26: Created Story 2.2 artifact with AC-mapped implementation tasks and moved story status to `ready-for-dev`.
- 2026-02-26: Implemented Story 2.2 run endpoint dispatch/idempotency/failure behavior, added contract and regression tests, passed quality gates, and moved story to `review`.
- 2026-02-26: Senior code review completed with changes requested; story moved to `in-progress` for follow-up fixes.
- 2026-02-26: Addressed all code-review follow-ups (strict `UPLOADED` run gate and non-empty `video_uri` precondition), added targeted regression tests, reran quality gates, and moved story back to `review`.
- 2026-02-26: Re-review completed with no remaining HIGH/MEDIUM issues; story moved to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-02-26

### Outcome

- Changes Requested

### Summary

- Core run-path behavior, replay semantics, and contract response wiring are in place.
- Two gaps remain: non-`UPLOADED` enforcement can be bypassed in a state-drift case, and dispatch payload can include empty `video_uri`.

### Severity Breakdown

- High: 1
- Medium: 1
- Low: 0

### Action Items

- [x] [HIGH] Require `job.status == UPLOADED` for first-time dispatch before attempting any dispatch write; do not allow fallback acceptance from in-progress statuses even if FSM helper returns for equal-state transitions. [apps/api/app/services/jobs.py:91]
- [x] [MEDIUM] Fail fast when `artifact_manifest.video_uri` is missing/empty for a run-eligible job, returning a contract-safe conflict path instead of dispatching empty upstream payload values. [apps/api/app/services/jobs.py:109]

### Final Re-Review (AI) - 2026-02-26

#### Outcome

- Approved

#### Summary

- First-time run dispatch is now strictly `UPLOADED`-gated, with replay-only behavior for in-progress statuses backed by existing dispatch records.
- Dispatch payload creation now rejects missing/empty `video_uri`, preventing invalid upstream dispatch requests.
- Added regression coverage for both scenarios; quality gates pass (`make lint`, `make test`, `make check`).
