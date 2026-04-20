---
stepsCompleted:
  - 1
  - 2
  - 3
  - 4
  - 5
  - 6
  - 7
  - 8
workflowType: architecture
project_name: Howera
user_name: founder
date: 2026-03-05
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - docs/golden-path.md
  - docs/dev-setup.md
  - spec/sas.md
  - spec/api/openapi.yaml
---

# Architecture Decision Document

## Project Context Analysis

### Requirements Overview
Howera has completed API-first v1 delivery (epics 1-6 done). The next phase is a frontend application that operationalizes existing API capabilities end-to-end:
- project and job management
- workflow run and lifecycle visibility
- transcript-backed instruction editing and regenerate task flows
- screenshot and anchor lifecycle operations
- export request, status, and secure download flows

The frontend must consume existing OpenAPI endpoints as-is for v1 parity and avoid introducing contract drift.

### Technical Constraints & Dependencies
- Backend contract source of truth: `spec/api/openapi.yaml`.
- Authentication model: bearer token compatible with existing API auth middleware.
- Async behavior: polling/task-driven UX for regenerate, screenshot, and export.
- Security baseline: no secrets in client logs, strict handling of signed URLs.
- Existing repo context: backend only (`apps/api`); frontend app will be introduced as new app surface.

### Cross-Cutting Concerns Identified
- Consistent async state UX across multiple domains.
- Ownership/no-leak behavior reflected in error handling UX.
- Accessibility baseline for all user-facing surfaces.
- Observability correlation between UI actions and API task IDs.

## Starter Template Evaluation

### Primary Technology Domain
Web frontend for workflow-heavy authoring product.

### Starter Options Considered
1. Next.js (App Router, TypeScript) + Tailwind
2. Vite + React + React Router
3. Remix

### Selected Starter: Next.js + TypeScript
`npx create-next-app@latest apps/web --ts --eslint --src-dir --app --import-alias "@/*"`

Selection rationale:
- Mature routing/data-fetching ergonomics.
- Strong ecosystem for component systems and accessibility tooling.
- Smooth deploy path for Firebase-hosted frontend target.

## Core Architectural Decisions

### Decision Priority Analysis
- Must decide now: app framework, auth/session strategy, API client strategy, async task UX pattern, component system, deployment model.
- Can defer: advanced collaboration features, offline mode, multi-role UI permissions.

### Data Architecture
- API remains system of record.
- Frontend state split:
  - Server state via TanStack Query.
  - Local UI state via lightweight store (Zustand or React context per feature).
- Contract types generated from OpenAPI where feasible; fallback to typed adapters around fetch client.
- Cache keys aligned to API resource identities (`projectId`, `jobId`, `instructionId`, `taskId`, `exportId`).

### Authentication & Security
- Firebase-authenticated user obtains bearer token.
- Token injected in API client layer only (single source for auth headers).
- No raw transcript or signed URL logging in browser console telemetry.
- Signed download URLs stored ephemerally in memory and never persisted to local storage.

### API & Communication Patterns
- Frontend calls FastAPI endpoints directly through a thin API client module.
- Standardized API response handler maps contract errors to UX-safe messages.
- Async operations share a common polling hook with task-specific selectors.
- Retry/backoff is client-side bounded and consistent with backend idempotency semantics.

### Frontend Architecture
- Route groups by domain:
  - `/projects`
  - `/projects/[projectId]/jobs`
  - `/jobs/[jobId]`
  - `/instructions/[instructionId]`
  - `/exports/[exportId]` (or panel-level detail)
- Shared workspace shell with three regions: navigation, main editor/content, context panel.
- Domain modules:
  - `projects`, `jobs`, `instructions`, `screenshots`, `exports`, `tasks`, `auth`.
- Reusable async primitives:
  - `TaskStatusPanel`, `LifecycleTimeline`, `StatusBadge`, `RetryAction`.

### Infrastructure & Deployment
- Frontend build output deployed to Firebase Hosting (v1-aligned).
- Runtime API base URL provided through environment config.
- CI checks for frontend:
  - lint/typecheck/unit tests
  - accessibility smoke checks
  - E2E golden-path subset against mock-capable backend

