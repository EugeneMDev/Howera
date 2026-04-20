# Story 15.3: Execute Screenshot Pipeline Through Real Media and Storage Services

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor workflow,
I want screenshot extraction and asset mutation backed by real media and storage services,
so that anchors and screenshots are durable production artifacts rather than scaffold-only state.

## Acceptance Criteria

1. Given screenshot extraction is requested, when the pipeline runs, then media processing executes against the selected tooling and stores outputs durably.
2. Given screenshot assets are replaced, deleted, uploaded, or annotated, when those actions complete, then manifest linkage, versioning, and active-asset rules remain consistent.
3. Given screenshot-related failures occur, when users poll task state, then sanitized outcomes and replay-safe behavior remain intact.

## Tasks / Subtasks

- [ ] Implement the real screenshot extraction pipeline using the selected media tooling.
- [ ] Store generated and uploaded screenshot assets through the object-storage path.
- [ ] Preserve anchor metadata, active-asset resolution, and versioning behavior.
- [ ] Integrate annotation and replace flows with durable artifact updates.
- [ ] Add integration tests covering extraction, lifecycle mutation, and failure handling.

## Dev Notes

### Developer Context Section

- The API and frontend already model screenshot lifecycle behavior, but the repository lacks the underlying production pipeline.
- This story should turn the existing contract into a real durable service path.
- It depends on object storage, workflow runtime, and persistence being complete first.

### Technical Requirements

- Preserve anchor addressing and cross-version traceability rules.
- Keep artifact writes atomic or logically consistent.
- Avoid leaking uploaded-image URLs, tokens, or content into logs.

### File Structure Requirements

- Primary expected touch points:
- screenshot pipeline modules
- storage adapters
- `apps/api/app/services/`
- `apps/api/tests/`

### Testing Requirements

- Verify extraction and asset lifecycle flows produce durable storage artifacts.
- Verify active fallback behavior remains correct after delete or replace actions.
- Verify annotation and upload failures do not corrupt manifest state.

### References

- `_bmad-output/implementation-artifacts/5-1-extract-screenshot-with-alignment-parameters-and-anchor-metadata.md`
- `_bmad-output/implementation-artifacts/5-6-anchor-addressing-persistence-policy-and-cross-version-traceability.md`
- `AGENTS.md`
- `.env.example`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/implementation-artifacts/5-1-extract-screenshot-with-alignment-parameters-and-anchor-metadata.md`
- `_bmad-output/implementation-artifacts/5-6-anchor-addressing-persistence-policy-and-cross-version-traceability.md`
- `AGENTS.md`

### Completion Notes List

- 2026-04-05: Created Story 15.3 artifact for executing the screenshot pipeline through real media and storage services.

### File List

- `_bmad-output/implementation-artifacts/15-3-execute-screenshot-pipeline-through-real-media-and-storage-services.md`
- `_bmad-output/implementation-artifacts/production-readiness-sprint-status.yaml`

### Change Log

- 2026-04-05: Created Story 15.3 artifact and moved production-readiness story status from `backlog` to `ready-for-dev`.
