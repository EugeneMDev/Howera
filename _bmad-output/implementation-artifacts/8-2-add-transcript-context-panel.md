# Story 8.2: Add Transcript Context Panel

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want transcript segments beside the editor,
so that I can align edits with source audio context.

## Acceptance Criteria

1. Given transcript content exists for the job, when the editor opens the transcript panel, then segments render with timestamps and text and transcript refresh does not reset editor selection.
2. Given transcript is unavailable or not ready, when the panel is opened, then the UI shows a clear pending or unavailable state and the editor remains usable.

## Tasks / Subtasks

- [x] Add transcript panel layout and toggle behavior inside the instruction workspace.
- [x] Implement transcript query and pagination support through the shared API client.
- [x] Render segment timestamps and text in a reading-friendly panel.
- [x] Preserve editor selection and draft state while transcript data refreshes.
- [x] Add pending, unavailable, and not-ready states for transcript access.
- [x] Add tests for transcript rendering, state preservation, and `TRANSCRIPT_NOT_READY` handling.

## Dev Notes

### Developer Context Section

- Transcript retrieval is already implemented by backend Story 4.1.
- UX requires the transcript context panel to be available without breaking editor flow.
- This story should prepare for regenerate and screenshot workflows that depend on nearby source context.

### Technical Requirements

- Use `GET /jobs/{jobId}/transcript` with contract pagination.
- Preserve editor-local UI state while transcript data changes.
- Show clear pending or unavailable states rather than empty silence.
- Keep transcript text out of browser telemetry and debug logging.
- Current implementation keeps transcript fetching lazy behind an explicit panel toggle, uses contract `limit/cursor` pagination with append-only ordering, and stores editor selection snapshots separately from transcript state so refreshes do not mutate the markdown draft.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/features/instructions/`
- `apps/web/src/features/jobs/`
- `apps/web/src/shared/hooks/`
- `apps/web/tests/`

### Testing Requirements

- Verify transcript panel renders timestamps and text correctly.
- Verify transcript refresh does not reset current editor selection.
- Verify not-ready and unavailable states remain usable.
- Verify pagination or incremental load behavior does not reorder segments.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `docs/golden-path.md`
- `_bmad-output/implementation-artifacts/4-1-retrieve-transcript-segments-for-job.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `docs/golden-path.md`
- `_bmad-output/implementation-artifacts/4-1-retrieve-transcript-segments-for-job.md`

### Completion Notes List

- 2026-03-24: Created Story 8.2 artifact with transcript-side-panel scope and state-preservation guardrails.
- 2026-03-24: Captured transcript pending/unavailable UX requirements for frontend implementation.
- 2026-03-25: Added transcript pagination support to the shared job API layer and implemented transcript panel state/helpers for loading, append, not-ready, and unavailable cases.
- 2026-03-25: Extended the instruction editor with a toggleable transcript side panel, reading-friendly timestamped segment rendering, and editor selection snapshots preserved across transcript refreshes.
- 2026-03-25: Added unit coverage for transcript contract helpers, selection snapshot utilities, and updated job API tests, then passed `make lint`, `make test`, `make typecheck`, `make build`, and `make check` in `apps/web`.

### File List

- `_bmad-output/implementation-artifacts/8-2-add-transcript-context-panel.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/features/jobs/api.ts`
- `apps/web/src/features/instructions/selection.ts`
- `apps/web/src/features/instructions/transcript-state.ts`
- `apps/web/src/features/instructions/transcript-hooks.ts`
- `apps/web/src/features/instructions/components/instruction-transcript-panel.tsx`
- `apps/web/src/features/instructions/components/instruction-editor-screen.tsx`
- `apps/web/tests/unit/instruction-selection.test.ts`
- `apps/web/tests/unit/instructions-transcript.test.ts`
- `apps/web/tests/unit/jobs-api.test.tsx`

### Change Log

- 2026-03-24: Created Story 8.2 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-03-25: Implemented transcript side-panel loading, timestamped segment rendering, not-ready/unavailable states, and selection-preserving transcript refresh behavior in `apps/web`.
- 2026-03-25: Added transcript/selection unit tests, passed `make check`, and moved Story 8.2 to `done`.
