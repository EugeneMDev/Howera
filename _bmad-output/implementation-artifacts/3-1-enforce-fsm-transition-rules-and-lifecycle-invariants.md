# Story 3.1: Enforce FSM Transition Rules and Lifecycle Invariants

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want all job status changes validated by FSM,
so that lifecycle behavior remains deterministic and safe.

## Acceptance Criteria

1. Given a status transition request from `current_status` to `attempted_status` that is not allowed by FSM, when transition validation runs, then the API returns `409` with `error_code=FSM_TRANSITION_INVALID`, the error payload includes `current_status`, `attempted_status`, and `allowed_next_statuses`, and no mutation is persisted.
2. Given a transition request for terminal state mutation (`FAILED`, `CANCELLED`, `DONE` to any new status), when validation runs, then the API returns `409` with `error_code=FSM_TERMINAL_IMMUTABLE` and no mutation is persisted.

## Tasks / Subtasks

- [x] Implement centralized FSM-governed job transition mutation (AC: 1, 2)
- [x] Introduce/align a single transition application boundary that always calls `domain/job_fsm.ensure_transition(old_status, new_status)` before status mutation.
- [x] Refactor job status updates in service/callback paths to use the centralized transition boundary instead of ad-hoc direct assignments.
- [x] Ensure failed transition attempts do not mutate `status`, `updated_at`, write counters, or related manifests/failure metadata.
- [x] Preserve terminal immutability semantics for `FAILED`, `CANCELLED`, and `DONE`.
- [x] Align transition error payloads with contract shape (AC: 1, 2)
- [x] Confirm `409` payloads include `current_status`, `attempted_status`, and `allowed_next_statuses` for invalid transitions.
- [x] Confirm terminal-mutation attempts return `FSM_TERMINAL_IMMUTABLE` and no write side effects.
- [x] Keep no-leak and existing auth/error semantics unchanged.
- [x] Add mandatory FSM unit coverage for valid/invalid/terminal transitions (AC: 1, 2)
- [x] Add dedicated unit tests covering representative allowed transitions across lifecycle stages.
- [x] Add forbidden-transition tests (at least one per major stage group).
- [x] Add terminal-state immutability tests for `FAILED`, `CANCELLED`, and `DONE`.
- [x] Add service/API regression tests proving invalid transitions produce `409` and no mutation persists.
- [x] Verify quality gates and contract safety (AC: 1, 2)
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.
- [x] Validate `/openapi.json` still exposes contract-compliant transition error schemas where applicable.

### Review Follow-ups (AI)

- [x] [AI-Review][HIGH] Ensure terminal-state run attempts (`FAILED`/`CANCELLED`/`DONE` -> `AUDIO_EXTRACTING`) return `FSM_TERMINAL_IMMUTABLE` by routing this path through canonical FSM validation instead of precheck-only `FSM_TRANSITION_INVALID`. [apps/api/app/services/jobs.py:87]
- [x] [AI-Review][HIGH] Restrict no-op self-transitions to FSM-allowed retry states; current global early-return (`old_status == new_status`) allows invalid no-op transitions (for example `CREATED -> CREATED`) to bypass `FSM_TRANSITION_INVALID`, and callback flow then persists event/timestamp/write side effects instead of rejecting. [apps/api/app/domain/job_fsm.py:38]

## Dev Notes

### Developer Context Section

- Story 2.1 and 2.2 rely on FSM validation paths (`confirm-upload`, `run`) and should continue to emit contract-safe conflict payloads.
- Story 1.4 callback processing also performs state transitions; this story standardizes transition enforcement across all mutation paths.
- Existing code already has `domain/job_fsm.ensure_transition`; this story focuses on invariant enforcement and mutation consistency.

### Technical Requirements

- Every non-initial job status mutation must pass through `domain/job_fsm.ensure_transition`.
- Direct transition mutations that bypass FSM validation are not allowed.
- Invalid transition attempts must produce `409` contract errors with transition details and no persisted mutation.
- Terminal states (`FAILED`, `CANCELLED`, `DONE`) are immutable.
- Transition enforcement must be deterministic across API-triggered and callback-triggered state updates.

