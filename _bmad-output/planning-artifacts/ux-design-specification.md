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
  - 9
  - 10
  - 11
  - 12
  - 13
  - 14
lastStep: 14
workflowType: ux-design
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/implementation-readiness-report-2026-02-22.md
  - docs/golden-path.md
  - docs/dev-setup.md
  - spec/sas.md
  - spec/api/openapi.yaml
---

# UX Design Specification Howera

**Author:** founder  
**Date:** 2026-03-05

---

## Executive Summary

### Project Vision
Howera v1 already delivers the API-first workflow backbone. The frontend phase focuses on turning this deterministic backend into a high-clarity authoring experience where editors can move from upload to published export with confidence, minimal ambiguity, and visible system state.

### Target Users
- Documentation editors producing process and demo guides from recorded videos.
- Operations or QA stakeholders who need traceable export outcomes.
- Teams that require predictable async behavior and audit-friendly workflows.

### Key Design Challenges
- Complex async lifecycle states must be understandable without exposing backend internals.
- Long-running operations (run, regenerate, screenshot extraction, export) require reliable polling and clear progress cues.
- Rich editing with anchors/screenshots must remain stable across instruction versions.
- Failure handling must be actionable while preserving no-leak security posture.

### Design Opportunities
- Treat lifecycle visibility as a first-class UI primitive.
- Make the editor "workflow-aware" (status, transcript context, screenshot anchors, export readiness).
- Build a reusable async task pattern shared across regenerate, screenshot, and export flows.
- Establish a design system that can scale to collaboration and enterprise controls in v2/v3.

## Core User Experience

### Defining Experience
"From raw video to publishable instructions in one continuous workspace." Users should never feel they are jumping between disconnected tools.

### Platform Strategy
- One workspace shell with project, job, and instruction context preserved.
- Progressive disclosure: basic actions first, advanced controls on demand.
- Deterministic state UI mapped directly to backend FSM and task statuses.

### Effortless Interactions
- One-click action affordances for run, regenerate, screenshot extract, and export.
- Inline optimistic feedback for user actions, with explicit server reconciliation states.
- Context-preserving navigation (return to same selection, cursor range, anchor block).

### Critical Success Moments
- First successful draft load after workflow run.
- First successful screenshot insertion aligned to intended timestamp.
- First successful export with visible downloadable artifact.

### Experience Principles
- State clarity over visual novelty.
- Trust through explicit status and provenance.
- Low cognitive load in high-complexity workflows.
- Recoverability by design (retry, resume, no silent failure).

## Desired Emotional Response

### Primary Emotional Goals
- Confidence: "I always know what the system is doing."
- Control: "I can refine and recover without losing work."
- Momentum: "The flow keeps me moving toward publishable output."

### Emotional Journey Mapping
- Start: mild uncertainty while setting up job and upload.
- Middle: growing confidence through visible progress and transcript-backed editing.
- End: completion satisfaction when export succeeds and is downloadable.

### Micro-Emotions
- Relief when retries/replays are handled safely.
- Assurance when task progress updates are timely and accurate.
- Ownership when edits and screenshot decisions are explicit and reversible.

### Design Implications
- Always expose current lifecycle state and "what happens next".
- Show polling freshness and last update timestamps.
- Offer deterministic empty/error states with direct remediation actions.

### Emotional Design Principles
- Never hide system uncertainty.
- Prefer explicitness to magic.
- Fail clearly and recover quickly.

## UX Pattern Analysis & Inspiration

### Inspiring Products Analysis
- Notion: calm information density and block-based editing model.
- Linear: predictable async feedback and task-oriented status language.
- Figma: contextual tool surfaces that reduce mode switching.

### Transferable UX Patterns
- Context panels that can be opened without breaking editing flow.
- Action bars with primary lifecycle controls.
- Unified notifications with persistent task history.

### Anti-Patterns to Avoid
- Modal-heavy flows for routine actions.
- Ambiguous status labels (e.g., generic "processing").
- Hidden failures requiring users to inspect logs.

### Design Inspiration Strategy
Adopt a "calm control center" direction: structured layout, clear hierarchy, strong status semantics, and restrained visual style.

## Design System Foundation

### 1.1 Design System Choice
Tailwind CSS + shadcn/ui + Radix primitives.

### Rationale for Selection
- Fast implementation velocity for product teams.
- Accessible primitives and predictable component behavior.
- Easy theming and tokenization without deep lock-in.

### Implementation Approach
- Token-first design foundation (`color`, `type`, `spacing`, `radius`, `motion`).
- Component library with documented states: default, loading, success, error, disabled.
- Shared async components: `TaskBadge`, `StateTimeline`, `StatusToast`, `RetryAction`.

### Customization Strategy
- Keep custom components minimal and domain-driven.
- Reserve custom visuals for editor, timeline, and screenshot workflows.

## 2. Core User Experience

### 2.1 Defining Experience
A single editor-centric surface that combines transcript context, markdown editing, screenshot management, and export control.

### 2.2 User Mental Model
- Project contains jobs.
- Job moves through lifecycle states.
- Job produces transcript and instruction artifacts.
- Instruction evolves through versions and anchors.
- Exports are reproducible snapshots of instruction + assets.

### 2.3 Success Criteria
- User can complete golden path without leaving the web app.
- User can explain current state and next valid action at any point.
- User can recover from transient failures without support intervention.

