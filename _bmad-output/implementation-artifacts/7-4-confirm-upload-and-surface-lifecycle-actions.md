# Story 7.4: Confirm Upload and Surface Lifecycle Actions

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an editor,
I want to confirm upload and perform only valid lifecycle actions,
so that job execution remains aligned to backend FSM rules.

## Acceptance Criteria

1. Given a job is in `CREATED`, when the editor confirms upload using the current contract payload, then the UI moves to the `UPLOADED` state view and clearly indicates that the current flow is confirm-by-`video_uri`.
2. Given a job is eligible for `run`, `retry`, or `cancel`, when the editor triggers an action, then the UI reflects idempotent, accepted, or conflict outcomes explicitly and status polling remains bounded and visible.

## Tasks / Subtasks

- [x] Implement confirm-upload form flow using the current `video_uri` contract.
- [x] Add lifecycle action hooks for `run`, `cancel`, and `retry` with contract-safe mutation handling.
- [x] Add lifecycle timeline and status panel bound to backend job state and timestamps.
- [x] Gate available actions from current job status without inventing client-side FSM rules beyond contract behavior.
- [x] Surface replay, accepted, and conflict outcomes explicitly for lifecycle actions.
- [x] Add polling freshness and bounded refresh behavior for status progression after action submission.
- [x] Add unit coverage for confirm-upload, run, cancel, retry contract calls and lifecycle UI helpers.

## Dev Notes

### Developer Context Section

- Backend lifecycle contract is already implemented across Stories 2.1, 2.2, 3.5, and 3.6.
- Frontend must reflect backend FSM outcomes rather than duplicate lifecycle logic.
- The current MVP flow supports confirm-by-`video_uri`, not browser-native main video upload.
- Current implementation keeps lifecycle actions on the job detail route, with a contract-mapped timeline, action gating derived from current `JobStatus`, and a bounded polling window after lifecycle mutations.
- The retry form defaults `model_profile` to `cloud-default` because that value is already used across backend retry tests and avoids inventing an undocumented profile.

### Technical Requirements

- Use `POST /jobs/{jobId}/confirm-upload`, `POST /jobs/{jobId}/run`, `POST /jobs/{jobId}/cancel`, and `POST /jobs/{jobId}/retry`.
- Keep lifecycle timeline directly mapped to backend status values.
- Preserve idempotent replay messaging for `run` and `retry`.
- Keep polling bounded and visible to the user.
- Do not invent a binary main-video upload handshake; upload confirmation remains a `video_uri` form until backend contract changes.

### File Structure Requirements

- Primary expected touch points:
- `apps/web/src/features/jobs/`
- `apps/web/src/app/(workspace)/jobs/`
- `apps/web/src/shared/hooks/`
- `apps/web/tests/`

### Testing Requirements

- Verify confirm-upload transitions the UI into an `UPLOADED`-ready state.
- Verify run/cancel/retry mutations show accepted, replayed, and conflict outcomes.
- Verify invalid lifecycle actions do not leave stale optimistic state behind.
- Verify polling and last-refreshed UI are visible during in-flight processing.
- Final verification target: `cd apps/web && make check`.

### References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `spec/domain/job_fsm.md`
- `docs/golden-path.md`
- `_bmad-output/implementation-artifacts/2-1-confirm-job-upload-with-video-uri.md`
- `_bmad-output/implementation-artifacts/2-2-start-workflow-run-for-an-upload-confirmed-job.md`
- `_bmad-output/implementation-artifacts/3-5-cancel-running-job-via-fsm-governed-rules.md`
- `_bmad-output/implementation-artifacts/3-6-retry-failed-job-from-checkpoint-with-policy-bound-model-profile.md`

## Dev Agent Record

### Agent Model Used

GPT-5.3-Codex

### Debug Log References

- `_bmad-output/planning-artifacts/epics-frontend-bmad.md`
- `spec/api/openapi.yaml`
- `spec/domain/job_fsm.md`
- `docs/golden-path.md`
- `_bmad-output/implementation-artifacts/2-1-confirm-job-upload-with-video-uri.md`
- `_bmad-output/implementation-artifacts/2-2-start-workflow-run-for-an-upload-confirmed-job.md`

### Completion Notes List

- 2026-03-24: Created Story 7.4 artifact with lifecycle-action scope and FSM-bound UI guardrails.
- 2026-03-24: Captured confirm-by-`video_uri` constraint and bounded status-polling requirements for frontend implementation.
- 2026-03-24: Added lifecycle API wrappers, action-gating helpers, retry request-id generation, and a bounded polling hook for job lifecycle refresh behavior.
- 2026-03-24: Reworked job detail UI to support confirm-by-`video_uri`, `run`, `cancel`, and `retry`, with explicit replay/conflict/success messaging and visible refresh freshness.
- 2026-03-24: Added lifecycle timeline rendering and unit tests for lifecycle contract calls, gating, and status rendering; passed `make lint`, `make test`, `make typecheck`, `make build`, and `make check` in `apps/web`.

### File List

- `_bmad-output/implementation-artifacts/7-4-confirm-upload-and-surface-lifecycle-actions.md`
- `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`
- `apps/web/src/features/jobs/api.ts`
- `apps/web/src/features/jobs/hooks.ts`
- `apps/web/src/features/jobs/lifecycle.ts`
- `apps/web/src/features/jobs/components/job-detail-screen.tsx`
- `apps/web/src/features/jobs/components/job-lifecycle-timeline.tsx`
- `apps/web/src/shared/hooks/use-bounded-polling.ts`
- `apps/web/tests/unit/jobs-api.test.tsx`
- `apps/web/tests/unit/jobs-lifecycle.test.tsx`

### Change Log

- 2026-03-24: Created Story 7.4 artifact and moved frontend story status from `backlog` to `ready-for-dev`.
- 2026-03-24: Implemented contract-safe lifecycle actions, bounded polling, and lifecycle UI on the job detail route.
- 2026-03-24: Added lifecycle-focused unit coverage, passed `make check`, and moved Story 7.4 to `done`.
