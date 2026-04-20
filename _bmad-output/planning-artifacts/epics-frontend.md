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
  - spec/api/openapi.yaml
---

# Howera - Frontend Epic Breakdown

## Overview

This document provides the frontend epic and story breakdown for the post-v1 phase, decomposing existing API capabilities into implementable web application stories.

## Requirements Inventory

### Functional Requirements

FE-FR-001: Authenticated editor can access protected frontend workspace using valid bearer session.
FE-FR-002: Editor can create/read projects and jobs through frontend UI while preserving ownership boundaries.
FE-FR-003: Editor can confirm upload and run workflow from job detail UI.
FE-FR-004: Editor can view job lifecycle and callback-driven status progression clearly.
FE-FR-005: Editor can retrieve and edit instruction markdown with version conflict-safe UX.
FE-FR-006: Editor can view transcript segments and use them during editing.
FE-FR-007: Editor can request targeted regenerate and monitor task status to completion.
FE-FR-008: Editor can execute screenshot extraction flow and monitor task outcomes.
FE-FR-009: Editor can replace, delete, upload, and annotate screenshot assets on anchors.
FE-FR-010: Editor can request export generation, monitor status, and retrieve secure download links.
FE-FR-011: Editor can view provenance and operational metadata relevant to publish confidence.
FE-FR-012: Frontend surfaces consistent error/recovery states for API failures, auth failures, and async task failures.

### NonFunctional Requirements

FE-NFR-001: Frontend must satisfy WCAG 2.2 AA baseline for in-scope pages.
FE-NFR-002: Frontend must preserve deterministic UI-state mapping to backend contract states.
FE-NFR-003: Frontend must avoid logging secrets, raw transcript payloads, or signed URL artifacts.
FE-NFR-004: Frontend must provide responsive behavior for desktop/tablet and support mobile status checks.
FE-NFR-005: CI checks must include lint, typecheck, unit tests, and E2E golden-path subset.
FE-NFR-006: Polling/retry behavior must be bounded and transparent to users.

### Additional Requirements

- Backend OpenAPI contract remains source of truth for request/response behavior.
- No frontend-only business logic may bypass backend FSM or idempotency rules.
- Frontend architecture follows `architecture.md` and UX flows from `ux-design-specification.md`.
- New UI work must remain compatible with Firebase-hosted deployment model in v1 scope.

### FR Coverage Map

FE-FR-001: Epic 7 - Frontend foundation and authentication
FE-FR-002: Epic 7 - Workspace/project/job navigation and CRUD surface
FE-FR-003: Epic 7 - Job intake and run controls
FE-FR-004: Epic 7 - Lifecycle timeline and status visibility
FE-FR-005: Epic 8 - Instruction editor and version-safe updates
FE-FR-006: Epic 8 - Transcript context and retrieval UX
FE-FR-007: Epic 8 - Regenerate request and task polling UX
FE-FR-008: Epic 9 - Screenshot extraction submit/poll UX
FE-FR-009: Epic 9 - Screenshot asset lifecycle and anchor tools
FE-FR-010: Epic 10 - Export create/status/download UX
FE-FR-011: Epic 10 - Provenance and publish confidence panels
FE-FR-012: Epic 11 - Reliability hardening and error-state consistency

## Epic List

### Epic 7: Frontend Foundation and Workspace Navigation
Editors can authenticate, navigate project/job context, and trigger run lifecycle controls with clear status visibility.
**FRs covered:** FE-FR-001, FE-FR-002, FE-FR-003, FE-FR-004

### Epic 8: Instruction Authoring and Regeneration Experience
Editors can author instructions with transcript context, handle versioning safely, and run targeted regenerate flows.
**FRs covered:** FE-FR-005, FE-FR-006, FE-FR-007

### Epic 9: Screenshot and Anchor Authoring Experience
Editors can manage screenshot extraction and full anchor asset lifecycle operations directly in the UI.
**FRs covered:** FE-FR-008, FE-FR-009

### Epic 10: Export and Publish Experience
Editors can create exports, track completion, obtain download links, and inspect provenance for publish confidence.
**FRs covered:** FE-FR-010, FE-FR-011

### Epic 11: Frontend Reliability, Accessibility, and Release Readiness
Frontend achieves production quality through accessibility compliance, deterministic async behaviors, and release gates.
**FRs covered:** FE-FR-012, FE-NFR-001, FE-NFR-002, FE-NFR-003, FE-NFR-004, FE-NFR-005, FE-NFR-006

## Epic 7: Frontend Foundation and Workspace Navigation

Editors can authenticate, navigate project/job context, and trigger run lifecycle controls with clear status visibility.

### Story 7.1: Initialize Frontend App Shell and Design Tokens

As an editor,
I want a stable frontend shell with shared layout and tokenized styling,
So that all product flows feel consistent and implementation can scale.

**Acceptance Criteria:**

**Given** frontend app bootstrap is complete
**When** user opens workspace routes
**Then** shared app shell renders navigation, workspace area, and context panel regions
**And** typography/color/spacing tokens are applied from a central theme definition.

