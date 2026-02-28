# Story 3.2: Validate Callback Contract, Idempotency, and Ordering Policy

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a platform operator,
I want callback processing to validate payload and reject duplicates safely,
so that asynchronous updates are replay-safe.

## Acceptance Criteria

1. Given callback payload with `job_id`, `event_id`, `status`, and `occurred_at`, when first accepted, then idempotency record is stored with unique key `(job_id, event_id)` and callback processing proceeds once.
2. Given same `(job_id, event_id)` and same payload hash is replayed, when received again, then API returns contract-defined replay success (`200` no-op), `replayed=true` is returned, and no state or artifact writes are repeated.
3. Given same `(job_id, event_id)` but different payload content, when received, then API returns `409` with `error_code=EVENT_ID_PAYLOAD_MISMATCH` and no mutation is persisted.
4. Given callback `occurred_at` is older than latest applied event and implies backward or non-monotonic transition, when evaluated, then API returns `409` with `error_code=CALLBACK_OUT_OF_ORDER`, response includes `latest_applied_occurred_at`, `current_status`, and `attempted_status`, and no mutation is persisted.

## Tasks / Subtasks

- [x] Implement first-accept callback idempotency recording and single-apply semantics (AC: 1)
- [x] Persist callback idempotency record keyed by `(job_id, event_id)` on first accepted event.
- [x] Ensure first accepted callback path returns `204` and applies state transition at most once.
- [x] Ensure callback target-job lookup/no-leak policy happens before mutation side effects.
- [x] Implement deterministic replay behavior for identical duplicate payloads (AC: 2)
- [x] Compare incoming callback payload signature against stored payload for the same `(job_id, event_id)`.
- [x] Return `200` replay response with `replayed=true` and contract replay payload fields.
- [x] Ensure replay path performs no additional status/artifact/failure writes and does not duplicate side effects.
- [x] Enforce payload mismatch conflict for duplicate `event_id` with different content (AC: 3)
- [x] Return `409 EVENT_ID_PAYLOAD_MISMATCH` with contract details including `event_id`.
- [x] Ensure mismatch path persists no mutation to job status, artifact/failure metadata, or callback-write counters.
- [x] Enforce callback ordering guard with strict monotonic `occurred_at` policy (AC: 4)
- [x] Reject callbacks where `occurred_at <= latest_applied_occurred_at` with `409 CALLBACK_OUT_OF_ORDER`.
- [x] Include `latest_applied_occurred_at`, `current_status`, and `attempted_status` in conflict details.
- [x] Ensure out-of-order rejection occurs before any state/artifact/failure mutation.
- [x] Preserve contract/FSM boundary and schema alignment (AC: 1, 2, 3, 4)
- [x] Keep `/internal/jobs/{jobId}/status` route thin and delegate behavior to callback service/domain boundary.
- [x] Ensure applied callback status transitions use centralized FSM validation (`ensure_transition` via repository transition helper).
- [x] Verify runtime `/openapi.json` callback route includes `200/204/401/404/409` and `409` oneOf of `FsmTransitionError`, `CallbackOrderingError`, and `EventIdPayloadMismatchError`.
- [x] Add AC-mapped tests and execute quality gates (AC: 1, 2, 3, 4)
- [x] Add API/unit tests for first-accept `204`, identical replay `200` no-op, payload mismatch `409`, and out-of-order/equal-timestamp `409`.
- [x] Add no-mutation assertions across replay/rejection paths (status, `updated_at`, callback event store, latest timestamp, write counters).
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Story 1.4 established callback-secret authentication and initial callback processing semantics (`204` first accept, `200` replay, `409` mismatch/out-of-order).
- Story 3.1 introduced centralized FSM transition boundaries to ensure contract-consistent transition errors across services.
- This story hardens callback contract semantics and replay safety guarantees as a dedicated lifecycle invariant scope.

### Technical Requirements

- Endpoint in scope: `POST /internal/jobs/{jobId}/status`.
- Callback request contract uses `StatusCallbackRequest` (`event_id`, `status`, `occurred_at`, `correlation_id`; optional `actor_type`, `artifact_updates`, `failure_code`, `failure_message`, `failed_stage`).
- Idempotency identity must be `(job_id, event_id)` with deterministic payload-signature comparison.
- First accepted callback must return `204` and apply mutation once.
- Identical replay must return `200` with `replayed=true` and be a no-op for state/artifact/failure writes.
- Duplicate `event_id` with non-identical payload must return `409 EVENT_ID_PAYLOAD_MISMATCH` with `details.event_id`.
- Non-monotonic callback order (`occurred_at <= latest_applied_occurred_at`) must return `409 CALLBACK_OUT_OF_ORDER` with contract details fields.
- All applied callback state mutations must flow through FSM validation.
- Rejected/replayed callback paths must not mutate status, manifests, failure metadata, or write counters.

### Architecture Compliance

- `spec/` remains read-only source of truth.
- Contract-first behavior must remain aligned with `spec/api/openapi.yaml`.
- Callback routes stay thin; business logic resides in service/repository/domain boundaries.
- Status transitions must remain centralized through FSM validation helper boundaries.
- Preserve no-leak behavior and callback-secret authentication behavior.