### 2.4 Novel UX Patterns
- Lifecycle-aware command bar bound to valid next actions.
- Transcript-guided regeneration with selection provenance preview.
- Screenshot anchor inspector with version lineage visibility.

### 2.5 Experience Mechanics
- Predictive UI hints derived from contract-valid transitions.
- Polling orchestration with adaptive intervals by task state.
- Consistent toast + inline state messaging across all async actions.

## Visual Design Foundation

### Color System
- Base neutrals for editing comfort and long-session readability.
- Semantic colors: success, warning, error, info with AA contrast targets.
- Status mapping palette aligned to backend lifecycle phases.

### Typography System
- Heading: "Space Grotesk".
- Body/UI: "IBM Plex Sans".
- Monospace snippets (IDs, states, keys): "IBM Plex Mono".

### Spacing & Layout Foundation
- 8px spacing scale.
- Three-zone layout: global nav, workspace main, context side panel.
- Sticky action zones for primary lifecycle commands.

### Accessibility Considerations
- Keyboard-first command activation for all primary actions.
- Focus-visible styling with strong contrast.
- No color-only status communication; icon + label + tooltip required.

## Design Direction Decision

### Design Directions Explored
- Direction A: utilitarian dashboard (high density, low emotion).
- Direction B: editorial studio (balanced density, guidance-first).
- Direction C: immersive canvas (visual-first, complex interactions).

### Chosen Direction
Direction B: editorial studio.

### Design Rationale
Best fit for documentation workflows: enough structure for operational confidence while preserving writing focus.

### Implementation Approach
- Dashboard + editor split, with collapsible side panels.
- Persistent status rail and task center.
- Domain-specific toolbars for regenerate, screenshot, and export.

## User Journey Flows

### Journey 1: Project to Draft
- Create project -> create job -> confirm upload -> run workflow.
- Observe lifecycle progression from CREATED to DRAFT_READY.
- Open generated instruction and transcript context.

### Journey 2: Refine with Transcript + Regenerate
- Select text range in instruction.
- Request targeted regenerate and poll task.
- Resolve output into latest instruction version.

### Journey 3: Screenshot Lifecycle
- Extract screenshot at timestamp.
- Replace/delete/upload/annotate while preserving anchor linkage.
- Confirm active asset in context of instruction block.

### Journey 4: Publish Export
- Request MD_ZIP/PDF export.
- Monitor export task status.
- Download artifact after SUCCEEDED.

### Journey Patterns
- Every async request returns immediate acknowledgement + task identity.
- Every task view supports replay-safe refresh and explicit terminal outcomes.

### Flow Optimization Principles
- Keep editing context stable during async updates.
- Minimize navigation jumps between list/detail/editor.
- Surface primary next action in each state.

## Component Strategy

### Design System Components
- Buttons, inputs, menus, dialogs, tabs, cards, badges, toasts, tables.
- Form validation and helper text primitives.

### Custom Components
- JobLifecycleTimeline
- TaskStatusPanel
- TranscriptSegmentRail
- InstructionEditorShell
- AnchorAssetInspector
- ExportProvenanceCard

### Component Implementation Strategy
- Build domain components on top of design-system primitives.
- Enforce prop contracts for loading/error/empty states.
- Co-locate component tests with state fixtures.

### Implementation Roadmap
- Wave 1: app shell, auth, project/job screens.
- Wave 2: instruction editor + transcript context + regenerate flow.
- Wave 3: screenshot/anchor management.
- Wave 4: export center + provenance view + hardening.

## UX Consistency Patterns

### Button Hierarchy
- Primary: single action per view state.
- Secondary: supporting actions.
- Tertiary/ghost: low-priority utilities.

### Feedback Patterns
- Immediate toast for action acceptance.
- Inline status blocks for long-running tasks.
- Persistent event log for task lifecycle history.

### Form Patterns
- Validate as user types where safe; otherwise on submit.
- Contract-shaped error language mapped to API responses.
- Preserve unsaved editor state and show clear conflict handling.

### Navigation Patterns
- Breadcrumb + workspace context label.
- Left rail for project/job hierarchy.
- Right panel for details/provenance/anchor metadata.

### Additional Patterns
- Empty states with a single, clear first action.
- Error states with retry and fallback guidance.
- Polling indicator with last synced timestamp.

## Responsive Design & Accessibility

### Responsive Strategy
- Desktop-first for core authoring.
- Tablet support for review and light edits.
- Mobile support for status checks and download actions.

### Breakpoint Strategy
- `sm`: status and lightweight browsing.
- `md`: split-pane review/edit.
- `lg+`: full workspace with side panels.

### Accessibility Strategy
- WCAG 2.2 AA baseline.
- Semantic landmarks and heading hierarchy.
- Full keyboard access for command bar and editor controls.
- ARIA for dynamic status regions and task updates.

### Testing Strategy
- Component-level accessibility tests with automated checks.
- End-to-end keyboard traversal for golden journeys.
- Visual regression snapshots for state-critical screens.

### Implementation Guidelines
- No interaction without visible focus state.
- No blocking spinner without contextual message.
- No destructive action without explicit confirmation and undo path when feasible.

## Workflow Completion

UX design workflow is complete for the frontend phase after API-first v1 delivery. This specification is ready to feed the next BMAD workflows:
- `Create Architecture` for frontend technical decisions.
- `Create Epics and Stories` for frontend implementation slicing.
- `Check Implementation Readiness` before frontend build sprint kickoff.
