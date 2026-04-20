---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - docs/golden-path.md
  - spec/api/openapi.yaml
  - spec/acceptance/v1_mvp.md
---

# Howera - Frontend Epic Breakdown for BMAD Workflow

## Overview

This document is the BMAD-ready frontend epic and story breakdown for the post-v1 frontend phase. It is intended to be used as the source for `create-story` and `dev-story` preparation without relying on Jira-specific fields.

## Workflow Notes

- Canonical backend BMAD artifacts remain unchanged.
- This file is the canonical frontend phase epic breakdown.
- Frontend phase tracking is initialized separately in `_bmad-output/implementation-artifacts/frontend-sprint-status.yaml`.
- If the team wants stock BMAD auto-discovery without specifying phase files, frontend epics can later be merged into the canonical `epics.md` and `sprint-status.yaml`.

## Locked Scope Decisions

- Auth uses Firebase Web SDK session restore plus popup or redirect login.
- Browser sends Firebase ID token from `currentUser.getIdToken()` to FastAPI as bearer auth.
- Structural validation is in MVP and is already present in the instruction contract.
- Screenshot annotation is in MVP.
- Export MVP covers status tracking and secure download only.
- Export provenance and publish-readiness summary are deferred from MVP.

## Known Gap

- The current API supports `POST /jobs/{jobId}/confirm-upload`, but does not define a browser-facing main video upload handshake endpoint.
- Frontend MVP can therefore support confirm-by-`video_uri`, not true binary source-video upload.
- If real browser upload is required for the main video, create a separate backend contract story first.

## Requirements Inventory

### Functional Requirements

FE-FR-001: Authenticated editor can access protected frontend workspace using valid bearer session.
FE-FR-002: Editor can create and browse owned projects and jobs through frontend UI.
FE-FR-003: Editor can confirm upload, run workflow, retry failed runs, and cancel allowed jobs from the UI.
FE-FR-004: Editor can view lifecycle progression and valid next actions clearly.
FE-FR-005: Editor can retrieve and edit instruction markdown with version conflict-safe UX.
FE-FR-006: Editor can view transcript segments alongside instruction editing.
FE-FR-007: Editor can request targeted regenerate and monitor task status to completion.
FE-FR-008: Editor can view structural validation status and validation errors for instruction content.
FE-FR-009: Editor can execute screenshot extraction flow and monitor task outcomes.
FE-FR-010: Editor can inspect anchors and active asset context across instruction versions.
FE-FR-011: Editor can upload, attach, replace, and delete screenshot assets on anchors.
FE-FR-012: Editor can annotate screenshot assets and receive deterministic rendered results.
FE-FR-013: Editor can request export generation and monitor export status.
FE-FR-014: Editor can securely download completed export artifacts.
FE-FR-015: Frontend surfaces consistent error, retry, and async polling states.
FE-FR-016: Frontend satisfies accessibility and responsive baseline for in-scope pages.
FE-FR-017: Frontend has CI quality gates and mock-mode golden-path coverage.
FE-FR-018: Frontend deployment config and telemetry exclude secrets and sensitive content.

### NonFunctional Requirements

FE-NFR-001: Frontend must map UI state directly to backend contract and FSM/task states.
FE-NFR-002: Frontend must avoid logging secrets, raw transcript content, or signed URLs.
FE-NFR-003: Polling and retry behavior must be bounded and explicit to the user.
FE-NFR-004: Frontend must support desktop and tablet fully, with mobile status-checking support.
FE-NFR-005: Frontend must be suitable for BMAD story-by-story implementation sequencing.

## FR Coverage Map

FE-FR-001: Epic 7 - Foundation and authentication
FE-FR-002: Epic 7 - Projects and jobs workspace
FE-FR-003: Epic 7 - Job lifecycle controls
FE-FR-004: Epic 7 - Lifecycle timeline and action gating
FE-FR-005: Epic 8 - Instruction editor with conflict-safe save
FE-FR-006: Epic 8 - Transcript context panel
FE-FR-007: Epic 8 - Regenerate flow and task polling
FE-FR-008: Epic 8 - Validation status surface
FE-FR-009: Epic 9 - Screenshot extraction and task polling
FE-FR-010: Epic 9 - Anchor inspector and version context
FE-FR-011: Epic 9 - Asset lifecycle UX
FE-FR-012: Epic 9 - Annotation workflow
FE-FR-013: Epic 10 - Export request and status tracking
FE-FR-014: Epic 10 - Secure download UX
FE-FR-015: Epic 11 - Unified error, retry, and polling pattern
FE-FR-016: Epic 11 - Accessibility and responsive baseline
FE-FR-017: Epic 11 - Frontend test automation and CI
FE-FR-018: Epic 11 - Deployment config and safe telemetry

## Epic List