**Given** component library setup is complete
**When** developers add new screens
**Then** base primitives are reused instead of ad-hoc styles
**And** accessibility defaults are enabled on shared components.

### Story 7.2: Implement Auth Session and Protected Routing

As an editor,
I want protected routes to require valid authentication,
So that only authorized users can access workspace operations.

**Acceptance Criteria:**

**Given** user is unauthenticated
**When** they access protected routes
**Then** they are redirected to sign-in flow
**And** no protected API calls are executed.

**Given** user has valid session token
**When** they access workspace routes
**Then** API requests include bearer token
**And** auth failures show recoverable re-auth UX.

### Story 7.3: Build Projects and Jobs Workspace Screens

As an editor,
I want to create and browse my projects and jobs,
So that I can manage workflow work items from the UI.

**Acceptance Criteria:**

**Given** editor creates project/job from UI
**When** request succeeds
**Then** lists refresh with newly created records
**And** identifiers/status fields are shown contract-consistently.

**Given** ownership access is denied or item is absent
**When** editor navigates to project/job detail
**Then** UI shows no-leak not-found state
**And** does not expose cross-owner metadata.

### Story 7.4: Add Job Intake Controls and Lifecycle Timeline

As an editor,
I want to confirm upload, run workflow, and observe lifecycle progression,
So that I understand processing state and next valid actions.

**Acceptance Criteria:**

**Given** job is `CREATED`
**When** editor confirms upload
**Then** UI transitions to `UPLOADED` state view
**And** run control becomes enabled.

**Given** run is requested
**When** backend transitions lifecycle states
**Then** timeline updates with current status and timestamps
**And** terminal/error states include explicit recovery actions.

## Epic 8: Instruction Authoring and Regeneration Experience

Editors can author instructions with transcript context, handle versioning safely, and run targeted regenerate flows.

### Story 8.1: Implement Instruction Editor with Version-Safe Save

As an editor,
I want to edit instruction markdown and save safely,
So that I can refine generated content without accidental overwrite.

**Acceptance Criteria:**

**Given** instruction is loaded
**When** editor updates markdown and saves
**Then** latest version metadata is shown
**And** success state confirms persisted update.

**Given** backend reports version conflict
**When** save fails
**Then** UI presents conflict message with reload/merge options
**And** unsaved local content remains recoverable.

### Story 8.2: Add Transcript Context Panel

As an editor,
I want transcript segments alongside instruction editing,
So that I can align edits with source audio context.

**Acceptance Criteria:**

**Given** transcript exists for job
**When** editor opens transcript panel
**Then** segment list renders with timestamps and text
**And** panel interactions do not reset editor state.

**Given** transcript is unavailable or still processing
**When** panel is opened
**Then** UI shows clear pending/empty state
**And** offers refresh guidance.

### Story 8.3: Implement Regenerate Request and Polling UX

As an editor,
I want to regenerate selected instruction fragments,
So that I can improve targeted sections without rerunning full workflow.

**Acceptance Criteria:**

**Given** editor selects valid range and submits regenerate
**When** backend accepts request
**Then** UI shows task creation acknowledgement
**And** task status polling starts automatically.

**Given** regenerate task completes or fails
**When** polling reaches terminal state
**Then** UI surfaces result summary
**And** failed states expose retry path without data loss.

### Story 8.4: Surface Structural Validation Status in Editor

As an editor,
I want structural validation results visible during editing,
So that I can maintain publish-ready instruction quality.

**Acceptance Criteria:**

**Given** instruction is loaded
**When** validation metadata exists
**Then** editor displays current validation status
**And** violations are explained with actionable hints.

**Given** validation status changes after save/regenerate
**When** response is received
**Then** UI updates status in-place
**And** does not require full page refresh.

## Epic 9: Screenshot and Anchor Authoring Experience

Editors can manage screenshot extraction and full anchor asset lifecycle operations directly in the UI.

### Story 9.1: Implement Screenshot Extraction Flow

As an editor,
I want to request screenshot extraction at target timestamp,
So that I can attach visuals to instruction context.

**Acceptance Criteria:**

**Given** editor submits extraction request with valid parameters
**When** backend accepts the request
**Then** UI shows task ID and pending status
**And** extraction progress is trackable.

**Given** extraction task succeeds
**When** outcome is available
**Then** active anchor asset metadata is displayed
**And** editor can insert/use asset contextually.

### Story 9.2: Implement Asset Replace/Delete/Upload Attach UX

As an editor,
I want to manage screenshot asset versions on anchors,
So that I can keep visuals accurate while preserving lifecycle traceability.

**Acceptance Criteria:**

**Given** editor chooses replace/delete/upload action
**When** operation succeeds
**Then** anchor active asset view updates deterministically
**And** operation history is visible to the user.

**Given** operation fails due to validation or auth issues
**When** error is returned
**Then** UI maps error to clear user-safe feedback
**And** current active asset state remains consistent.

### Story 9.3: Implement Annotation Workflow UX

As an editor,
I want to annotate screenshot assets,
So that visuals can communicate key UI details.

**Acceptance Criteria:**

