# Story 13.2: Persist Idempotency, Callback Ledger, and Audit Events

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a platform team,
I want callback replay protection and audit trails stored durably,
so that workflow safety and traceability survive restarts and multi-instance execution.

## Acceptance Criteria

1. Given a workflow callback is replayed with the same `event_id`, when the API processes it after a restart or on another instance, then the duplicate is still treated as a no-op.
2. Given status transitions and export or regenerate side effects occur, when the operation completes, then audit events are stored durably and remain queryable for investigations.
3. Given callback ordering or payload conflicts occur, when they are rejected, then the rejection reason is preserved without corrupting domain state.

## Tasks / Subtasks

- [ ] Persist callback event records, latest-applied markers, and idempotency keys in durable storage.
- [ ] Persist status-transition and side-effect audit events with safe identifiers.
- [ ] Preserve rollback semantics around callback mutation failures.
- [ ] Ensure terminal-state immutability and FSM rules remain enforced.
- [ ] Add restart-safe and multi-instance callback replay tests.

## Dev Notes

### Developer Context Section

- The current callback and audit semantics are strong, but they live inside the in-memory scaffold.
- This story should move the callback ledger and audit trail to durable storage without weakening ordering or rollback rules.
- It depends on the persistent repository groundwork from Story 13.1.

### Technical Requirements

- All job lifecycle transitions must still route through `ensure_transition`.
- Duplicate callbacks must remain no-op and conflicting replays must remain detectable.
- Audit logs must avoid secrets and raw transcript leakage.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/repositories/`
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/app/services/jobs.py`
- `apps/api/tests/`

### Testing Requirements

- Verify replay protection after repository reinitialization or process restart.
- Verify payload mismatch, ordering rejection, and rollback behavior still hold.
- Verify audit persistence covers status transitions and stateful side effects.

### References

- `apps/api/app/services/internal_callbacks.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `AGENTS.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `apps/api/app/services/internal_callbacks.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`

### Completion Notes List

- 2026-04-05: Created Story 13.2 artifact for durable idempotency, callback-ledger, and audit-event persistence.

### File List

- `_bmad-output/implementation-artifacts/13-2-persist-idempotency-callback-ledger-and-audit-events.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 13.2 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