### Epic 7: Foundation and Auth
Editors can authenticate, navigate project/job context, and trigger valid lifecycle actions with clear state visibility.
**FRs covered:** FE-FR-001, FE-FR-002, FE-FR-003, FE-FR-004

### Epic 8: Instruction Workspace
Editors can author instructions with transcript context, version-safe saves, targeted regenerate flows, and visible validation state.
**FRs covered:** FE-FR-005, FE-FR-006, FE-FR-007, FE-FR-008

### Epic 9: Screenshots and Anchors
Editors can extract screenshots, inspect anchor context, manage asset versions, and annotate assets directly in the workflow UI.
**FRs covered:** FE-FR-009, FE-FR-010, FE-FR-011, FE-FR-012

### Epic 10: Export Delivery
Editors can request exports, monitor async export state, and securely download completed artifacts.
**FRs covered:** FE-FR-013, FE-FR-014

### Epic 11: Reliability and Release Readiness
Frontend achieves production-ready async behavior, accessibility, CI quality gates, and safe deployment/telemetry posture.
**FRs covered:** FE-FR-015, FE-FR-016, FE-FR-017, FE-FR-018, FE-NFR-001, FE-NFR-002, FE-NFR-003, FE-NFR-004, FE-NFR-005

## Epic 7: Foundation and Auth

Editors can authenticate, navigate project/job context, and trigger valid lifecycle actions with clear state visibility.

### Story 7.1: Bootstrap `apps/web` and Workspace Shell

As an editor,
I want a stable frontend shell with shared layout and state primitives,
So that all product flows feel consistent and implementation can scale.

**Acceptance Criteria:**

**Given** the frontend app is initialized
**When** a user opens workspace routes
**Then** a shared app shell renders navigation, workspace, and context panel regions
**And** shared loading, empty, and error states are available for feature teams.

**Given** frontend infrastructure is configured
**When** developers add new screens
**Then** shared API client, query provider, and design tokens are reused
**And** environment-driven API/Firebase configuration is already in place.

**Source Hints:** `_bmad-output/planning-artifacts/architecture.md`, `_bmad-output/planning-artifacts/ux-design-specification.md`

### Story 7.2: Restore Firebase Session and Protect Workspace Routes

As an editor,
I want valid sessions restored automatically and protected routes guarded,
So that I can resume work safely without reimplementing auth per screen.

**Acceptance Criteria:**

**Given** a user returns with a persisted Firebase session
**When** the app initializes
**Then** Firebase restores the session and `currentUser` becomes available
**And** protected routes resume with bearer-authenticated API access.

**Given** a user is unauthenticated
**When** they access a protected workspace route
**Then** they are redirected into the Firebase sign-in flow
**And** no protected API calls execute until auth completes.

**Source Hints:** user-confirmed auth flow notes from planning session, `_bmad-output/planning-artifacts/architecture.md`

### Story 7.3: Create and Browse Owned Projects and Jobs

As an editor,
I want to create and browse my projects and jobs,
So that I can manage workflow work items from the UI.

**Acceptance Criteria:**

**Given** an authenticated editor
**When** they create a project or job from the UI
**Then** the relevant list refreshes without full page reload
**And** contract-consistent identifiers and statuses are shown.

**Given** a project or job is missing or not owned by the editor
**When** the editor navigates to its route
**Then** the UI shows a no-leak not-found state
**And** exposes no cross-owner metadata.

**Source Hints:** `spec/api/openapi.yaml`, `docs/golden-path.md`

### Story 7.4: Confirm Upload and Surface Lifecycle Actions

As an editor,
I want to confirm upload and perform only valid lifecycle actions,
So that job execution remains aligned to backend FSM rules.

**Acceptance Criteria:**

**Given** a job is in `CREATED`
**When** the editor confirms upload using the current contract payload
**Then** the UI moves to the `UPLOADED` state view
**And** clearly indicates that the current flow is confirm-by-`video_uri`.

**Given** a job is eligible for `run`, `retry`, or `cancel`
**When** the editor triggers an action
**Then** the UI reflects idempotent, accepted, or conflict outcomes explicitly
**And** status polling remains bounded and visible.

**Source Hints:** `spec/api/openapi.yaml`, `docs/golden-path.md`, `spec/domain/job_fsm.md`

## Epic 8: Instruction Workspace

Editors can author instructions with transcript context, version-safe saves, targeted regenerate flows, and visible validation state.

### Story 8.1: Edit Instruction with Version-Safe Save

As an editor,
I want to edit instruction markdown and save safely,
So that I can refine generated content without accidental overwrite.

**Acceptance Criteria:**

**Given** an instruction is loaded
**When** the editor updates markdown and saves
**Then** the request includes `base_version`
**And** success updates version metadata without full page reload.

**Given** the backend returns `VERSION_CONFLICT`
**When** save fails
**Then** the UI preserves unsaved local content
**And** offers a reload or merge-oriented recovery path.

