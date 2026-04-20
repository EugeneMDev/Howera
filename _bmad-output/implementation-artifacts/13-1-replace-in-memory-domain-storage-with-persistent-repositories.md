# Story 13.1: Replace In-Memory Domain Storage with Persistent Repositories

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a backend team,
I want durable repositories for core domain state,
so that jobs, projects, and instructions survive restarts and scale beyond a single process.

## Acceptance Criteria

1. Given the API creates or updates projects, jobs, and instructions, when persistence is migrated, then those records are stored durably rather than in process memory.
2. Given the service restarts, when previously created entities are queried, then they remain available and ownership rules still apply.
3. Given the application boots, when repositories are wired, then `create_app` uses persistent storage as the primary runtime path instead of the current in-memory scaffold.

## Tasks / Subtasks

- [ ] Define repository interfaces or persistence boundaries for core domain records.
- [ ] Implement durable storage for projects, jobs, and instruction versions.
- [ ] Migrate read and write paths from the current in-memory store to the new persistence layer.
- [ ] Preserve ownership, no-leak, and FSM-related behavior during the migration.
- [ ] Add integration coverage for persistence-backed CRUD and retrieval paths.

## Dev Notes

### Developer Context Section

- `InMemoryStore` currently acts as the authoritative backend store and is explicitly described as scaffolding for tests.
- This story is the critical first persistence milestone and blocks durable idempotency, workflow callbacks, and artifact management.
- Existing tests provide behavioral expectations that should be preserved through the repository migration.

### Technical Requirements

- Preserve API contract behavior from `spec/api/openapi.yaml`.
- Avoid direct status mutation that bypasses `ensure_transition`.
- Keep data modeling compatible with follow-on audit, callback, and artifact requirements.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/repositories/`
- `apps/api/app/services/`
- `apps/api/app/main.py`
- `apps/api/tests/`

### Testing Requirements

- Verify persisted records survive restart boundaries or equivalent repository reinitialization.
- Verify ownership and no-leak behavior remain unchanged.
- Verify the API contract still serves the same path and schema surface.

### References

- `apps/api/app/repositories/memory.py`
- `apps/api/app/main.py`
- `spec/api/openapi.yaml`
- `AGENTS.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `apps/api/app/repositories/memory.py`
- `apps/api/app/main.py`
- `spec/api/openapi.yaml`

### Completion Notes List

- 2026-04-05: Created Story 13.1 artifact for replacing the in-memory domain store with persistent repositories.

### File List

- `_bmad-output/implementation-artifacts/13-1-replace-in-memory-domain-storage-with-persistent-repositories.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 13.1 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
