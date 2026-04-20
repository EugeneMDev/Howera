# Story 14.2: Process Status Callbacks Transactionally on Persistent State

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a platform team,
I want workflow status callbacks applied transactionally against persistent state,
so that retries, artifacts, and failure metadata remain consistent under real execution.

## Acceptance Criteria

1. Given a valid callback arrives, when it is processed, then the status transition, artifact updates, failure metadata, and callback ledger changes commit atomically.
2. Given a callback would violate ordering, payload, or FSM rules, when it is rejected, then persisted state remains unchanged and the rejection is traceable.
3. Given a callback mutation fails partway through, when the system rolls back, then no partial state escapes to later reads.

## Tasks / Subtasks

- [ ] Implement transactional callback processing over the persistent repository layer.
- [ ] Persist artifact updates, failure metadata, and audit events within the same mutation boundary.
- [ ] Preserve ordering, payload-signature, and replay protections on the durable path.
- [ ] Add failure-injection tests to validate rollback semantics.
- [ ] Ensure retry checkpoint logic still works for callbacks accepted after failed jobs.

## Dev Notes

### Developer Context Section

- The current in-memory callback mutation code already models rollback and ordering carefully.
- This story should preserve that behavior while moving execution to the durable runtime path.
- It depends on Stories 13.2 and 14.1 to provide persistent ledgers and real dispatch metadata.

### Technical Requirements

- Route all lifecycle status changes through `ensure_transition`.
- Keep terminal states immutable.
- Preserve checkpoint-aware retry handling and artifact-manifest consistency.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/services/internal_callbacks.py`
- `apps/api/app/repositories/`
- `apps/api/tests/`

### Testing Requirements

- Verify atomic callback application and rollback on injected failures.
- Verify ordering and replay rejection behavior after persistence migration.
- Verify transcript, export, and failure metadata stay consistent after callback application.

### References

- `apps/api/app/services/internal_callbacks.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/domain/job_fsm.py`
- `AGENTS.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `apps/api/app/services/internal_callbacks.py`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/domain/job_fsm.py`

### Completion Notes List

- 2026-04-05: Created Story 14.2 artifact for transactional callback processing on persistent state.

### File List

- `_bmad-output/implementation-artifacts/14-2-process-status-callbacks-transactionally-on-persistent-state.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 14.2 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
