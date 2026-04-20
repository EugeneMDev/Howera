# Story 17.2: Run Full-Stack Integration Pipeline Without Mock-Only Dependencies

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a delivery team,
I want a full-stack integration pipeline that exercises real stack components,
so that merge safety is not limited to mock-mode frontend and scaffold-level backend tests.

## Acceptance Criteria

1. Given the pipeline is executed, when the stack boots, then web, API, persistence, storage, and workflow components run together without relying solely on mocks.
2. Given the core user path is exercised, when tests run, then create, upload, run, callback, edit, screenshot or export, and secure retrieval cover at least one real end-to-end slice.
3. Given the pipeline fails, when diagnostics are emitted, then the failing layer or stage is clear enough to route ownership quickly.

## Tasks / Subtasks

- [ ] Define the minimum full-stack environment required for CI or staging integration.
- [ ] Add one or more integration tests that run against real stack components rather than mock-only APIs.
- [ ] Reuse or extend the local-stack smoke path for automation.
- [ ] Add actionable diagnostics for stack boot failures and stage-specific regressions.
- [ ] Document how to run the full-stack pipeline locally if supported.

## Dev Notes

### Developer Context Section

- The current frontend golden path is useful but still fully mocked.
- This story should become the first merge gate that proves real cross-stack behavior.
- It depends on runtime packaging, persistence, workflow execution, and at least one durable artifact pipeline.

### Technical Requirements

- Keep the integration slice small enough to remain reliable.
- Avoid external shared dependencies where deterministic local or ephemeral equivalents are possible.
- Preserve secure auth and signed-access handling on the real path.

### File Structure Requirements

- Primary expected touch points:
- integration test suites
- CI workflows
- local-stack bootstrap files
- `docs/golden-path.md`

### Testing Requirements

- Verify the pipeline exercises real cross-stack behavior.
- Verify diagnostics identify the failing layer or stage.
- Verify setup and teardown remain deterministic across repeated runs.

### References

- `docs/golden-path.md`
- `.github/workflows/frontend-quality.yml`
- `docs/dev-setup.md`
- `AGENTS.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `docs/golden-path.md`
- `.github/workflows/frontend-quality.yml`
- `docs/dev-setup.md`

### Completion Notes List

- 2026-04-05: Created Story 17.2 artifact for a full-stack integration pipeline without mock-only dependencies.

### File List

- `_bmad-output/implementation-artifacts/17-2-run-full-stack-integration-pipeline-without-mock-only-dependencies.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 17.2 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
