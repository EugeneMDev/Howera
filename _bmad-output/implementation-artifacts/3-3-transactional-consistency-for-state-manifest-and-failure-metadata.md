# Story 3.3: Transactional Consistency for State, Manifest, and Failure Metadata

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want callback side effects to be state-consistent,
so that artifact records and status remain aligned.

## Acceptance Criteria

1. Given callback mutation includes status, manifest updates, and optional failure metadata, when persisted, then state change, `artifact_manifest` merge, and failure fields are committed in one transaction and any write failure rolls back all three.
2. Given manifest update is applied, when merge executes, then update is merge-safe (keyed merge with no destructive overwrite of unrelated keys) and immutable raw artifact entries are never replaced or deleted implicitly.

## Tasks / Subtasks

- [x] Implement a transactional callback mutation boundary for status + side effects (AC: 1)
- [x] Introduce a single repository/service mutation boundary that applies callback status transition, manifest changes, and failure metadata atomically.
- [x] Ensure callback side effects are committed only after FSM transition validation succeeds.
- [x] Ensure any failure in side-effect persistence produces rollback/no-op behavior for status, manifest, and failure metadata together.
- [x] Add explicit failure-injection test path for transaction rollback semantics (AC: 1)
- [x] Add/store a deterministic failpoint in test scaffolding to simulate write failure during callback side-effect persistence.
- [x] Validate rollback behavior keeps prior `status`, `updated_at`, `artifact_manifest`, and failure fields unchanged when failpoint triggers.
- [x] Enforce merge-safe artifact update behavior (AC: 2)
- [x] Apply keyed merge semantics for `artifact_updates`: only provided keys are updated, unrelated manifest keys are preserved.
- [x] Ensure absent keys never null out existing manifest values.
- [x] Ensure immutable raw artifact entries (`video_uri`, `audio_uri`, `transcript_uri`) are not replaced/deleted by callback merge logic.
- [x] Define deterministic handling for unsupported/unknown `artifact_updates` keys (ignore or reject) without destructive side effects.
- [x] Apply failure metadata persistence rules (AC: 1, 2)
- [x] Persist `failure_code`, `failure_message`, and `failed_stage` consistently for relevant callback outcomes.
- [x] Ensure non-failure callbacks do not accidentally erase existing failure metadata unless explicitly policy-allowed and tested.
- [x] Keep callback contract and route behavior aligned (AC: 1, 2)
- [x] Preserve callback route response contract (`200/204/401/404/409`) and existing idempotency/order semantics from Story 3.2.
- [x] Preserve no-leak and callback-secret behavior from prior stories.
- [x] Add AC-mapped tests and run quality gates (AC: 1, 2)
- [x] Add regression tests for transactional success and rollback, merge-safe manifest updates, immutable raw key protection, and failure metadata consistency.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Story 3.1 centralized FSM transition enforcement boundaries.
- Story 3.2 completed callback idempotency, replay mismatch protection, and ordering rules.
- Current callback implementation persists callback event/timestamp after status transition but does not yet apply transactional manifest/failure metadata updates from `artifact_updates` and failure fields.

### Technical Requirements

- Endpoint in scope remains `POST /internal/jobs/{jobId}/status`.
- Callback processing must preserve existing idempotency/order semantics while extending atomic side-effect handling.
- State transition + manifest merge + failure metadata must behave transactionally.
- Manifest merge must be keyed and non-destructive for unrelated keys.
- Raw artifact entries (`video_uri`, `audio_uri`, `transcript_uri`) are immutable under callback merge operations.
- Write failure on any callback side-effect step must roll back status/manifest/failure metadata updates as a single unit.

### Architecture Compliance

- `spec/` remains read-only source of truth.
- All status transitions continue through `domain/job_fsm.ensure_transition`.
- Keep route handlers thin; transaction logic belongs in service/repository boundary.
- Preserve contract-first response codes/payload shapes and no-leak behavior.

### Library & Framework Requirements

- FastAPI + Pydantic schemas remain contract authority.
- Reuse `ApiError` patterns; avoid ad-hoc error envelopes.
- No new external dependency expected for this story.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/schemas/job.py` (only if failure metadata storage model needs extension)
- `apps/api/app/routes/internal.py` (only if response behavior requires contract-safe adjustment)
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py` and/or dedicated callback transactional test module

### Testing Requirements

- Validate successful callback mutation persists transition + manifest merge + failure metadata consistently.
- Validate injected write failure rolls back all callback mutation side effects.
- Validate merge-safe behavior preserves unrelated manifest keys.
- Validate immutable raw artifact keys cannot be replaced/deleted via callback merge updates.
- Validate replay/mismatch/out-of-order semantics from Story 3.2 remain unchanged.
- Validate runtime `/openapi.json` callback contract remains aligned.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 3.2 already enforces callback idempotency/order and added strong no-side-effect assertions for replay/reject paths; do not regress these guarantees.
- Story 3.1 now enforces self-transition rules via FSM table and has callback no-side-effect regression for invalid transitions; preserve this behavior while adding transactional side effects.
- Prior stories show contract drift is caught quickly by openapi tests; keep callback `409` schema mapping untouched unless spec requires change.

