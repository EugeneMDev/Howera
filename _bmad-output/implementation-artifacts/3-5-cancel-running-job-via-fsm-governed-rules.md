# Story 3.5: Cancel Running Job via FSM-Governed Rules

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to cancel an in-flight job when allowed,
so that I can stop unwanted processing safely.

## Acceptance Criteria

1. Given owned job in cancellable state, when cancel is requested, then transition to `CANCELLED` is applied via FSM and audit event is emitted with required fields.
2. Given job is non-cancellable, when cancel is requested, then API returns `409` with `error_code=FSM_TRANSITION_INVALID` and response includes `current_status` and `attempted_status=CANCELLED`, and no mutation is persisted.

## Tasks / Subtasks

- [x] Implement `POST /jobs/{jobId}/cancel` with ownership + no-leak behavior (AC: 1, 2)
- [x] Add route handler for cancel endpoint using existing auth dependency and owner-scoped job lookup.
- [x] Ensure missing/non-owned job returns contract-safe `404 RESOURCE_NOT_FOUND`.
- [x] Keep route thin; cancellation logic must live in service/repository boundary.
- [x] Enforce FSM-governed cancel transition semantics (AC: 1, 2)
- [x] Add `JobService.cancel_job(owner_id, job_id)` and route all state updates through `ensure_transition` via repository transition helper.
- [x] Ensure successful cancel transitions set job status to `CANCELLED` and return contract `Job` payload.
- [x] Ensure non-cancellable states return `409` FSM error with attempted status `CANCELLED` and no write side effects.
- [x] Emit auditable cancel transition event with required fields (AC: 1)
- [x] Reuse/add transition-audit persistence boundary so cancel writes exactly one event with required fields: `event_type`, `job_id`, `project_id`, `actor_type`, `prev_status`, `new_status`, `occurred_at`, `recorded_at`, `correlation_id`.
- [x] Ensure actor mapping is API/editor path safe (expected `editor`) and `recorded_at` is server-generated UTC.
- [x] Ensure failed/rejected cancel attempts emit no transition audit event.
- [x] Add AC-mapped tests and verify contract invariants (AC: 1, 2)
- [x] Add API tests for successful cancel from cancellable states.
- [x] Add API tests for non-cancellable/terminal cancel attempts asserting `409` and no side effects.
- [x] Add ownership/no-leak tests for cancel endpoint.
- [x] Add audit event assertions for cancel success and no-audit assertions for cancel rejection.
- [x] Update OpenAPI contract assertions in tests for `/jobs/{jobId}/cancel` response set.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Story 3.1 established strict FSM enforcement and terminal immutability semantics (`FSM_TRANSITION_INVALID` vs `FSM_TERMINAL_IMMUTABLE`).
- Story 3.2 and 3.3 hardened callback idempotency/ordering and transactional mutation boundaries; cancel flow must not regress those invariants.
- Story 3.4 introduced transition-audit persistence for accepted callback transitions; Story 3.5 should extend auditable transition coverage to API-driven cancel transitions.

### Technical Requirements

- Endpoint in scope: `POST /jobs/{jobId}/cancel`.
- Contract behavior from OpenAPI:
  - `200` returns `Job` on successful cancel.
  - `404` returns `NoLeakNotFoundError` for missing/non-owned job.
  - `409` returns `FsmTransitionError` when cancellation is not allowed.
- Cancellation target status is always `CANCELLED` and must be validated by FSM transition rules.
- Successful cancellation must emit a transition audit event with required fields and without secrets/raw transcript/prompt content.

### Architecture Compliance

- `spec/` is read-only source of truth.
- All status transitions must be validated through `domain/job_fsm.ensure_transition` (direct `job.status = ...` is forbidden outside controlled repository helper boundary).
- Terminal states (`FAILED`, `CANCELLED`, `DONE`) are immutable.
- Keep business logic in service/repository layers; route handlers remain thin.
- Preserve no-existence-leak policy and secure logging constraints.

### Library & Framework Requirements

