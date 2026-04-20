# Story 12.1: Define Production Architecture and Deployment Topology

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a platform lead,
I want a documented production architecture and deployment topology,
so that persistence, workflow, hosting, and security decisions are fixed before implementation starts.

## Acceptance Criteria

1. Given the current scaffold relies on in-memory persistence and thin deployment assumptions, when the ADR is approved, then it names the production choices for database, object storage, workflow runner, authentication, frontend hosting, secrets, and observability.
2. Given backend and frontend teams plan implementation, when they read the ADR, then the request, callback, artifact, and deployment flows identify exact integration boundaries and owned runtimes.
3. Given follow-on stories depend on this decision set, when the architecture changes, then there is one authoritative document to update and cite.

## Tasks / Subtasks

- [ ] Document current-state architectural gaps and scaffolding constraints.
- [ ] Select the production targets for database, storage, workflow execution, auth, and web hosting.
- [ ] Define the end-to-end flow for upload, run, callback, artifact generation, export, and download.
- [ ] Capture deployment boundaries, networking assumptions, and secret ownership for each runtime.
- [ ] Record rejected alternatives, migration notes, and open questions that could block implementation.

## Dev Notes

### Developer Context Section

- The current backend wires `InMemoryStore` from `app.main`, so replacement targets should be fixed before repository and workflow work begins.
- The repo contains frontend hosting scaffolding but no complete cross-stack deployment topology yet.
- This story is the architectural prerequisite for runtime config, persistence, and CI/CD stories.

### Technical Requirements

- Do not modify `spec/`; document architecture outside `spec/`.
- Cover both API and `apps/web` deployment targets.
- Define integration boundaries between API, workflow runner, storage, and hosting layers.
- Keep the output actionable enough to unblock follow-on implementation stories directly.

### File Structure Requirements

- Primary expected touch points:
- `_bmad-output/`
- `docs/`
- runtime or environment documentation if needed

### Testing Requirements

- Review-based story; no dedicated code tests required beyond standard repo verification.
- Ensure follow-on stories can reference the ADR unambiguously.

### References

- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/prd.md`
- `AGENTS.md`
- `apps/api/app/main.py`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/prd.md`
- `AGENTS.md`

### Completion Notes List

- 2026-04-05: Created Story 12.1 artifact for the production architecture ADR and deployment-topology decision set.

### File List

- `_bmad-output/implementation-artifacts/12-1-define-production-architecture-and-deployment-topology.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 12.1 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