**Given** editor submits annotation operations
**When** render completes
**Then** updated rendered asset appears as active asset
**And** operation set is persistently associated with anchor.

**Given** repeated identical operation set is submitted
**When** backend deduplicates/replays
**Then** UI handles replay as successful no-op
**And** does not duplicate visual artifacts.

### Story 9.4: Add Anchor Context and Cross-Version Visibility

As an editor,
I want to understand anchor mapping across instruction versions,
So that screenshot references remain stable during edits.

**Acceptance Criteria:**

**Given** anchor has addressing metadata
**When** editor inspects anchor details
**Then** block-level addressing and active asset are clearly shown
**And** version context is visible.

**Given** instruction version changes
**When** anchor linkage is still valid
**Then** UI preserves anchor references
**And** warns only when mapping requires user action.

## Epic 10: Export and Publish Experience

Editors can create exports, track completion, obtain download links, and inspect provenance for publish confidence.

### Story 10.1: Build Export Request and Status Tracking UI

As an editor,
I want to request PDF/MD_ZIP exports and track progress,
So that I can prepare shareable deliverables confidently.

**Acceptance Criteria:**

**Given** editor requests export format
**When** request is accepted
**Then** export record appears with `REQUESTED`/`RUNNING` progression
**And** job context stays visible.

**Given** export reaches terminal status
**When** status polling updates
**Then** UI shows `SUCCEEDED` or `FAILED` clearly
**And** failed outcome provides retry action.

### Story 10.2: Implement Secure Download UX

As an editor,
I want download action only when export is ready,
So that artifact access remains secure and predictable.

**Acceptance Criteria:**

**Given** export status is not `SUCCEEDED`
**When** editor attempts download
**Then** download action is disabled or guarded
**And** readiness guidance is displayed.

**Given** export is `SUCCEEDED`
**When** editor requests download URL
**Then** time-limited URL is obtained and used immediately
**And** URL is not persisted in unsafe storage.

### Story 10.3: Surface Export Provenance Details

As an editor,
I want provenance details for completed exports,
So that I can trust reproducibility and audit traceability.

**Acceptance Criteria:**

**Given** export detail is opened
**When** provenance metadata exists
**Then** instruction version, screenshot set identity, and timestamps are displayed
**And** values match backend payload.

**Given** provenance fields are unavailable
**When** export detail loads
**Then** UI displays graceful placeholder state
**And** does not fabricate metadata.

### Story 10.4: Add Publish Readiness Summary

As an editor,
I want one place that summarizes readiness to publish,
So that I can verify completion conditions quickly.

**Acceptance Criteria:**

**Given** job has at least one successful export
**When** editor views publish summary
**Then** `DONE` semantics are clearly explained
**And** latest successful artifacts are linked.

**Given** no successful export exists
**When** summary is viewed
**Then** readiness is shown as incomplete
**And** next required action is surfaced.

## Epic 11: Frontend Reliability, Accessibility, and Release Readiness

Frontend achieves production quality through accessibility compliance, deterministic async behaviors, and release gates.

### Story 11.1: Implement Consistent Error and Recovery Patterns

As an editor,
I want consistent error handling across all workflows,
So that failures are understandable and recoverable.

**Acceptance Criteria:**

**Given** API/async/auth errors occur
**When** UI renders error states
**Then** error messaging follows shared pattern language
**And** each state includes clear retry or recovery action.

**Given** transient network failures occur
**When** polling/request retries are attempted
**Then** retry behavior is bounded and visible
**And** UI prevents duplicate destructive actions.

### Story 11.2: Achieve Accessibility and Responsive Baseline

As an editor,
I want the interface to be accessible and usable across devices,
So that core workflows are reliable for diverse users and contexts.

**Acceptance Criteria:**

**Given** keyboard-only interaction
**When** navigating primary workflows
**Then** all actionable controls are reachable and operable
**And** focus states are always visible.

**Given** viewport changes across desktop/tablet/mobile
**When** viewing key pages
**Then** layout remains functional and readable
**And** essential actions stay discoverable.

### Story 11.3: Add Frontend Test Automation and Quality Gates

As a delivery team,
I want automated frontend quality checks,
So that regressions are caught before release.

**Acceptance Criteria:**

**Given** CI pipeline runs
**When** frontend changes are introduced
**Then** lint, typecheck, and unit tests execute
**And** failures block merge.

**Given** golden-path E2E suite runs in mock mode
**When** critical journeys are executed
**Then** create->run->edit->screenshot->export flow passes
**And** failures include actionable diagnostics.

### Story 11.4: Prepare Deployment and Observability for Frontend

As a platform team,
I want frontend deployment and telemetry readiness,
So that production rollout is controlled and measurable.

**Acceptance Criteria:**

**Given** release candidate is built
**When** deployment pipeline executes
**Then** environment configuration for API/auth endpoints is validated
**And** build artifact is deployable to target hosting.

**Given** users perform key actions
**When** telemetry is emitted
**Then** non-sensitive events correlate with task/job identifiers
**And** logs exclude secrets and raw transcript content.