### Architecture Compliance

- `spec/` is source of truth and read-only.
- Contract-first: preserve documented status codes and error shapes.
- Keep route handlers thin; transition logic belongs to domain/service/repository boundaries.
- Preserve existing no-leak behavior and security constraints.

### Library & Framework Requirements

- FastAPI + Pydantic contract schemas remain authoritative for response payloads.
- Reuse `ApiError`/error-schema patterns; do not introduce ad-hoc error envelopes.
- No new external dependencies are expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/domain/job_fsm.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/app/repositories/memory.py` (if central transition helper is introduced here)
- `apps/api/app/schemas/error.py` (only if contract-shape alignment is needed)
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_job_fsm.py` (new dedicated FSM unit suite, if created)

### Testing Requirements

- Add explicit unit tests for allowed transitions, invalid transitions, and terminal-state immutability.
- Add regression tests showing invalid transition attempts do not mutate persisted state/write counters.
- Preserve current behavior for already implemented stories (auth/ownership/confirm-upload/run/callback).
- Final verification gate: `make lint`, `make test`, `make check` in `apps/api`.

### Previous Story Intelligence

- Prior stories surfaced contract-shape drift quickly; transition conflicts must stay schema-accurate.
- Run and callback flows are now implemented and should reuse the same transition enforcement boundary.
- Logging redaction work from Story 1.5 should not be regressed while updating transition paths.

### Git Intelligence Summary

- Epic 1 and Epic 2 delivered auth, ownership, callback, confirm-upload, and run behaviors.
- Epic 3 starts with deterministic FSM invariants; keep this change set tightly focused on transition enforcement and tests.

### Project Structure Notes

- No standalone architecture artifact exists in `_bmad-output/planning-artifacts/`; use OpenAPI + FSM spec + PRD + acceptance tasks + implemented patterns.
- Continue using established `domain/services/repositories/routes/schemas/tests` structure under `apps/api`.

### References