### Decision Impact Analysis
- Chosen stack optimizes developer velocity and long-term maintainability.
- Shared async/task patterns reduce UX inconsistency and defect rate.
- Contract-generated typing reduces runtime integration errors.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined
- Naming patterns
- Structure patterns
- Format patterns
- Communication patterns
- Process patterns

### Naming Patterns
- Feature-first directories (`features/jobs`, `features/exports`).
- Hook naming: `use<Domain><Action>` (e.g., `useJobRun`, `useExportStatus`).
- Component naming: domain + role (`JobLifecycleTimeline`).

### Structure Patterns
- `apps/web/src/app` for routes/layout.
- `apps/web/src/features` for domain logic.
- `apps/web/src/shared` for UI kit, api client, utils, constants.
- `apps/web/tests` for integration/e2e support fixtures.

### Format Patterns
- TypeScript strict mode required.
- Zod schema wrappers at API boundaries where runtime validation adds safety.
- UI copy follows explicit action/state language (no ambiguous status text).

### Communication Patterns
- API errors mapped to typed `AppError` with user-safe message + debug metadata (non-sensitive).
- Polling status updates include last refreshed timestamp in UI.
- Toasts for action acknowledgement, inline state blocks for long-running operations.

### Process Patterns
- Contract-first FE changes: update generated types when OpenAPI changes.
- Every feature story includes empty/loading/error/success/resume states.
- Frontend changes reference corresponding API endpoints in acceptance checks.

### Enforcement Guidelines
- PR checklist requires accessibility and async-state behavior verification.
- Avoid direct fetch usage outside shared API client.
- No business logic in presentational components.

### Pattern Examples
- `useTaskPolling(taskId, selector)` reusable hook.
- `DomainActionButton` pattern with pending/disabled/retry handling.

## Project Structure & Boundaries

### Complete Project Directory Structure
```text
apps/
  api/
  web/
    src/
      app/
        (workspace)/
          projects/
          jobs/
          instructions/
      features/
        auth/
        projects/
        jobs/
        instructions/
        screenshots/
        exports/
        tasks/
      shared/
        api/
        ui/
        hooks/
        lib/
        styles/
    tests/
      unit/
      integration/
      e2e/
```

### Architectural Boundaries
- `app/` composes pages and route-level concerns.
- `features/` contains domain logic and API integration.
- `shared/` contains reusable primitives only.
- Backend-specific assumptions must remain in API client adapters, not UI components.

### Requirements to Structure Mapping
- Job lifecycle UX -> `features/jobs`, `features/tasks`.
- Instruction authoring/regenerate -> `features/instructions`.
- Screenshot lifecycle -> `features/screenshots`.
- Export flows -> `features/exports`.

### Integration Points
- FastAPI endpoints from v1 OpenAPI.
- Firebase auth/session infrastructure.
- Optional telemetry provider via shared event interface.

### File Organization Patterns
- One feature, one API module, one query-key module, one UI entry module.
- Avoid circular dependencies between features.

### Development Workflow Integration
- Story implementation flow remains BMAD-aligned (`Create Story -> Dev Story -> Code Review`).
- Frontend stories must include endpoint contract assertions in test strategy.

## Architecture Validation Results

### Coherence Validation ✅
Architecture aligns with API-first backend decisions and frontend UX intent without introducing conflicting domain models.

### Requirements Coverage Validation ✅
All frontend-facing journeys (project/job/run/edit/screenshot/export) are mapped to architecture modules and route surfaces.

### Implementation Readiness Validation ✅
Stack, boundaries, state model, and CI expectations are concrete enough for story decomposition and sprint kickoff.

### Gap Analysis Results
- Needs follow-up: exact auth token acquisition flow in browser runtime environments.
- Needs follow-up: final decision on generated API client toolchain.

### Validation Issues Addressed
- Avoided introducing new backend contract assumptions.
- Kept architecture scoped to frontend phase while reusing v1 backend invariants.

### Architecture Completeness Checklist
- [x] Context and constraints documented
- [x] Starter strategy selected
- [x] Core technical decisions recorded
- [x] Consistency patterns defined
- [x] Project structure and boundaries mapped
- [x] Validation and readiness status captured

### Architecture Readiness Assessment
Ready for `Create Epics and Stories` for frontend implementation.

### Implementation Handoff
Immediate next BMAD step: generate frontend epics/stories referencing this architecture and the UX specification.
