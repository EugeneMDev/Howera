# Story 12.4: Add Health, Readiness, and Operational Bootstrap Surface

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want explicit health and readiness endpoints plus bootstrap checks,
so that environments can detect broken startup state before serving user traffic.

## Acceptance Criteria

1. Given the API is deployed, when liveness checks run, then a lightweight health endpoint responds without requiring full dependency access.
2. Given critical runtime dependencies are unavailable or misconfigured, when readiness checks run, then they fail with a conservative signal that blocks traffic.
3. Given developers or CI bootstrap a stack, when they follow the documented checks, then they can verify API readiness and contract availability consistently.

## Tasks / Subtasks

- [ ] Add health and readiness endpoints consistent with the chosen runtime topology.
- [ ] Define which dependencies readiness must verify and which checks remain liveness-only.
- [ ] Update bootstrap documentation to use the supported operational endpoints.
- [ ] Add tests for healthy and degraded readiness outcomes.
- [ ] Ensure the operational surface remains safe and does not leak secrets or internal data.

## Dev Notes

### Developer Context Section

- Current docs reference `/healthz`, but the codebase does not expose a health or readiness surface yet.
- This story should create the minimum operational contract needed for deployment orchestration and CI smoke checks.
- Readiness behavior should stay conservative as persistence and workflow dependencies are added.

### Technical Requirements

- Keep health checks lightweight and readiness checks explicit.
- Ensure operational endpoints do not expose credentials, transcript content, or internal topology secrets.
- Keep `/openapi.json` and the documented bootstrap path accessible.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/`
- `docs/dev-setup.md`
- CI or deployment docs if needed

### Testing Requirements

- Verify health and readiness behavior with supported dependency states.
- Verify bootstrap docs use the actual operational endpoints.
- Verify error responses remain safe and contract-appropriate.

### References

- `docs/dev-setup.md`
- `apps/api/app/main.py`
- `spec/api/openapi.yaml`
- `AGENTS.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `docs/dev-setup.md`
- `apps/api/app/main.py`
- `spec/api/openapi.yaml`

### Completion Notes List

- 2026-04-05: Created Story 12.4 artifact for API health, readiness, and operational bootstrap endpoints.

### File List

- `_bmad-output/implementation-artifacts/12-4-add-health-readiness-and-operational-bootstrap-surface.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 12.4 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
