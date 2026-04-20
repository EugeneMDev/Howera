# Story 16.2: Add Structured Logging, Metrics, and Tracing Controls

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want structured observability controls,
so that production incidents can be diagnosed without leaking sensitive content.

## Acceptance Criteria

1. Given requests, jobs, and callbacks flow through the system, when logs are emitted, then they include safe correlation identifiers and structured metadata instead of ad hoc text-only output.
2. Given operators need runtime insight, when metrics and tracing are enabled, then core latency, failure, and workflow-health signals become observable without exposing secrets or transcript content.
3. Given observability features are disabled or unavailable, when the system runs, then application behavior remains safe and predictable.

## Tasks / Subtasks

- [ ] Define a structured logging schema for request, job, callback, and artifact events.
- [ ] Add metrics instrumentation for key backend and workflow paths.
- [ ] Add optional tracing hooks aligned with the chosen deployment stack.
- [ ] Ensure safe logging redaction rules remain enforced for identifiers and payload content.
- [ ] Add tests or verification for observability enablement and redaction behavior.

## Dev Notes

### Developer Context Section

- The repository already includes safe identifier helpers and frontend telemetry redaction, but backend observability is not yet production-grade.
- This story should turn scattered logs into an explicit operational surface.
- It depends on runtime packaging and production topology decisions being established first.

### Technical Requirements

- Never log secrets, raw transcripts, or signed URLs.
- Keep observability controls environment-driven.
- Preserve low-friction local development when metrics or tracing are disabled.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/`
- observability configuration files if needed
- `apps/api/tests/`
- `docs/dev-setup.md`

### Testing Requirements

- Verify logs use the safe structured schema.
- Verify metrics and tracing toggles behave deterministically.
- Verify sensitive content remains redacted or omitted.

### References

- `apps/api/app/core/logging_safety.py`
- `apps/api/app/services/internal_callbacks.py`
- `.env.example`
- `AGENTS.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `apps/api/app/core/logging_safety.py`
- `apps/api/app/services/internal_callbacks.py`
- `.env.example`

### Completion Notes List

- 2026-04-05: Created Story 16.2 artifact for structured logging, metrics, and tracing controls.

### File List

- `_bmad-output/implementation-artifacts/16-2-add-structured-logging-metrics-and-tracing-controls.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 16.2 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
