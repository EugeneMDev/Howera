# Story 11.3: Add Frontend Test Automation and BMAD Quality Gates

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a delivery team,
I want automated frontend quality checks,
so that regressions are caught before release and BMAD story execution stays disciplined.

## Acceptance Criteria

1. Given frontend changes are introduced, when CI runs, then lint, typecheck, and unit tests execute and failures block merge.
2. Given the mock-mode golden path is executed, when create, run, edit, screenshot, and export flows are exercised, then the critical path passes end to end and failures emit actionable diagnostics.

## Tasks / Subtasks

- [x] Add stable frontend commands for lint, typecheck, test, and build.
- [x] Add CI wiring so frontend quality gates run automatically.
- [x] Add unit-test coverage for shared UI, API, and feature logic.
- [x] Add mock-mode integration or E2E golden-path coverage for create, run, edit, screenshot, and export flows.
- [x] Add failure diagnostics that identify the broken frontend step clearly.
- [x] Document frontend verification commands alongside BMAD workflow expectations.

## Dev Notes

### Developer Context Section

- AGENTS requires proof before done through lint, test, and check commands.
- Architecture expects frontend CI quality gates and golden-path subset coverage.
- This story should turn the planned `apps/web` verification workflow into a reliable release gate.

### Technical Requirements

- Support `make lint`, `make test`, and `make check` in `apps/web`.
- Ensure CI blocks merge on frontend failures.
- Prefer deterministic mock-mode tests for the golden path.
- Keep diagnostics actionable enough to localize failures quickly.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/Makefile`
- `apps/web/package.json`
- `apps/web/tests/`
- repository CI config files
- docs for local verification if needed

### Testing Requirements

- Verify lint, typecheck, unit test, and build commands run locally.
- Verify CI executes and fails on broken frontend checks.
- Verify mock-mode golden-path coverage spans core workflow steps.
- Verify diagnostics identify the failing step or domain.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `docs/golden-path.md`
- `AGENTS.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `docs/golden-path.md`
- `AGENTS.md`

### Completion Notes List

- 2026-03-24: Created Story 11.3 artifact with frontend verification and CI-gate scope.
- 2026-03-24: Captured mock-mode golden-path and actionable-diagnostics requirements for frontend implementation.
- 2026-04-04: Split `apps/web` test commands into unit and mock-mode golden-path entrypoints while preserving stable `make lint`, `make test`, and `make check` workflows.
- 2026-04-04: Added a deterministic frontend golden-path integration suite that exercises create, run, edit, screenshot, and export flows through the real API wrapper layer.
- 2026-04-04: Added step-labeled golden-path failure diagnostics so broken workflow stages are identifiable directly from test output.
- 2026-04-04: Added a GitHub Actions workflow that runs lint, unit tests, golden-path tests, typecheck, and build under mock auth on pull requests.
- 2026-04-04: Documented frontend verification and BMAD proof-before-done expectations in `docs/dev-setup.md` and `docs/golden-path.md`.
- 2026-04-04: Verified `make lint`, `make test`, and `make check` in `apps/web`.

### File List

- `_bmad-output/implementation-artifacts/11-3-add-frontend-test-automation-and-bmad-quality-gates.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `.github/workflows/frontend-quality.yml`
- `apps/web/Makefile`
- `apps/web/package.json`
- `apps/web/tests/integration/frontend-golden-path.test.ts`
- `docs/dev-setup.md`
- `docs/golden-path.md`

### Change Log

- 2026-03-24: Created Story 11.3 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-04-04: Completed Story 11.3 frontend quality-gate and mock-mode golden-path work and moved frontend story status to `done`.
