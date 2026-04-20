# Story 13.3: Integrate Object Storage with Artifact Manifest Discipline

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a backend team,
I want artifacts stored and tracked through real object storage,
so that raw and derived assets are durable, versioned, and policy-controlled.

## Acceptance Criteria

1. Given a job owns raw and derived artifacts, when storage integration is complete, then every stored file is represented in `artifact_manifest` with durable storage references.
2. Given raw artifacts such as source video, audio, or transcript are created, when later workflows execute, then those raw artifacts remain immutable.
3. Given derived assets such as screenshots and exports are generated, when new versions are created, then versioned linkage and download policy remain explicit and traceable.

## Tasks / Subtasks

- [ ] Implement object storage integration behind an adapter or repository boundary.
- [ ] Persist artifact manifest updates with explicit raw versus derived ownership rules.
- [ ] Add versioned linkage for screenshots, exports, and other derived outputs.
- [ ] Support securely scoped signed-access patterns where required.
- [ ] Add tests for manifest consistency, immutability, and versioned asset linkage.

## Dev Notes

### Developer Context Section

- Artifact state is currently modeled in memory and cannot survive runtime restarts.
- This story should establish real storage references before screenshot and export pipelines are implemented.
- It should preserve the repository's existing manifest discipline and no-anonymous-file policy.

### Technical Requirements

- Maintain an `artifact_manifest` for every job.
- Keep raw artifact references immutable after creation.
- Ensure derived assets are versioned and linked back to the owning job and instruction context.

### File Structure Requirements

- Primary expected touch points:
- `apps/api/app/repositories/`
- storage adapter modules
- `apps/api/app/services/`
- `apps/api/tests/`

### Testing Requirements

- Verify manifest updates remain logically consistent on failures.
- Verify signed URL scope and TTL rules remain explicit.
- Verify derived-asset version history remains queryable.

### References

- `AGENTS.md`
- `apps/api/app/repositories/memory.py`
- `.env.example`
- `_bmad-output/planning-artifacts/architecture.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `AGENTS.md`
- `apps/api/app/repositories/memory.py`
- `.env.example`

### Completion Notes List

- 2026-04-05: Created Story 13.3 artifact for object-storage integration and durable artifact-manifest discipline.

### File List

- `_bmad-output/implementation-artifacts/13-3-integrate-object-storage-with-artifact-manifest-discipline.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 13.3 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
