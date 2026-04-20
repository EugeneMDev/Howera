# Story 14.4: Verify Full Workflow Smoke Path on a Real Local Stack

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a delivery team,
I want an automated smoke path against the real local stack,
so that the core workflow is proven outside of mock-only or in-memory assumptions.

## Acceptance Criteria

1. Given the local stack is bootstrapped with the chosen persistence and workflow components, when the smoke test runs, then it exercises upload confirmation, run dispatch, callback processing, and at least one artifact-producing checkpoint.
2. Given the smoke path fails, when diagnostics are emitted, then they identify the broken stage clearly enough to localize the issue quickly.
3. Given developers or CI rerun the smoke test, when the environment is reset, then setup and teardown remain deterministic.

## Tasks / Subtasks

- [ ] Define the minimum local stack required for the smoke path.
- [ ] Add an automated smoke test that exercises the real workflow lifecycle.
- [ ] Ensure diagnostics label the failing stage clearly.
- [ ] Add bootstrap and teardown steps suitable for local and CI usage.
- [ ] Document how to run and interpret the smoke test.

## Dev Notes

### Developer Context Section

- The frontend currently has a strong mock-mode golden path, but the repository lacks a real cross-stack workflow smoke test.
- This story should become the first true end-to-end proof that the scaffold has been replaced by production-grade runtime pieces.
- It depends on persistent repositories and real workflow dispatch.

### Technical Requirements

- Prefer deterministic local infrastructure over shared external dependencies.
- Keep the smoke path narrow but representative.
- Ensure failures surface the step label or stage name directly.

### File Structure Requirements

- Primary expected touch points:
- integration test suites
- local stack bootstrap files
- `docs/golden-path.md`
- CI configuration if needed

### Testing Requirements

- Verify the smoke path covers upload, run, callback, and artifact readiness.
- Verify failures remain actionable.
- Verify the local stack can be reset between runs.

### References

- `docs/golden-path.md`
- `docs/dev-setup.md`
- `.github/workflows/frontend-quality.yml`
- `AGENTS.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `docs/golden-path.md`
- `docs/dev-setup.md`
- `.github/workflows/frontend-quality.yml`

### Completion Notes List

- 2026-04-05: Created Story 14.4 artifact for a real local-stack workflow smoke test.

### File List

- `_bmad-output/implementation-artifacts/14-4-verify-full-workflow-smoke-path-on-a-real-local-stack.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 14.4 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
