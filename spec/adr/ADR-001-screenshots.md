# ADR-001 - Screenshot Extraction, Anchoring, and Annotation Storage

**Status:** Accepted  
**File:** `spec/adr/ADR-001-screenshots.md`  
**Date:** 2026-02-21  
**Owner:** Solution Architecture

---

## 1. Context

Howera generates step-by-step instructions from video. Authors must be able to insert screenshots at specific timestamps, adjust frame selection, annotate images (blur/arrow/marker/pencil), and export the final guide as PDF/MD bundle.

Key requirements:
- Videos may be large (1-10GB+) and in various codecs (H.264/H.265).
- Timestamp-to-frame extraction must be reliable, deterministic, and compatible with on-prem deployments.
- Screenshot insertions must remain stable across Markdown edits.
- Annotation data must be portable across v1/v2/v3 (Firebase to on-prem), and support re-rendering for export.

---

## 2. Decision

We adopt the following decisions:

1. **Server-side frame extraction (ffmpeg).**  
   Screenshots are extracted on the backend (or worker) using ffmpeg, not in the browser.
2. **Stable anchoring via Block IDs (primary) with Char Offset fallback (v1 only).**  
   Each screenshot insertion is linked to a stable Markdown block marker: `<!-- block:<uuid> -->`.  
   If v1 editor cannot enforce block markers reliably, we allow a temporary fallback anchor using character offsets, with migration to Block IDs in v2.
3. **Annotation storage as Operation Log + Rendered Output.**  
   Store annotation edits as structured operations (blur/stroke/arrow/highlight/text) with normalized coordinates, and additionally store a rendered flattened image for fast preview/export.
4. **Immutable base image + versioned derived assets.**  
   The extracted base screenshot is immutable. Any annotation results in a new derived asset version referencing the same base image.

---

## 3. Rationale

### 3.1 Why server-side extraction

- Avoids downloading large videos to clients.
- Ensures consistent frame extraction for different codecs and browsers.
- Works in air-gapped/on-prem environments.
- Centralizes compute and allows GPU/CPU scaling on worker nodes.
- Simplifies security: client never receives raw video bytes beyond upload.

### 3.2 Why Block IDs

- Character offsets are fragile (Markdown edits shift offsets).
- Block IDs provide stable anchors across edits, reformatting, and regeneration.
- Enables deterministic export reconstruction.

### 3.3 Why operation log for annotations

- Portable across storages and stacks (Firestore/Postgres/MinIO).
- Supports auditability (who blurred what, when).
- Supports re-rendering at different resolutions for PDF.
- Enables undo/redo and future collaborative editing.

---

## 4. Alternatives Considered

### A) Client-side screenshot extraction (HTML5 video + canvas)

**Rejected** due to:
- Large video download cost and latency.
- Codec support inconsistency (especially H.265).
- Difficult on-prem constraints (browser GPU decoding differs).
- Poor determinism for exact timestamp-to-frame mapping.

### B) Store only rendered image (no operations)

**Rejected** due to:
- Loss of semantic edit history.
- No re-render at different DPI.
- No undo/redo.
- Harder compliance/audit requirements.

### C) Anchor by Markdown line number / DOM position

**Rejected** due to:
- Highly unstable under edits.
- Breaks under regeneration and formatting.

---

## 5. Detailed Design

### 5.1 Extraction API

**Endpoint:** `POST /jobs/{jobId}/screenshots/extract`

**Request:**
- `timestamp_ms` (required)
- `offset_ms` (optional, default `0`)
- `strategy` (optional): `nearest_keyframe | precise` (default `precise`)
- `format` (optional): `png | jpg` (default `png`)

**Response:**
- `asset_id`
- `image_uri`
- `width`, `height`
- `extracted_at_ms` (effective timestamp used)

**Implementation:**
- Use ffmpeg with accurate seek:
  - For `precise`, use `-ss` after input (slower but accurate).
  - For `nearest_keyframe`, use `-ss` before input (faster but approximate).
- Store output in object storage (Firebase Storage / MinIO).

### 5.2 Markdown Anchoring

#### Primary (Block ID)

Markdown blocks must include markers.

Example:

```md
<!-- block:8b4b9e41-0c7c-4e3d-8d4e-1f9d7f3c2e9a -->
### Step 3 - Open Settings
Click the gear icon.
```

Screenshot anchor links:
- `instruction_id`
- `block_id`
- `timestamp_ms`
- `asset_id`

#### Fallback (v1 only)

Use:
- `char_offset` (integer)
- `selection_hash` (optional checksum)

A migration job in v2 should convert offsets to Block IDs where possible.

### 5.3 Annotation Operation Log

Operation schema (conceptual).

Each operation contains:
- `op_id` (uuid)
- `type` (`blur|stroke|arrow|highlight|text|box`)
- `created_by`
- `created_at`
- `params` (type-specific)
- `normalized_coords` (`0..1` coordinates relative to base image)

Examples:
- **Blur**
  - `rect: {x,y,w,h}`
  - `radius`
- **Arrow**
  - `from: {x,y}`
  - `to: {x,y}`
  - `thickness`
- **Stroke**
  - `points: [{x,y}, ...]`
  - `thickness`
- **Text**
  - `pos: {x,y}`
  - `value`
  - `font_size`

Storage model:
- `base_asset` (immutable)
- `derived_asset` (versioned):
  - `base_asset_id`
  - `operations[]`
  - `rendered_image_uri`
  - `version`

### 5.4 Rendering Strategy

UI uses:
- Base image + overlay operations for interactive editing.

Backend export uses:
- Server-side renderer to produce flattened images at export DPI.

Store both:
- Operations JSON (source of truth).
- Flattened rendered image (performance).

## 6. Consequences

Positive:
- Deterministic extraction and export.
- Portable annotation data across deployment phases.
- Stable anchors across edits.
- Future-proof for collaboration features.

Negative / Trade-offs:
- Requires backend compute for extraction/rendering.
- Needs a Markdown normalization layer to ensure block markers exist.
- Increased storage (base + derived images + ops log).

## 7. Security and Compliance Notes

Access to image URIs must be controlled via signed URLs with TTL.

Audit log should record:
- Screenshot extracted.
- Operations applied (blur especially).
- Exports created.

Ensure PII redaction is performed before export if required by policy.

## 8. Implementation Notes (v1 to v3)

### v1 (Firebase + OpenAI)

- Extraction: run ffmpeg in API container (simple) or small worker.
- Storage: Firebase Storage.
- Anchors: fallback `char_offset` allowed if editor is not block-aware.

### v2 (Hybrid)

Same as v1, but:
- Enforce Block IDs in editor (recommended).
- Local LLM does not change screenshot subsystem.

### v3 (On-prem)

- Extraction: dedicated worker pool (CPU/GPU as needed).
- Storage: MinIO.
- DB: Postgres stores metadata and operation logs.
- Export renderer runs server-side and writes artifacts to MinIO.

## 9. Acceptance Criteria

- Extracted screenshot matches timestamp within configured tolerance.
- User can shift frames forward/back and replace screenshot.
- Block-ID anchors remain stable after Markdown edits and regenerate.
- Annotation operations persist and can be re-rendered deterministically.
- Export uses flattened annotated images (no missing overlays).