### Library & Framework Requirements

- FastAPI route contracts and response status codes must match OpenAPI.
- Pydantic schemas must match callback request/replay/conflict payload shapes.
- Reuse existing `ApiError` and structured error-schema patterns; avoid ad-hoc envelopes.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/routes/internal.py`
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/internal.py`
- `apps/api/app/schemas/error.py`
- `apps/api/app/main.py` (only if runtime OpenAPI callback `409` schema shaping needs alignment)
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py` and/or a dedicated callback-focused test module

### Testing Requirements

- Validate first accepted callback persists idempotency record and returns `204`.
- Validate identical callback replay returns `200` with `replayed=true` and does not duplicate side effects.
- Validate payload mismatch for duplicate key returns `409 EVENT_ID_PAYLOAD_MISMATCH` and no mutation.
- Validate out-of-order and equal-timestamp callbacks return `409 CALLBACK_OUT_OF_ORDER` with required detail fields.
- Validate callback conflict/replay paths preserve no-mutation invariants (state, manifests/failure metadata, write counters).
- Validate runtime `/openapi.json` callback path remains contract-compliant (`200/204/401/404/409` and `409` oneOf schemas).
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 1.4 required multiple follow-up iterations to align callback request/response contracts and strict ordering semantics; preserve that alignment and avoid regression.
- Story 3.1 standardized FSM transition error behavior and side-effect safety on rejected transitions; callback flow must reuse the same invariant boundary.
- Prior stories found runtime OpenAPI drift quickly; validate callback `409` schema mapping after any route/service changes.

### Git Intelligence Summary

- Recent commit sequence establishes callback and FSM foundation:
- `484cbfe` Story 1.4 callback-secret + callback processing contract alignment
- `b718e6c` Story 2.2 run idempotency/dispatch safety
- Story 3.2 should focus narrowly on callback idempotency/order guarantees and side-effect invariants without unrelated refactors.

### Project Structure Notes

- No standalone `architecture.md` artifact exists in `_bmad-output/planning-artifacts/`; derive constraints from OpenAPI, FSM spec, PRD, acceptance tasks, and existing implementation patterns.
- Maintain current `apps/api/app/{routes,services,repositories,schemas}` and `apps/api/tests` organization.

### References

- `spec/api/openapi.yaml` (`StatusCallbackRequest`, `StatusCallbackReplayResponse`, callback conflict schemas, `/internal/jobs/{jobId}/status`)
- `spec/domain/job_fsm.md` (Sections 3.2 idempotency, 8 callback payload requirements, 9 FSM acceptance tests)
- `spec/acceptance/tasks_codex_v1.md` (Task 07 callback idempotency + ordering + atomicity)
- `_bmad-output/planning-artifacts/epics.md` (Epic 3, Story 3.2)
- `_bmad-output/planning-artifacts/prd.md` (FR-012, FR-013, FR-014; callback/idempotency requirements)
- `_bmad-output/project-context.md` (FSM/idempotency architectural invariants)
- `_bmad-output/implementation-artifacts/1-4-validate-internal-callback-secret.md`
- `_bmad-output/implementation-artifacts/3-1-enforce-fsm-transition-rules-and-lifecycle-invariants.md`

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

- Created Story 3.2 artifact with acceptance-criteria-mapped tasks and callback contract guardrails.
- Added implementation guidance focused on idempotency identity, replay/mismatch handling, strict ordering, and no-mutation invariants.
- Verified callback processing already satisfies Story 3.2 contract semantics for first-accept idempotency storage, replay no-op behavior, payload mismatch conflict, and strict monotonic ordering conflicts.
- Added callback API regression assertions proving replay/mismatch/out-of-order paths produce no additional mutations (`status`, `updated_at`, callback event map, latest callback timestamp, write counters).
- Verification completed in `apps/api` on 2026-02-26: `make lint`, `make test`, and `make check` all passed.

### File List

- `_bmad-output/implementation-artifacts/3-2-validate-callback-contract-idempotency-and-ordering-policy.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `apps/api/tests/test_auth_middleware.py`

### Change Log

- 2026-02-26: Created Story 3.2 artifact with AC-mapped implementation tasks and moved story status to `ready-for-dev`.
- 2026-02-26: Started Story 3.2 development workflow and moved sprint tracking to `in-progress`.
- 2026-02-26: Added callback no-mutation regression assertions for replay/conflict paths, ran `make lint`, `make test`, and `make check`, and moved story to `review`.
- 2026-02-26: Senior code review completed with approval; story moved to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-02-26

### Outcome

- Approved

### Summary

- Acceptance criteria validation passed: callback idempotency storage, replay no-op semantics, payload-mismatch conflict behavior, and strict non-monotonic ordering rejection are implemented and covered by tests.
- Source-level review found no High or Medium defects in the Story 3.2 implementation scope.
- Story claims and implementation evidence align for source changes, and required quality gates were executed successfully.

### Severity Breakdown

- High: 0
- Medium: 0
- Low: 0

### Action Items

- None.
