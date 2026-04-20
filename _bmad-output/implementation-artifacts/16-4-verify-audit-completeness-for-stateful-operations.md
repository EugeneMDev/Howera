# Story 16.4: Verify Audit Completeness for Stateful Operations

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a compliance-minded platform team,
I want audit coverage verified for stateful operations,
so that critical lifecycle, export, and regenerate actions remain explainable after production rollout.

## Acceptance Criteria

1. Given status transitions, exports, regenerate actions, and cleanup events occur, when audit completeness is reviewed, then each critical operation emits a durable audit record.
2. Given operator or incident review is required, when the audit trail is inspected, then records correlate safely to job, instruction, and artifact identifiers without leaking sensitive content.
3. Given gaps are discovered, when follow-up tasks are created or fixes land, then audit expectations are codified in tests.

## Tasks / Subtasks

- [ ] Define the required audit matrix for stateful operations.
- [ ] Compare current emitted events against that matrix and fill the missing coverage.
- [ ] Add tests that assert required audit emissions for critical operations.
- [ ] Verify audit storage and retrieval remain durable and safe.
- [ ] Document residual exclusions or intentionally unaudited paths if any remain.

## Dev Notes

### Developer Context Section

- The scaffold already models several audit events, but production rollout requires a complete and durable audit story.
- This story should turn audit expectations into an explicit verification gate.
- It depends on durable audit persistence and real workflow or artifact paths existing first.

### Technical Requirements

- Cover status transitions, exports, regenerate actions, and retention or cleanup where applicable.
- Keep audit payloads safe and correlation-friendly.
- Avoid logging secrets, signed URLs, or raw transcript bodies.

### File Structure Requirements

- Primary expected touch points:
- audit or repository modules
- `apps/api/tests/`
- operational docs if needed

### Testing Requirements

- Verify required audit events exist for the defined operation matrix.
- Verify audit records remain durable and queryable.
- Verify sensitive content is not stored in audit payloads.

### References

- `AGENTS.md`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/services/internal_callbacks.py`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `AGENTS.md`
- `apps/api/app/repositories/memory.py`
- `apps/api/app/services/jobs.py`
- `apps/api/app/services/internal_callbacks.py`

### Completion Notes List

- 2026-04-05: Created Story 16.4 artifact for audit-completeness verification of stateful operations.

### File List

- `_bmad-output/implementation-artifacts/16-4-verify-audit-completeness-for-stateful-operations.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 16.4 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
