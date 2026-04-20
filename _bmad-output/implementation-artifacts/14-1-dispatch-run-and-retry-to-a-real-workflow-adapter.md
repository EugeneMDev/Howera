# Story 14.1: Dispatch Run and Retry to a Real Workflow Adapter

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a backend team,
I want `run` and `retry` to dispatch through a real workflow adapter,
so that job execution leaves the scaffold and reaches the chosen orchestration runtime.

## Acceptance Criteria

1. Given a job is eligible for `run` or `retry`, when the API accepts the request, then a real workflow dispatch is emitted through an isolated adapter rather than only an in-memory record.
2. Given dispatch metadata is created, when the request completes, then the system stores enough information to correlate later callbacks, retries, and failures durably.
3. Given the workflow adapter is unavailable, when dispatch fails, then the API returns the defined failure contract without mutating state incorrectly.

## Tasks / Subtasks

- [ ] Define the workflow adapter interface and isolate external dispatch logic behind it.
- [ ] Implement real `run` and `retry` dispatch for the selected workflow runtime.
- [ ] Persist dispatch metadata and callback correlation inputs durably.
- [ ] Preserve FSM gating and no-op replay behavior around run and retry requests.
- [ ] Add tests for successful dispatch, adapter failure, and replay-safe behavior.

## Dev Notes

### Developer Context Section

- Current dispatch behavior only creates a `WorkflowDispatchRecord` in memory and does not call a real orchestrator.
- This story should be the first true execution bridge from API lifecycle actions to workflow infrastructure.
- It depends on persistent storage and the configuration contract being in place.

### Technical Requirements

- Keep workflow integration behind an adapter boundary rather than inline API logic.
- Preserve `ensure_transition` and current lifecycle validation semantics.
- Ensure callback URLs, secrets, and correlation identifiers are included safely.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/services/jobs.py`
- workflow adapter modules
- `apps/api/app/repositories/`
- `apps/api/tests/`

### Testing Requirements

- Verify accepted dispatches reach the workflow adapter with the expected payload.
- Verify dispatch failures do not leave partially advanced job state.
- Verify replay and retry semantics stay consistent.

### References

- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `.env.example`
- `AGENTS.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `apps/api/app/services/jobs.py`
- `apps/api/app/repositories/memory.py`
- `.env.example`

### Completion Notes List

- 2026-04-05: Created Story 14.1 artifact for real workflow dispatch through an isolated adapter.

### File List

- `_bmad-output/implementation-artifacts/14-1-dispatch-run-and-retry-to-a-real-workflow-adapter.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 14.1 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