**Source Hints:** `spec/api/openapi.yaml`, `_bmad-output/planning-artifacts/ux-design-specification.md`

### Story 8.2: Add Transcript Context Panel

As an editor,
I want transcript segments beside the editor,
So that I can align edits with source audio context.

**Acceptance Criteria:**

**Given** transcript content exists for the job
**When** the editor opens the transcript panel
**Then** segments render with timestamps and text
**And** transcript refresh does not reset editor selection.

**Given** transcript is unavailable or not ready
**When** the panel is opened
**Then** the UI shows a clear pending or unavailable state
**And** the editor remains usable.

**Source Hints:** `spec/api/openapi.yaml`, `docs/golden-path.md`

### Story 8.3: Request Targeted Regenerate and Poll Task Status

As an editor,
I want to regenerate a selected block or range,
So that I can improve content without rerunning the full workflow.

**Acceptance Criteria:**

**Given** the editor selects a valid `block_id` or `char_range`
**When** they submit regenerate with a `client_request_id`
**Then** the UI shows task acknowledgement immediately
**And** polling begins automatically.

**Given** the regenerate task reaches `SUCCEEDED` or `FAILED`
**When** polling receives terminal state
**Then** the UI surfaces the result or sanitized failure details
**And** keeps the editor in a recoverable state.

**Source Hints:** `spec/api/openapi.yaml`, `_bmad-output/planning-artifacts/ux-design-specification.md`

### Story 8.4: Surface Validation Status and Validation Errors

As an editor,
I want validation status visible while editing,
So that I can maintain publish-ready instruction quality.

**Acceptance Criteria:**

**Given** instruction payload contains validation metadata
**When** the instruction is loaded or refreshed
**Then** the UI displays `validation_status`, validation errors, and validation timing
**And** validation UI updates after save or regenerate.

**Given** validation errors exist
**When** the editor reviews them
**Then** the UI presents actionable messages without blocking ongoing editing
**And** does not invent data absent from the contract.

**Source Hints:** `spec/api/openapi.yaml`, `apps/api/app/schemas/instruction.py`

## Epic 9: Screenshots and Anchors

Editors can extract screenshots, inspect anchor context, manage asset versions, and annotate assets directly in the workflow UI.

### Story 9.1: Request Screenshot Extraction and Poll Task

As an editor,
I want to request screenshot extraction at a target timestamp,
So that I can attach visuals to instruction context.

**Acceptance Criteria:**

**Given** the editor submits a contract-valid extraction request
**When** the backend accepts it
**Then** the UI shows task acknowledgement and pending state immediately
**And** the extraction task is pollable to completion.

**Given** the extraction task reaches terminal state
**When** results are available
**Then** the UI surfaces anchor or asset linkage returned by the task
**And** preserves surrounding editor context.

**Source Hints:** `spec/api/openapi.yaml`, `docs/golden-path.md`

### Story 9.2: Inspect Anchor Context and Version Visibility

As an editor,
I want to inspect anchor addressing and active asset context,
So that screenshot references remain understandable across instruction versions.

**Acceptance Criteria:**

**Given** an instruction has anchors
**When** the editor opens anchor details
**Then** block addressing, active asset state, and instruction version context are shown
**And** no-leak not-found behavior is preserved.

**Given** instruction version context changes
**When** anchor mapping is still valid
**Then** the UI preserves anchor references
**And** warns only when user action is required.

**Source Hints:** `spec/api/openapi.yaml`, `_bmad-output/planning-artifacts/ux-design-specification.md`

### Story 9.3: Manage Screenshot Asset Lifecycle

As an editor,
I want to upload, attach, replace, and delete screenshot assets on anchors,
So that visuals stay accurate while preserving deterministic asset state.

**Acceptance Criteria:**

**Given** the editor uploads or replaces an asset through the current contract flows
**When** the operation succeeds
**Then** the UI reflects the new active asset deterministically
**And** duplicate action submission does not create ambiguous state.

**Given** the editor deletes an asset or an operation fails
**When** the response returns
**Then** the UI reflects fallback or preserved active state correctly
**And** surfaces validation or auth errors safely.

**Source Hints:** `spec/api/openapi.yaml`, backend screenshot stories 5.2 to 5.4 in `_bmad-output/implementation-artifacts/`

### Story 9.4: Annotate Screenshot Assets

As an editor,
I want to apply annotation operations to screenshot assets,
So that visuals can communicate key details in the final instructions.

**Acceptance Criteria:**

**Given** the editor submits annotation operations
**When** render completes successfully
**Then** the rendered asset becomes the active asset view
**And** the UI preserves the operation outcome in context.

**Given** the same normalized operations are submitted again or rendering fails
**When** the backend responds
**Then** replay is treated as a successful no-op
**And** render failure leaves current UI state consistent.

