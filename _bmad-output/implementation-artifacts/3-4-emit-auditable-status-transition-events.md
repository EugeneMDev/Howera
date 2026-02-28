# Story 3.4: Emit Auditable Status Transition Events

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a compliance stakeholder,
I want status transitions to produce auditable events,
so that job lifecycle decisions are traceable.

## Acceptance Criteria

1. Given any accepted state transition, when audit event is recorded, then event includes required fields: `event_type`, `job_id`, `project_id`, `actor_type`, `prev_status`, `new_status`, `occurred_at`, `recorded_at`, `correlation_id` and event payload excludes secrets and raw transcript content.
2. Given duplicate callback replay (no-op), when processed, then no duplicate transition audit event is emitted.

## Tasks / Subtasks

- [x] Introduce auditable transition-event persistence boundary for callback-applied transitions (AC: 1, 2)
- [x] Add a deterministic in-memory audit event record structure with required contract fields.
- [x] Add repository/store write path to persist transition audit events for accepted transitions.
- [x] Ensure `recorded_at` is generated server-side (UTC) and not trusted from callback payload.
- [x] Ensure accepted callback transition path emits exactly one transition audit record (AC: 1, 2)
- [x] Emit transition audit event only on first accepted callback mutation path (204 path).
- [x] Populate required fields from callback/job context: `event_type`, `job_id`, `project_id`, `actor_type`, `prev_status`, `new_status`, `occurred_at`, `recorded_at`, `correlation_id`.
- [x] Define deterministic `event_type` value and actor-type fallback behavior when callback `actor_type` is omitted.
- [x] Prevent duplicate audit events for replay/reject paths (AC: 2)
- [x] Ensure identical replay (`200` no-op) does not append any transition audit event.
- [x] Ensure payload mismatch, out-of-order, and FSM-invalid/terminal callbacks append no transition audit event.
- [x] Preserve callback contract and existing idempotency/order semantics (AC: 1, 2)
- [x] Preserve `/internal/jobs/{jobId}/status` response contract (`200/204/401/404/409`) and existing schema behavior.
- [x] Preserve callback-secret/no-leak behavior and secure logging boundaries.
- [x] Ensure audit payload does not include secrets, callback secret value, transcript text, prompt text, or raw artifact payload blobs.
- [x] Add AC-mapped regression tests and execute quality gates (AC: 1, 2)
- [x] Add tests for accepted callback transition audit event creation with required fields and expected values.
- [x] Add tests proving replay no-op does not emit duplicate transition audit events.
- [x] Add tests proving mismatch/out-of-order/FSM-invalid callbacks do not emit transition audit events.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Story 3.1 centralized FSM transition enforcement boundaries and no-mutation behavior for rejected transitions.
- Story 3.2 hardened callback idempotency, payload mismatch handling, and strict monotonic callback ordering.
- Story 3.3 added transactional consistency for state + manifest + failure metadata, including rollback semantics and raw artifact merge safety.

### Technical Requirements

- Endpoint in scope remains `POST /internal/jobs/{jobId}/status`.
- For accepted transitions, emit one transition audit record containing required fields from `AuditEvent` schema and callback endpoint description:
  - `event_type`
  - `job_id`
  - `project_id`
  - `actor_type` (`editor`/`orchestrator`/`system`; callback path should resolve to an allowed value)
  - `prev_status`
  - `new_status`
  - `occurred_at`
  - `recorded_at`
  - `correlation_id`
- Replay semantics must stay unchanged:
  - First accepted callback -> `204`
  - Identical replay -> `200` no-op
  - Payload mismatch -> `409 EVENT_ID_PAYLOAD_MISMATCH`
  - Out-of-order/equal timestamp -> `409 CALLBACK_OUT_OF_ORDER`
- Transition audit records must not be emitted for replay no-op or rejection paths.
- Audit payload and logs must exclude secrets and raw transcript/prompt content.

### Architecture Compliance

- `spec/` remains read-only source of truth.
- Keep route handlers thin; callback transition/audit behavior belongs in service/repository boundaries.
- Preserve centralized FSM enforcement via `domain/job_fsm.ensure_transition`.
- Preserve existing callback idempotency/order semantics from Story 3.2 and transactional mutation boundaries from Story 3.3.
- Preserve no-leak behavior and callback-secret authentication constraints.

### Library & Framework Requirements