- FastAPI + Pydantic response/request schemas remain contract authority.
- Reuse existing error model patterns (`ApiError`, `FsmTransitionError`, `NoLeakNotFoundError`).
- No new external dependencies expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py` (if OpenAPI response-set assertions need extension)
- `apps/api/app/main.py` (only if runtime OpenAPI shaping requires targeted response wiring)

### Testing Requirements

- Validate successful cancel in FSM-cancellable state transitions to `CANCELLED` and returns contract `Job` payload.
- Validate non-cancellable state returns `409` FSM error with `attempted_status=CANCELLED` and no mutation.
- Validate no-leak behavior for non-owned/missing job (`404 RESOURCE_NOT_FOUND`).
- Validate cancel success emits exactly one transition audit event with required fields.
- Validate rejected cancel emits no transition audit event.
- Validate `/openapi.json` includes `/jobs/{jobId}/cancel` with `200/404/409` response set.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 3.4 already provides deterministic transition-audit field mapping and replay/rejection no-duplicate invariants in repository-backed persistence.
- Story 3.4 tests emphasized side-effect accounting (`job_write_count`, callback event counts, audit event counts); reuse this pattern for cancel no-side-effect assertions.
- Prior stories repeatedly surfaced OpenAPI response drift as a regression risk; ensure cancel endpoint response codes/schema refs are asserted explicitly.

### Git Intelligence Summary

- Recent Epic 3 implementation concentrated transition correctness in:
  - `apps/api/app/domain/job_fsm.py`
  - `apps/api/app/repositories/memory.py`
  - `apps/api/app/services/jobs.py`
  - `apps/api/app/services/internal_callbacks.py`
- Existing route/service patterns for owner-scoped operations and no-leak behavior should be mirrored for cancel endpoint implementation.

### Project Structure Notes

- No standalone architecture markdown exists under `_bmad-output/planning-artifacts/`; derive implementation constraints from `spec/api/openapi.yaml`, `spec/domain/job_fsm.md`, and existing Story 3 artifacts.
- Keep diffs minimal and focused on cancel endpoint flow + tests.

### References

- `spec/api/openapi.yaml` (`/jobs/{jobId}/cancel`, `FsmTransitionError`, `NoLeakNotFoundError`)
- `spec/domain/job_fsm.md` (global cancel transition rules and terminal immutability)
- `spec/acceptance/tasks_codex_v1.md` (Task 06 run/cancel/retry expectations)
- `_bmad-output/planning-artifacts/epics.md` (Epic 3, Story 3.5)
- `_bmad-output/project-context.md` (architecture invariants)
- `_bmad-output/implementation-artifacts/3-4-emit-auditable-status-transition-events.md`
- `apps/api/app/domain/job_fsm.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/routes/dependencies.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py`

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
- `_bmad-output/implementation-artifacts/3-4-emit-auditable-status-transition-events.md`
- `apps/api/app/domain/job_fsm.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`

### Completion Notes List

- Implemented `POST /jobs/{jobId}/cancel` route and `JobService.cancel_job(...)` with owner-scoped no-leak behavior (`404 RESOURCE_NOT_FOUND` for missing/non-owned).
- Added repository atomic status+audit helper `transition_job_status_with_audit(...)` and reused normalized transition-audit record building for callback and API-driven transitions.
- Cancel success now transitions through FSM to `CANCELLED` and emits one transition audit event with required fields (`event_type`, `job_id`, `project_id`, `actor_type=editor`, `prev_status`, `new_status`, `occurred_at`, `recorded_at`, `correlation_id`).
- Added request correlation-id dependency wiring for cancel flow audit correlation propagation.
- Cleared active dispatch records on successful cancel so cancelled jobs cannot be replayed through stale run dispatch state.
- Added/updated regression coverage for cancel success, invalid/terminal rejection no-side-effects, no-leak ownership behavior, service-level cancel semantics, and `/openapi.json` cancel contract responses.
- Verification completed in `apps/api`: `make lint`, `make test`, and `make check` all passed.

### File List

- `_bmad-output/implementation-artifacts/3-5-cancel-running-job-via-fsm-governed-rules.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/routes/dependencies.py`
- `apps/api/app/routes/jobs.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/main.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py`

### Change Log

- 2026-02-28: Created Story 3.5 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-02-28: Started Story 3.5 dev workflow.
- 2026-02-28: Implemented cancel endpoint/service/audit behavior with AC-mapped tests, ran `make lint`, `make test`, and `make check`, and moved story to `review`.
- 2026-02-28: Completed code-review follow-up fixes (cancel dispatch cleanup, cancel 404 no-side-effect assertions, generated cancel correlation-id audit assertion), reran quality gates, and moved story to `done`.

## Senior Developer Review (AI)

### Review Date

2026-02-28

### Reviewer

GPT-5.3-Codex

### Outcome

Approve

### Findings Summary

- 0 High, 0 Medium, 0 Low remaining after review fixes.

### Findings and Resolutions

- [x] [HIGH] Cancelled jobs could still replay `/run` as `200` when stale dispatch records remained, bypassing terminal-state run rejection behavior.
  - Fix: Delete active dispatch record on successful cancel so rerun attempts from `CANCELLED` follow FSM terminal immutability (`409 FSM_TERMINAL_IMMUTABLE`).
  - Evidence: `apps/api/app/services/jobs.py` (`cancel_job`), `apps/api/app/repositories/memory.py` (`delete_dispatch_for_job`), `apps/api/tests/test_jobs_ownership.py` (`test_cancel_job_success_returns_200_and_emits_transition_audit`, `test_cancel_job_service_enforces_fsm_and_emits_transition_audit`)
- [x] [MEDIUM] Cancel no-leak (`404`) tests did not assert no side effects for write/audit counters.
  - Fix: Added assertions that `job_write_count` and `transition_audit_events` remain unchanged for cross-owner and missing-job cancel attempts.
  - Evidence: `apps/api/tests/test_jobs_ownership.py` (`test_cancel_job_cross_owner_and_missing_job_are_no_leak_404`)
- [x] [MEDIUM] Cancel flow had no explicit regression proving generated request correlation IDs propagate into emitted transition audit records when `X-Correlation-Id` is absent.
  - Fix: Added regression asserting audit `correlation_id` is generated (`req-...`) when header is omitted.
  - Evidence: `apps/api/tests/test_jobs_ownership.py` (`test_cancel_job_without_correlation_header_generates_request_correlation_id_for_audit`)
