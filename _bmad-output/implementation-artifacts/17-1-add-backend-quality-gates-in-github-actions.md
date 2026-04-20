# Story 17.1: Add Backend Quality Gates in GitHub Actions

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a delivery team,
I want backend quality gates enforced in GitHub Actions,
so that API regressions are blocked before merge instead of relying only on local discipline.

## Acceptance Criteria

1. Given backend code changes are proposed, when CI runs, then lint, test, and check commands for the API execute automatically and failures block merge.
2. Given CI provisions the backend environment, when the workflow installs dependencies, then the setup matches the supported runtime packaging path.
3. Given verification fails, when developers inspect CI output, then the broken stage is easy to identify.

## Tasks / Subtasks

- [ ] Add a GitHub Actions workflow for backend verification.
- [ ] Reuse the supported backend install and run strategy from the runtime-packaging story.
- [ ] Ensure the workflow covers the API verification commands required by `AGENTS.md`.
- [ ] Add clear step names and failure reporting.
- [ ] Document the backend CI gate in developer docs if needed.

## Dev Notes

### Developer Context Section

- The repository currently has a frontend CI workflow only.
- This story should establish the backend equivalent before full-stack integration and deployment automation are attempted.
- It depends on runtime packaging and stable verification commands being defined first.

### Technical Requirements

- Keep CI aligned with the supported backend dependency-install path.
- Avoid parallel workflows that verify different backend commands inconsistently.
- Ensure CI remains deterministic and reproducible.

### File Structure Requirements

- Primary expected touch points:
- `.github/workflows/`
- `apps/api/`
- `docs/dev-setup.md` if needed

### Testing Requirements

- Verify CI runs backend verification commands successfully on the supported runtime.
- Verify failures report the broken stage clearly.
- Verify the workflow blocks merge on failure.

### References

- `.github/workflows/frontend-quality.yml`
- `apps/api/Makefile`
- `apps/api/pyproject.toml`
- `AGENTS.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `.github/workflows/frontend-quality.yml`
- `apps/api/Makefile`
- `apps/api/pyproject.toml`

### Completion Notes List

- 2026-04-05: Created Story 17.1 artifact for backend GitHub Actions quality gates.

### File List

- `_bmad-output/implementation-artifacts/17-1-add-backend-quality-gates-in-github-actions.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 17.1 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