**Source Hints:** `spec/api/openapi.yaml`, backend annotation story 5.5 in `_bmad-output/implementation-artifacts/`

## Epic 10: Export Delivery

Editors can request exports, monitor async export state, and securely download completed artifacts.

### Story 10.1: Request Exports and Track Export Status

As an editor,
I want to request `MD_ZIP` and `PDF` exports and track progress,
So that I can prepare shareable deliverables confidently.

**Acceptance Criteria:**

**Given** the editor requests an export for the chosen instruction version
**When** the request is accepted or replayed
**Then** the UI shows export record state transitions clearly
**And** job context remains visible during async processing.

**Given** the export reaches terminal state
**When** status polling updates
**Then** the UI shows `SUCCEEDED` or `FAILED` clearly
**And** failed states expose a retry path aligned to the contract.

**Source Hints:** `spec/api/openapi.yaml`, `docs/golden-path.md`

### Story 10.2: Download Completed Exports Securely

As an editor,
I want download action only when an export is ready,
So that artifact access remains secure and predictable.

**Acceptance Criteria:**

**Given** export status is not `SUCCEEDED`
**When** the editor views or attempts download
**Then** download action is disabled or guarded
**And** readiness guidance is displayed.

**Given** export status is `SUCCEEDED`
**When** the editor requests download
**Then** the frontend uses the signed URL immediately
**And** does not persist the URL in unsafe browser storage.

**Source Hints:** `spec/api/openapi.yaml`, `_bmad-output/planning-artifacts/architecture.md`

## Epic 11: Reliability and Release Readiness

Frontend achieves production-ready async behavior, accessibility, CI quality gates, and safe deployment/telemetry posture.

### Story 11.1: Implement Unified Error, Retry, and Polling Pattern

As an editor,
I want consistent error and async handling across workflows,
So that failures are understandable and recoverable.

**Acceptance Criteria:**

**Given** API or auth errors occur
**When** the UI renders failure states
**Then** `400`, `401`, `404`, `409`, and `502` outcomes follow a shared pattern
**And** no-leak `404` remains generic.

**Given** long-running async actions are active
**When** polling and retry behavior is applied
**Then** retry is bounded and visible
**And** destructive actions are disabled while in-flight.

**Source Hints:** `_bmad-output/planning-artifacts/architecture.md`, `_bmad-output/planning-artifacts/ux-design-specification.md`

### Story 11.2: Achieve Accessibility and Responsive Baseline

As an editor,
I want the interface usable across devices and accessible by keyboard,
So that core workflows remain reliable for diverse users and contexts.

**Acceptance Criteria:**

**Given** keyboard-only interaction
**When** the user navigates primary workflows
**Then** all critical controls are reachable and operable
**And** focus states remain visible.

**Given** desktop, tablet, and mobile status-check contexts
**When** key pages are viewed
**Then** layout remains functional and readable
**And** essential actions remain discoverable.

**Source Hints:** `_bmad-output/planning-artifacts/ux-design-specification.md`

### Story 11.3: Add Frontend Test Automation and BMAD Quality Gates

As a delivery team,
I want automated frontend quality checks,
So that regressions are caught before release and BMAD story execution stays disciplined.

**Acceptance Criteria:**

**Given** frontend changes are introduced
**When** CI runs
**Then** lint, typecheck, and unit tests execute
**And** failures block merge.

**Given** the mock-mode golden path is executed
**When** create, run, edit, screenshot, and export flows are exercised
**Then** the critical path passes end to end
**And** failures emit actionable diagnostics.

**Source Hints:** `docs/golden-path.md`, `_bmad-output/planning-artifacts/architecture.md`

### Story 11.4: Prepare Deployment Config and Safe Telemetry

As a platform team,
I want deployment configuration and telemetry prepared safely,
So that frontend rollout is controlled and observability remains non-sensitive.

**Acceptance Criteria:**

**Given** a release candidate is built
**When** deployment configuration is validated
**Then** API base URL and Firebase runtime settings are environment-driven
**And** the app is deployable to the chosen hosting target.

**Given** telemetry is emitted for key UI actions
**When** events are recorded
**Then** they correlate to job, task, and export identifiers
**And** logs exclude tokens, raw transcript content, and signed URLs.

**Source Hints:** `_bmad-output/planning-artifacts/architecture.md`

## Deferred from MVP

- Export provenance panel
- Publish-readiness summary

## Recommended BMAD Story Creation Order

1. 7.1
2. 7.2
3. 11.1
4. 7.3
5. 7.4
6. 8.1
7. 8.2
8. 8.3
9. 8.4
10. 9.1
11. 9.2
12. 9.3
13. 9.4
14. 10.1
15. 10.2
16. 11.2
17. 11.3
18. 11.4