- `spec/domain/job_fsm.md` (transition table, terminal state rules, required FSM test coverage)
- `spec/api/openapi.yaml` (`FsmTransitionError`, `TransitionErrorDetails`, conflict response schemas)
- `spec/acceptance/tasks_codex_v1.md` (FSM validation expectations across run/callback flows)
- `_bmad-output/planning-artifacts/epics.md` (Epic 3, Story 3.1)
- `_bmad-output/planning-artifacts/prd.md` (FR-007, FR-008, FR-011)
- `_bmad-output/implementation-artifacts/2-1-confirm-job-upload-with-video-uri.md`
- `_bmad-output/implementation-artifacts/2-2-start-workflow-run-for-an-upload-confirmed-job.md`
- `_bmad-output/implementation-artifacts/1-4-validate-internal-callback-secret.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `spec/domain/job_fsm.md`
- `spec/api/openapi.yaml`

### Completion Notes List

- Added centralized FSM transition boundary in repository (`transition_job_status`) to ensure all service/callback status mutations pass through `ensure_transition`.
- Refactored job-service transition paths (`confirm-upload`, `run`) to remove direct status assignments and use centralized transition application.
- Refactored internal callback service transition application to use centralized boundary while preserving replay/order/conflict behavior.
- Added shared `allowed_next_statuses(...)` helper in FSM domain logic and aligned run conflict payload details to include contract-safe allowed-transition metadata.
- Added dedicated FSM unit suite (`test_job_fsm.py`) covering representative allowed transitions, forbidden transitions, terminal immutability, and no-mutation behavior for invalid transition attempts.
- Verified existing API contract behavior remains intact (openapi response-shape tests continue to pass).
- Verification completed in `apps/api` on 2026-02-26: `make lint`, `make test`, and `make check` all passed.
- ✅ Resolved review finding [HIGH]: terminal-state run attempts now flow through canonical FSM transition validation and return `FSM_TERMINAL_IMMUTABLE`.
- Added API and unit regression coverage for terminal-state run attempts across `FAILED`, `CANCELLED`, and `DONE`.
- ✅ Resolved review finding [HIGH]: FSM self-transitions are now enforced by transition table rules (retry states only), preventing invalid no-op callback transitions from being persisted.
- Added FSM and callback regression coverage for invalid self-transition rejection with no side effects.
- Verification rerun completed in `apps/api` on 2026-02-26: `make lint`, `make test`, and `make check` all passed.

### File List

- `_bmad-output/implementation-artifacts/3-1-enforce-fsm-transition-rules-and-lifecycle-invariants.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/app/domain/job_fsm.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_job_fsm.py`
- `apps/api/tests/test_jobs_ownership.py`

### Change Log

- 2026-02-26: Created Story 3.1 artifact with AC-mapped implementation tasks and moved story status to `ready-for-dev`.
- 2026-02-26: Implemented Story 3.1 centralized FSM transition enforcement, aligned transition error detail metadata, added mandatory FSM/unit no-mutation regression tests, ran quality gates, and moved story to `review`.
- 2026-02-26: Senior code review completed with changes requested; story moved to `in-progress`.
- 2026-02-26: Addressed code-review follow-up for terminal run semantics, added terminal-state run regression tests, reran quality gates, and moved story back to `review`.
- 2026-02-26: Re-review identified remaining FSM self-transition invariant gap in callback path; story moved to `in-progress`.
- 2026-02-26: Addressed re-review follow-up for FSM self-transition enforcement, added callback no-side-effect regression coverage, reran quality gates, and moved story back to `review`.
- 2026-02-26: Final re-review approved after self-transition enforcement fix and regression validation; story moved to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-02-26

### Outcome

- Changes Requested

### Summary

- Centralized FSM transition plumbing is in place and mutation-side no-op guarantees for invalid transitions are well covered.
- Remaining gap: terminal-state run attempts currently emit `FSM_TRANSITION_INVALID` instead of `FSM_TERMINAL_IMMUTABLE`, which weakens lifecycle invariant semantics.

### Severity Breakdown

- High: 1
- Medium: 0
- Low: 0

### Action Items

- [x] [HIGH] Route terminal run attempts through canonical `ensure_transition` behavior (or equivalent terminal check) so `FAILED`/`CANCELLED`/`DONE` attempts return `FSM_TERMINAL_IMMUTABLE` with no mutation. [apps/api/app/services/jobs.py:87]

### Re-Review (AI) - 2026-02-26

#### Outcome

- Changes Requested

#### Summary

- Most Story 3.1 invariants are implemented and tested.
- A remaining high-severity gap exists: `ensure_transition` currently accepts all `old_status == new_status` transitions before FSM table checks, so disallowed no-op transitions can be accepted and persisted through callback processing instead of returning `FSM_TRANSITION_INVALID`.

#### Severity Breakdown

- High: 1
- Medium: 0
- Low: 0

#### Action Items

- [x] [HIGH] Enforce self-transition rules via FSM table (or explicit allowlist) so non-allowed no-op transitions are rejected with `FSM_TRANSITION_INVALID`, and add callback-path regression coverage proving no side effects on rejection. [apps/api/app/domain/job_fsm.py:38]

### Final Re-Review (AI) - 2026-02-26

#### Outcome

- Approved

#### Summary

- FSM transition validation now enforces self-transitions through the transition table, allowing retry no-ops only where explicitly modeled.
- Callback path now rejects invalid no-op transitions (for example `CREATED -> CREATED`) with `FSM_TRANSITION_INVALID` and no persisted side effects.
- Verification gates pass with regression coverage included (`make lint`, `make test`, `make check`).

#### Severity Breakdown

- High: 0
- Medium: 0
- Low: 0

#### Action Items

- None.