- FastAPI + Pydantic schemas remain contract authority.
- Reuse existing `ApiError` and structured error schema patterns.
- No new external dependencies are expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_internal_callback_transactions.py` and/or a dedicated callback audit test module
- `apps/api/app/schemas/error.py` (only if contract-safe error-shape alignment needs adjustment)
- `apps/api/app/main.py` (only if runtime OpenAPI shaping requires a targeted update)

### Testing Requirements

- Validate accepted callback transition emits one transition audit event with all required fields.
- Validate replay no-op does not emit duplicate transition audit events.
- Validate mismatch/out-of-order/FSM-invalid callbacks emit no transition audit events.
- Validate callback response contract remains unchanged (`200/204/401/404/409`) and existing replay/order/idempotency tests continue to pass.
- Validate audit payload does not contain secret/callback-secret/transcript/prompt leakage.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 3.2 already provides strong no-side-effect assertions for replay and rejection paths; audit writes must follow the same invariants.
- Story 3.3 introduced transactional callback mutation boundaries; transition audit emission should align with accepted transition application semantics and rollback expectations.
- Prior stories show openapi response-shape drift is caught quickly; do not change callback route contract without spec change.

### Git Intelligence Summary

- Recent repository commits established callback/run foundations:
- `b718e6c` `2-2-start-workflow-run-for-an-upload-confirmed-job`
- `484cbfe` `1-4-validate-internal-callback-secret`
- Story 3.4 should remain narrowly scoped to auditable transition-event emission behavior on accepted callback transitions.

### Project Structure Notes

- No standalone `architecture.md` exists in `_bmad-output/planning-artifacts/`; derive implementation guardrails from OpenAPI, FSM spec, acceptance tasks, and completed Story 3 artifacts.
- Keep diffs minimal and localized to callback service/repository/tests.

### References

- `spec/api/openapi.yaml` (`AuditEvent` schema and `/internal/jobs/{jobId}/status` transition-audit requirements)
- `spec/domain/job_fsm.md` (callback payload and lifecycle invariants)
- `spec/acceptance/tasks_codex_v1.md` (Task 07 transition-audit expectation)
- `_bmad-output/planning-artifacts/epics.md` (Epic 3, Story 3.4)
- `_bmad-output/planning-artifacts/prd.md` (FR-029 and auditability goals)
- `_bmad-output/implementation-artifacts/3-1-enforce-fsm-transition-rules-and-lifecycle-invariants.md`
- `_bmad-output/implementation-artifacts/3-2-validate-callback-contract-idempotency-and-ordering-policy.md`
- `_bmad-output/implementation-artifacts/3-3-transactional-consistency-for-state-manifest-and-failure-metadata.md`
- `apps/api/app/services/internal_callbacks.py`
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
- `_bmad-output/implementation-artifacts/3-2-validate-callback-contract-idempotency-and-ordering-policy.md`
- `_bmad-output/implementation-artifacts/3-3-transactional-consistency-for-state-manifest-and-failure-metadata.md`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_internal_callback_transactions.py`

### Completion Notes List

- Added `TransitionAuditRecord` and `transition_audit_events` persistence to the in-memory repository boundary for accepted callback transitions.
- Extended callback transactional mutation flow to append exactly one transition audit event on first accepted callback (`204` path), including required fields (`event_type`, `job_id`, `project_id`, `actor_type`, `prev_status`, `new_status`, `occurred_at`, `recorded_at`, `correlation_id`).
- Added deterministic actor-type fallback (`system`) when callback `actor_type` is omitted and deterministic event type value (`JOB_STATUS_TRANSITION_APPLIED`).
- Confirmed replay and rejection paths emit no transition audit events (`replay`, `payload mismatch`, `out-of-order`, and FSM-invalid/terminal rejection scenarios).
- Added regression assertions for transition audit semantics in callback API and transactional test suites.
- Verification completed in `apps/api`: `make lint`, `make test`, and `make check` all passed.

### File List

- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_internal_callback_transactions.py`
- `_bmad-output/implementation-artifacts/3-4-emit-auditable-status-transition-events.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-02-27: Created Story 3.4 artifact with AC-mapped implementation tasks and moved story status to `ready-for-dev`.
- 2026-02-27: Started Story 3.4 dev workflow and moved sprint tracking to `in-progress`.
- 2026-02-27: Implemented callback transition-audit emission with required fields, added no-duplicate/no-reject audit regression assertions, ran `make lint`, `make test`, and `make check`, and moved story to `review`.
- 2026-02-28: Completed code review follow-up fixes (terminal callback no-audit regression, actor-type passthrough verification, UTC `recorded_at` assertion, and sensitive-field exclusion audit assertions), reran `make lint`, `make test`, and `make check`, and moved story to `done`.

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

- [x] [MEDIUM] Missing regression to prove terminal-state callback rejection emits no transition audit event side effects.
  - Fix: Added terminal callback rejection regression with no-side-effect assertions.
  - Evidence: `apps/api/tests/test_auth_middleware.py` (`test_callback_from_terminal_state_returns_409_without_side_effects`)
- [x] [MEDIUM] Audit event timestamp test did not assert UTC semantics for server-generated `recorded_at`.
  - Fix: Added UTC timezone assertion for `recorded_at`.
  - Evidence: `apps/api/tests/test_internal_callback_transactions.py` (`test_callback_applies_transactional_status_manifest_and_failure_updates`)
- [x] [MEDIUM] Audit regression suite did not explicitly verify actor passthrough and exclusion of raw transcript/prompt callback fields from persisted transition audit payload.
  - Fix: Added dedicated actor passthrough and sensitive-field exclusion tests.
  - Evidence: `apps/api/tests/test_internal_callback_transactions.py` (`test_callback_transition_audit_keeps_supplied_actor_type`, `test_transition_audit_payload_excludes_sensitive_callback_payload_fields`)
