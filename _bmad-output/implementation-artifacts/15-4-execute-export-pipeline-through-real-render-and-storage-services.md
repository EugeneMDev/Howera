# Story 15.4: Execute Export Pipeline Through Real Render and Storage Services

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want exports rendered and stored by real production services,
so that completed download artifacts reflect durable output rather than only modeled state transitions.

## Acceptance Criteria

1. Given an export is requested, when the pipeline runs, then the selected renderer generates the requested artifact format and stores it durably.
2. Given an export succeeds, when status is queried, then provenance, manifest linkage, and download policy remain frozen and traceable.
3. Given export generation fails or is replayed, when users inspect state, then the status model, sanitized outcomes, and idempotency behavior remain correct.

## Tasks / Subtasks

- [ ] Implement the real export rendering pipeline for the selected output formats.
- [ ] Store generated export artifacts durably and link them into the manifest.
- [ ] Preserve export FSM, provenance freezing, and signed-download policy.
- [ ] Handle retries, failures, and idempotency on the real execution path.
- [ ] Add integration tests for successful and failed export generation.

## Dev Notes

### Developer Context Section

- Existing backend and frontend stories already define the export contract, status model, and secure download behavior.
- This story should connect that contract to a real rendering pipeline and durable artifact storage.
- It depends on persistence, object storage, and workflow runtime being available first.

### Technical Requirements

- Keep export provenance immutable after success.
- Maintain strictly scoped signed-download behavior.
- Avoid persisting signed URLs or leaking export contents into logs.

### File Structure Requirements

- Primary expected touch points:
- export pipeline modules
- storage adapters
- `apps/api/app/services/`
- `apps/api/tests/`

### Testing Requirements

- Verify PDF and packaged markdown outputs are generated durably.
- Verify export FSM and provenance linkage remain correct under replay or failure.
- Verify secure download policy continues to use time-limited signed URLs.

### References

- `_bmad-output/implementation-artifacts/6-1-create-export-request-bound-to-exact-instruction-version.md`
- `_bmad-output/implementation-artifacts/6-5-issue-strictly-scoped-signed-download-url.md`
- `AGENTS.md`
- `.env.example`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/6-1-create-export-request-bound-to-exact-instruction-version.md`
- `_bmad-output/implementation-artifacts/6-5-issue-strictly-scoped-signed-download-url.md`
- `AGENTS.md`

### Completion Notes List

- 2026-04-05: Created Story 15.4 artifact for real export rendering and durable storage integration.

### File List

- `_bmad-output/implementation-artifacts/15-4-execute-export-pipeline-through-real-render-and-storage-services.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 15.4 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
