# Story 14.3: Add Retry, Backoff, and Dead-Letter Controls for Workflow Failures

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want bounded retry and failure-isolation controls for workflow dispatch and callback problems,
so that transient issues recover automatically and stuck executions are visible instead of silent.

## Acceptance Criteria

1. Given a workflow dispatch or callback delivery fails transiently, when retry policy applies, then retries follow bounded backoff rather than unbounded repeated attempts.
2. Given an execution exceeds retry or timeout policy, when recovery is no longer possible automatically, then the failure is surfaced through a durable dead-letter or equivalent operator-visible record.
3. Given jobs become stuck between accepted dispatch and terminal outcome, when operators inspect system state, then stale executions are distinguishable from healthy in-flight work.

## Tasks / Subtasks

- [ ] Define retry policy, timeout thresholds, and failure escalation rules for dispatch and callback paths.
- [ ] Persist retry attempts, last-failure metadata, and terminal escalation state durably.
- [ ] Add dead-letter or equivalent failure isolation for executions requiring manual attention.
- [ ] Emit safe audit or telemetry signals for retry exhaustion and stuck-workflow detection.
- [ ] Add tests for transient recovery, retry exhaustion, and stale-execution detection.

## Dev Notes

### Developer Context Section

- Current dispatch failure handling is single-shot and returns an API error without an operational recovery model.
- This story should add production control loops around workflow reliability before the system relies on real providers.
- It depends on real workflow dispatch and durable callback processing being available.

### Technical Requirements

- Preserve API contract behavior for client-facing errors.
- Keep retry policy explicit and configurable.
- Avoid duplicate side effects when retries overlap with already-applied callbacks.

### File Structure Requirements

- Primary expected touch points:
- workflow adapter modules
- `apps/api/app/services/`
- `apps/api/app/repositories/`
- `apps/api/tests/`

### Testing Requirements

- Verify bounded retry and backoff behavior.
- Verify dead-letter or equivalent escalation occurs after exhaustion.
- Verify duplicate side effects are not introduced by retry logic.

### References

- `apps/api/app/services/jobs.py`
- `apps/api/app/services/internal_callbacks.py`
- `.env.example`
- `AGENTS.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `apps/api/app/services/jobs.py`
- `apps/api/app/services/internal_callbacks.py`
- `.env.example`

### Completion Notes List

- 2026-04-05: Created Story 14.3 artifact for workflow retry, backoff, and dead-letter operational controls.

### File List

- `_bmad-output/implementation-artifacts/14-3-add-retry-backoff-and-dead-letter-controls-for-workflow-failures.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 14.3 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
