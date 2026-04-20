# Story 6.6: Emit Canonical Export Audit Events

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a compliance stakeholder,
I want export actions auditable end-to-end,
so that export lifecycle is traceable and policy-compliant.

## Acceptance Criteria

1. Given export lifecycle events occur, when audit events are emitted, then event types are exactly `EXPORT_REQUESTED`, `EXPORT_STARTED`, `EXPORT_SUCCEEDED`, and `EXPORT_FAILED` and each includes `export_id` and export identity key plus required audit metadata.
2. Given request or processing is idempotent replay with no new business transition, when audit is evaluated, then duplicate idempotent business events are suppressed.

## Tasks / Subtasks

- [x] Introduce canonical export-audit persistence in repository boundaries (AC: 1, 2)
- [x] Add deterministic in-memory `ExportAuditRecord` structure aligned to required `ExportAuditEvent` metadata fields.
- [x] Add `export_audit_events` storage and write counter tracking for export-audit emissions.
- [x] Add helper utilities for recording audit events with server-side `recorded_at` and safe correlation-id fallback.
- [x] Emit canonical export audit events only on new business transitions (AC: 1)
- [x] Emit `EXPORT_REQUESTED` when a new export request is persisted.
- [x] Emit `EXPORT_STARTED` only on accepted `REQUESTED -> RUNNING` transitions.
- [x] Emit `EXPORT_SUCCEEDED` only on accepted `RUNNING -> SUCCEEDED` transitions.
- [x] Emit `EXPORT_FAILED` only on accepted `RUNNING -> FAILED` transitions.
- [x] Ensure callback-driven export transitions preserve callback `occurred_at` and `correlation_id` in emitted export-audit records.
- [x] Suppress duplicate events for idempotent replays/no-op paths (AC: 2)
- [x] Ensure idempotent request replay (`POST /jobs/{jobId}/exports` returning existing export) emits no duplicate `EXPORT_REQUESTED`.
- [x] Ensure replayed processing transitions (`start/success/failure` replays and callback replay path) emit no duplicate business audit events.
- [x] Preserve transactional rollback semantics so failed callback mutation does not leave partial export-audit side effects.
- [x] Add AC-mapped tests and run quality gates (AC: 1, 2)
- [x] Add repository/service tests asserting required export-audit fields and canonical event-type sequence per export lifecycle.
- [x] Add tests asserting replay/no-op paths suppress duplicate export business audit events.
- [x] Add callback transaction test assertions covering export-audit emission + replay suppression.
- [x] Run `make lint`, `make test`, and `make check` in `apps/api`.

## Dev Notes

### Developer Context Section

- Story 6.1 introduced deterministic export identity and request idempotency behavior.
- Story 6.3 introduced export FSM execution semantics (`REQUESTED -> RUNNING -> SUCCEEDED|FAILED`) and deferred canonical audit stream expansion to this story.
- Story 6.4 introduced owner-scoped export status retrieval, and Story 6.5 introduced signed download URL issuance policy.
- Story 6.6 scope is export-audit event emission only; avoid endpoint/contract expansion unless already defined in OpenAPI.

### Technical Requirements

- Canonical event types are fixed: `EXPORT_REQUESTED`, `EXPORT_STARTED`, `EXPORT_SUCCEEDED`, `EXPORT_FAILED`.
- Required metadata must include at least:
- `event_type`
- `export_id`
- `identity_key`
- `occurred_at`
- `recorded_at` (server-generated)
- `correlation_id`
- Idempotent replay/no-op paths must not append duplicate business events.
- Export transition rules remain governed by existing export FSM and replay semantics.

### Architecture Compliance

- Keep `spec/` read-only.
- Keep route handlers thin and preserve existing service/repository layering.
- Preserve current API contract response codes/fields for export endpoints.
- Preserve callback transactional consistency and rollback guarantees.
- Ensure no secret/raw transcript data is introduced into audit payloads.

### Library & Framework Requirements