### Git Intelligence Summary

- Recent Story 3 sequence is incremental and state-safety focused:
- `3.1` FSM invariants and transition enforcement
- `3.2` callback idempotency/order hardening
- `3.3` should stay narrowly scoped to transactional side-effect consistency and merge policy.

### Project Structure Notes

- No standalone `architecture.md` exists in planning artifacts; derive implementation guardrails from OpenAPI, FSM spec, PRD, acceptance tasks, and completed Story 3 artifacts.
- Keep diffs minimal and localized to callback service/repository/tests.

### References

- `spec/api/openapi.yaml` (`/internal/jobs/{jobId}/status` callback description with transactional/merge requirements)
- `spec/domain/job_fsm.md` (FSM transition rules and callback invariants)
- `spec/acceptance/tasks_codex_v1.md` (Task 07 transactional callback expectation)
- `_bmad-output/planning-artifacts/epics.md` (Epic 3, Story 3.3)
- `_bmad-output/planning-artifacts/prd.md` (FR-015, FR-016)
- `_bmad-output/implementation-artifacts/3-1-enforce-fsm-transition-rules-and-lifecycle-invariants.md`
- `_bmad-output/implementation-artifacts/3-2-validate-callback-contract-idempotency-and-ordering-policy.md`
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
- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/tests/test_internal_callback_transactions.py`
- `apps/api/tests/test_auth_middleware.py`

### Completion Notes List

- Added `InMemoryStore.apply_callback_mutation(...)` as a single atomic boundary for callback status, manifest merge, failure metadata, callback event persistence, and latest callback timestamp tracking.
- Added deterministic callback failpoint support (`callback_mutation_failpoint_event_id` + stage) with full rollback to prior `status`, `updated_at`, `artifact_manifest`, failure fields, callback event state, and write counters.
- Implemented keyed, non-destructive manifest merge semantics: immutable raw keys (`video_uri`, `audio_uri`, `transcript_uri`) support first-write but reject overwrite/delete, mutable known keys (`draft_uri`, `exports`) are updated, unknown keys are ignored, and `None` values do not clear existing data.
- Persisted failure metadata fields (`failure_code`, `failure_message`, `failed_stage`) only when supplied, preserving prior values on non-failure callbacks without explicit failure metadata.
- Added Story 3.3 regression tests for transactional success, failpoint rollback semantics across all failpoint stages, merge safety, immutable raw key protection, first-write raw artifact handling, and failure metadata behavior while preserving existing Story 3.2 idempotency/order contract tests.
- Ran code-review fixes for identified High/Medium issues and re-verified `apps/api` with `make lint`, `make test`, and `make check`.

### File List

- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/app/domain/job_fsm.py`
- `apps/api/app/services/jobs.py`
- `apps/api/tests/test_internal_callback_transactions.py`
- `apps/api/tests/test_auth_middleware.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_job_fsm.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/3-3-transactional-consistency-for-state-manifest-and-failure-metadata.md`

### Change Log

- 2026-02-26: Created Story 3.3 artifact with AC-mapped implementation tasks and moved story status to `ready-for-dev`.
- 2026-02-27: Implemented transactional callback mutation boundary with rollback-safe failpoint support, merge-safe artifact update policy, and AC-mapped regression coverage; moved story status to `review`.
- 2026-02-27: Senior code review completed; fixed raw artifact first-write handling and expanded rollback coverage; moved story status to `done`.

## Senior Developer Review (AI)

### Review Date

2026-02-27

### Reviewer

GPT-5.3-Codex

### Outcome

Approve

### Findings Summary

- 1 High and 2 Medium findings were identified and fixed in this review pass.

### Findings and Resolutions

- [x] [HIGH] Callback merge previously dropped `audio_uri` and `transcript_uri` updates, which prevented required raw artifact manifest persistence paths.
  - Fix: Added first-write semantics for immutable raw keys while still blocking overwrite/delete.
  - Evidence: `apps/api/app/repositories/memory.py` (`_merge_artifact_updates`)
- [x] [MEDIUM] Rollback failpoint validation covered only one stage.
  - Fix: Expanded rollback test to cover `after_status`, `after_manifest`, `after_failure_metadata`, and `after_callback_event`.
  - Evidence: `apps/api/tests/test_internal_callback_transactions.py` (`test_callback_failpoint_rolls_back_all_side_effects`)
- [x] [MEDIUM] Story file list did not reflect current modified source/test files in workspace.
  - Fix: Updated Dev Agent Record → File List to align with current tracked source/test changes.