- FastAPI + Pydantic remain contract authority.
- Reuse existing in-memory audit-event persistence patterns from transition/regenerate audit implementations.
- No new dependencies expected.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/repositories/memory.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_internal_callback_transactions.py`
- `apps/api/tests/test_auth_middleware.py` (contract assertions if needed)

### Testing Requirements

- Validate canonical export audit-event sequence for new export request and execution transitions.
- Validate required export-audit fields are populated and structurally correct.
- Validate request/processing idempotent replay paths append no duplicate business events.
- Validate callback mutation replay path does not duplicate export audit events.
- Final verification gate: `make lint`, `make test`, and `make check` in `apps/api`.

### Previous Story Intelligence

- Story 6.3 set `last_audit_event` per export state transition; Story 6.6 extends this to canonical event persistence rather than state-only marker updates.
- Existing callback transaction tests already validate export state/idempotency behavior and are ideal anchor points for audit stream assertions.

### Git Intelligence Summary

- Export behavior is centralized in `JobService` and `InMemoryStore`; implement audit emission in repository transition boundaries to avoid duplicate logic.
- Keep diffs focused to minimize risk in already-stable Epic 6 flows.

### Project Structure Notes

- No standalone architecture artifact in planning outputs; derive constraints from OpenAPI, PRD, epics, and existing implementation patterns.
- Keep Story 6.6 scoped to canonical export-audit event emission and replay suppression guarantees.

### References

- `spec/api/openapi.yaml` (`ExportAuditEventType`, `ExportAuditEvent`, `/jobs/{jobId}/exports`)
- `spec/acceptance/tasks_codex_v1.md` (Task 15 idempotent replay and no duplicate business audit events)
- `_bmad-output/planning-artifacts/epics.md` (Epic 6, Story 6.6)
- `_bmad-output/planning-artifacts/prd.md` (FR-030 export auditability)
- `_bmad-output/implementation-artifacts/6-1-create-export-request-bound-to-exact-instruction-version.md`
- `_bmad-output/implementation-artifacts/6-3-execute-export-fsm-and-freeze-provenance-on-success.md`
- `_bmad-output/implementation-artifacts/6-4-retrieve-export-status-by-export-id.md`
- `_bmad-output/implementation-artifacts/6-5-issue-strictly-scoped-signed-download-url.md`
- `apps/api/app/repositories/memory.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_internal_callback_transactions.py`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/planning-artifacts/epics.md`
- `spec/api/openapi.yaml`
- `spec/acceptance/tasks_codex_v1.md`
- `_bmad-output/planning-artifacts/prd.md`
- `apps/api/app/repositories/memory.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_internal_callback_transactions.py`

### Completion Notes List

- 2026-03-04: Created Story 6.6 artifact from sprint backlog with AC-mapped tasks for canonical export audit-event emission and replay suppression.
- 2026-03-04: Implemented canonical export-audit persistence in `InMemoryStore` with `ExportAuditRecord`, `export_audit_events`, and `export_audit_write_count`.
- 2026-03-04: Emitted `EXPORT_REQUESTED|EXPORT_STARTED|EXPORT_SUCCEEDED|EXPORT_FAILED` only on accepted business transitions, with callback-aware `occurred_at`/`correlation_id` propagation and server-generated `recorded_at`.
- 2026-03-04: Added rollback protection for export-audit side effects in callback transaction failure paths.
- 2026-03-04: Added replay-suppression regression coverage for request/execution/callback replay paths.
- 2026-03-04: Verified `make lint`, `make test`, and `make check` in `apps/api` (all passing; `196` tests).
- 2026-03-05: Final code review found no remaining defects in Story 6.6 scope; quality gates remained green and story moved to `done`.

### File List

- `_bmad-output/implementation-artifacts/6-6-emit-canonical-export-audit-events.md`
- `apps/api/app/repositories/memory.py`
- `apps/api/tests/test_jobs_ownership.py`
- `apps/api/tests/test_internal_callback_transactions.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-03-04: Created Story 6.6 artifact and moved sprint status from `backlog` to `ready-for-dev`.
- 2026-03-04: Implemented canonical export-audit event emission and replay suppression with AC-mapped regression tests.
- 2026-03-04: Ran `make lint`, `make test`, and `make check` in `apps/api` and moved story/sprint status to `review`.
- 2026-03-05: Final re-review approved with no remaining findings; story/sprint status moved to `done`.

## Senior Developer Review (AI)

### Reviewer

- `Codex` (AI Senior Developer Reviewer)
- Date: 2026-03-05

### Outcome

- Approved

### Findings Summary

- High: 0
- Medium: 0
- Low: 0

### Findings

- No defects identified in Story 6.6 scope.

### Verification

- `make lint` passed.
- `make test` passed (`198` tests).
- `make check` passed.

### Residual Risk

- Low residual operational risk (future environment/config drift); current automated coverage for export-audit sequence, required metadata, replay suppression, and callback rollback behavior is in place.
