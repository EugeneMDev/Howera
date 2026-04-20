"use client";

import React, { useEffect, useRef, useState } from "react";

import type { useInstructionAnchors } from "@/features/screenshots/anchor-hooks";
import {
  buildAnnotationOperations,
  changeAnnotationDraftType,
  createAnnotationDraft,
  summarizeAnnotationDraft,
  type AnnotationDraft,
} from "@/features/screenshots/annotations";
import type { ScreenshotAssetLifecycleState } from "@/features/screenshots/asset-hooks";
import {
  applyAnchorAssetPreview,
  describeAnchorResolution,
  findActiveAnchorAsset,
  formatAnchorAddressing,
  getAnchorResolutionTone,
} from "@/features/screenshots/anchors";
import {
  isScreenshotTaskTerminal,
  type AnnotationOperationType,
  type ScreenshotFormat,
  type ScreenshotStrategy,
} from "@/features/screenshots/api";
import { normalizeScreenshotUploadMimeType } from "@/features/screenshots/asset-lifecycle";
import {
  createScreenshotIdempotencyKey,
  describeScreenshotPolling,
  getScreenshotTaskStatusTone,
} from "@/features/screenshots/extraction";
import { formatDateTime } from "@/shared/lib/format-date";
import { EmptyState, ErrorState, LoadingState } from "@/shared/ui/async-state";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { StatusPill } from "@/shared/ui/status-pill";
import { Textarea } from "@/shared/ui/textarea";

interface InstructionAnchorPanelProps {
  anchorsState: ReturnType<typeof useInstructionAnchors>;
  currentInstructionVersion: number;
  jobId: string;
  latestServerVersion: number;
  lifecycle: ScreenshotAssetLifecycleState;
}

const FORMAT_OPTIONS: ScreenshotFormat[] = ["png", "jpg", "webp"];
const STRATEGY_OPTIONS: ScreenshotStrategy[] = ["precise", "nearest_keyframe"];
const ANNOTATION_OPERATION_OPTIONS: AnnotationOperationType[] = ["arrow", "blur", "marker", "pencil"];
const ACCEPTED_UPLOAD_TYPES = "image/png,image/jpeg,image/webp";

function formatAnnotationOperationLabel(opType: AnnotationOperationType): string {
  if (opType === "arrow") {
    return "Arrow";
  }

  if (opType === "blur") {
    return "Blur";
  }

  if (opType === "marker") {
    return "Marker";
  }

  return "Pencil";
}

function renderTraceValue(value: unknown): string {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }

  return JSON.stringify(value);
}

function renderFeedbackCard(
  feedback: { description: string; title: string; tone: "danger" | "info" | "success" | "warning" },
  onDismiss: () => void,
) {
  const toneClass =
    feedback.tone === "success"
      ? "bg-[var(--status-success-soft)] text-[var(--status-success)]"
      : feedback.tone === "warning"
        ? "bg-[var(--status-warning-soft)] text-[var(--status-warning)]"
        : feedback.tone === "danger"
          ? "bg-[var(--status-danger-soft)] text-[var(--status-danger)]"
          : "bg-[var(--status-info-soft)] text-[var(--status-info)]";

  return (
    <div className={`rounded-[var(--radius-card)] px-4 py-4 ${toneClass}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="display-title text-lg font-semibold">{feedback.title}</h3>
          <p className="mt-2 text-sm leading-6">{feedback.description}</p>
        </div>
        <Button size="compact" variant="ghost" onClick={onDismiss}>
          Dismiss
        </Button>
      </div>
    </div>
  );
}

function renderAnnotationDraftFields({
  disabled,
  draft,
  onChange,
}: {
  disabled: boolean;
  draft: AnnotationDraft;
  onChange: (nextDraft: AnnotationDraft) => void;
}) {
  if (draft.op_type === "blur") {
    return (
      <div className="grid gap-3 md:grid-cols-2">
        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">X</span>
          <Input
            disabled={disabled}
            inputMode="decimal"
            name={`${draft.id}-x`}
            onChange={(event) => onChange({ ...draft, x: event.currentTarget.value })}
            placeholder="120"
            type="number"
            value={draft.x}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Y</span>
          <Input
            disabled={disabled}
            inputMode="decimal"
            name={`${draft.id}-y`}
            onChange={(event) => onChange({ ...draft, y: event.currentTarget.value })}
            placeholder="64"
            type="number"
            value={draft.y}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Width</span>
          <Input
            disabled={disabled}
            inputMode="decimal"
            name={`${draft.id}-width`}
            onChange={(event) => onChange({ ...draft, width: event.currentTarget.value })}
            placeholder="240"
            type="number"
            value={draft.width}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Height</span>
          <Input
            disabled={disabled}
            inputMode="decimal"
            name={`${draft.id}-height`}
            onChange={(event) => onChange({ ...draft, height: event.currentTarget.value })}
            placeholder="120"
            type="number"
            value={draft.height}
          />
        </label>

        <label className="block md:col-span-2">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
            Blur radius
          </span>
          <Input
            disabled={disabled}
            inputMode="decimal"
            name={`${draft.id}-radius`}
            onChange={(event) => onChange({ ...draft, radius: event.currentTarget.value })}
            placeholder="8"
            type="number"
            value={draft.radius}
          />
        </label>
      </div>
    );
  }

  if (draft.op_type === "arrow") {
    return (
      <div className="grid gap-3 md:grid-cols-2">
        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Start X</span>
          <Input
            disabled={disabled}
            inputMode="decimal"
            name={`${draft.id}-x1`}
            onChange={(event) => onChange({ ...draft, x1: event.currentTarget.value })}
            placeholder="120"
            type="number"
            value={draft.x1}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Start Y</span>
          <Input
            disabled={disabled}
            inputMode="decimal"
            name={`${draft.id}-y1`}
            onChange={(event) => onChange({ ...draft, y1: event.currentTarget.value })}
            placeholder="120"
            type="number"
            value={draft.y1}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">End X</span>
          <Input
            disabled={disabled}
            inputMode="decimal"
            name={`${draft.id}-x2`}
            onChange={(event) => onChange({ ...draft, x2: event.currentTarget.value })}
            placeholder="320"
            type="number"
            value={draft.x2}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">End Y</span>
          <Input
            disabled={disabled}
            inputMode="decimal"
            name={`${draft.id}-y2`}
            onChange={(event) => onChange({ ...draft, y2: event.currentTarget.value })}
            placeholder="220"
            type="number"
            value={draft.y2}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Color</span>
          <Input
            disabled={disabled}
            name={`${draft.id}-color`}
            onChange={(event) => onChange({ ...draft, color: event.currentTarget.value })}
            placeholder="#ff0000"
            value={draft.color}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Width</span>
          <Input
            disabled={disabled}
            inputMode="decimal"
            name={`${draft.id}-arrow-width`}
            onChange={(event) => onChange({ ...draft, width: event.currentTarget.value })}
            placeholder="4"
            type="number"
            value={draft.width}
          />
        </label>
      </div>
    );
  }

  if (draft.op_type === "marker") {
    return (
      <div className="space-y-3">
        <div className="grid gap-3 md:grid-cols-2">
          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Color</span>
            <Input
              disabled={disabled}
              name={`${draft.id}-color`}
              onChange={(event) => onChange({ ...draft, color: event.currentTarget.value })}
              placeholder="#ffd54a"
              value={draft.color}
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
              Opacity
            </span>
            <Input
              disabled={disabled}
              inputMode="decimal"
              name={`${draft.id}-opacity`}
              onChange={(event) => onChange({ ...draft, opacity: event.currentTarget.value })}
              placeholder="0.4"
              type="number"
              value={draft.opacity}
            />
          </label>
        </div>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
            Points (`x,y` per line)
          </span>
          <Textarea
            className="min-h-28"
            disabled={disabled}
            name={`${draft.id}-points`}
            onChange={(event) => onChange({ ...draft, points: event.currentTarget.value })}
            placeholder={"10,10\n40,28\n120,36"}
            rows={4}
            value={draft.points}
          />
        </label>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="grid gap-3 md:grid-cols-2">
        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Color</span>
          <Input
            disabled={disabled}
            name={`${draft.id}-color`}
            onChange={(event) => onChange({ ...draft, color: event.currentTarget.value })}
            placeholder="#111111"
            value={draft.color}
          />
        </label>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">Width</span>
          <Input
            disabled={disabled}
            inputMode="decimal"
            name={`${draft.id}-width`}
            onChange={(event) => onChange({ ...draft, width: event.currentTarget.value })}
            placeholder="3"
            type="number"
            value={draft.width}
          />
        </label>
      </div>

      <label className="block">
        <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
          Points (`x,y` per line)
        </span>
        <Textarea
          className="min-h-28"
          disabled={disabled}
          name={`${draft.id}-points`}
          onChange={(event) => onChange({ ...draft, points: event.currentTarget.value })}
          placeholder={"10,10\n40,28\n120,36"}
          rows={4}
          value={draft.points}
        />
      </label>
    </div>
  );
}

export function InstructionAnchorPanel({
  anchorsState,
  currentInstructionVersion,
  jobId,
  latestServerVersion,
  lifecycle,
}: InstructionAnchorPanelProps) {
  const {
    anchors,
    detailFeedback,
    detailStatus,
    hasAnchors,
    listFeedback,
    listStatus,
    refresh,
    selectedAnchor,
    selectedAnchorId,
    selectedAnchorSummary,
    setSelectedAnchorId,
    visibilityContextDescription,
    visibilityTargetVersionId,
  } = anchorsState;
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [replaceIdempotencyKey, setReplaceIdempotencyKey] = useState("");
  const [replaceTimestampMs, setReplaceTimestampMs] = useState("");
  const [replaceOffsetMs, setReplaceOffsetMs] = useState("0");
  const [replaceStrategy, setReplaceStrategy] = useState<ScreenshotStrategy>("precise");
  const [replaceFormat, setReplaceFormat] = useState<ScreenshotFormat>("png");
  const [attachIdempotencyKey, setAttachIdempotencyKey] = useState("");
  const [annotationIdempotencyKey, setAnnotationIdempotencyKey] = useState(() =>
    createScreenshotIdempotencyKey("annotate"),
  );
  const [annotationDrafts, setAnnotationDrafts] = useState<AnnotationDraft[]>(() => [
    createAnnotationDraft("arrow"),
  ]);
  const [uploadFile, setUploadFile] = useState<File | null>(null);

  useEffect(() => {
    setReplaceIdempotencyKey(createScreenshotIdempotencyKey("replace"));
    setReplaceTimestampMs("");
    setReplaceOffsetMs("0");
    setReplaceStrategy("precise");
    setReplaceFormat("png");
    setAttachIdempotencyKey(createScreenshotIdempotencyKey("attach"));
    setAnnotationIdempotencyKey(createScreenshotIdempotencyKey("annotate"));
    setAnnotationDrafts([createAnnotationDraft("arrow")]);
    setUploadFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, [selectedAnchorId]);

  const projectedSelectedAnchor = applyAnchorAssetPreview(selectedAnchor, lifecycle.assetPreview);
  const projectedSelectedAnchorSummary = applyAnchorAssetPreview(selectedAnchorSummary, lifecycle.assetPreview);
  const resolutionFeedback = describeAnchorResolution(projectedSelectedAnchor?.resolution);
  const activeAsset = findActiveAnchorAsset(projectedSelectedAnchor);
  const activeAssetId = projectedSelectedAnchor?.active_asset_id ?? null;
  const activeAssetPendingRefresh =
    projectedSelectedAnchor?.id === lifecycle.assetPreview?.anchor_id &&
    Boolean(activeAssetId) &&
    activeAsset === null;
  const replaceTask = lifecycle.replaceTask;
  const replaceTaskLocked = replaceTask !== null && !isScreenshotTaskTerminal(replaceTask.status);
  const annotationOperations = buildAnnotationOperations(annotationDrafts);
  const annotationMatchesCurrentView =
    lifecycle.annotationResult?.active_asset_id === projectedSelectedAnchor?.active_asset_id;
  const mutationLocked =
    replaceTaskLocked ||
    lifecycle.annotationIsSubmitting ||
    lifecycle.replaceIsSubmitting ||
    lifecycle.uploadIsSubmitting ||
    lifecycle.pendingDeleteAssetId !== null;
  const replaceTimestampValue = Number(replaceTimestampMs.trim());
  const replaceOffsetValue =
    replaceOffsetMs.trim().length === 0 ? 0 : Number(replaceOffsetMs.trim());
  const hasValidReplaceTimestamp =
    replaceTimestampMs.trim().length > 0 &&
    Number.isInteger(replaceTimestampValue) &&
    replaceTimestampValue >= 0;
  const hasValidReplaceOffset = Number.isInteger(replaceOffsetValue);
  const selectedUploadMimeType = uploadFile ? normalizeScreenshotUploadMimeType(uploadFile.type) : null;
  const canReplace =
    Boolean(projectedSelectedAnchor?.id) &&
    Boolean(projectedSelectedAnchor?.instruction_version_id) &&
    Boolean(activeAssetId) &&
    hasValidReplaceTimestamp &&
    hasValidReplaceOffset &&
    replaceIdempotencyKey.trim().length > 0 &&
    !mutationLocked;
  const canUploadAndAttach =
    Boolean(projectedSelectedAnchor?.id) &&
    Boolean(jobId) &&
    uploadFile !== null &&
    selectedUploadMimeType !== null &&
    attachIdempotencyKey.trim().length > 0 &&
    !mutationLocked;
  const canAnnotate =
    Boolean(projectedSelectedAnchor?.id) &&
    Boolean(activeAssetId) &&
    annotationIdempotencyKey.trim().length > 0 &&
    annotationOperations !== null &&
    !mutationLocked;

  return (
    <Panel>
      <PanelHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="eyebrow text-[var(--text-muted)]">Anchor context</p>
            <PanelTitle>Inspect and manage deterministic screenshot assets</PanelTitle>
            <PanelDescription>
              Anchor selection stays stable while the currently loaded instruction version changes.
              Asset mutations stay scoped to the selected anchor and replay-safe task state.
            </PanelDescription>
          </div>

          <div className="flex flex-wrap gap-2">
            <StatusPill tone="info">Current v{currentInstructionVersion}</StatusPill>
            <StatusPill tone="neutral">Latest known v{latestServerVersion}</StatusPill>
          </div>
        </div>
      </PanelHeader>

      <div className="space-y-4">
        <div className="flex flex-wrap gap-3">
          <Button size="compact" variant="secondary" onClick={refresh}>
            Refresh anchors
          </Button>
        </div>

        <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
          {visibilityContextDescription}
        </div>

        {listStatus === "loading" && !hasAnchors ? (
          <LoadingState
            description="Loading anchor list and active asset context for this instruction."
            title="Loading anchors"
          />
        ) : null}

        {listStatus === "error" ? (
          <ErrorState
            action={
              <Button size="compact" variant="secondary" onClick={refresh}>
                Retry anchors
              </Button>
            }
            description={listFeedback?.description ?? "Anchor data could not be loaded."}
            title={listFeedback?.title ?? "Anchor context unavailable"}
          />
        ) : null}

        {listStatus === "success" && anchors.length === 0 ? (
          <EmptyState
            action={
              <Button size="compact" variant="secondary" onClick={refresh}>
                Refresh anchors
              </Button>
            }
            description="This instruction does not have any screenshot anchors yet."
            title="No anchors"
          />
        ) : null}

        {anchors.length > 0 ? (
          <div className="grid gap-4 xl:grid-cols-[minmax(280px,0.88fr)_minmax(0,1.12fr)]">
            <div className="space-y-3">
              {anchors.map((anchor) => {
                const previewedAnchor = applyAnchorAssetPreview(anchor, lifecycle.assetPreview);
                const summaryActiveAsset = findActiveAnchorAsset(previewedAnchor);
                const summaryActiveAssetId = previewedAnchor?.active_asset_id ?? null;

                return (
                  <button
                    key={anchor.id}
                    className={`w-full rounded-[var(--radius-card)] border px-4 py-4 text-left transition ${
                      anchor.id === selectedAnchorId
                        ? "bg-[var(--brand-soft)]"
                        : "bg-white/45 hover:bg-white/65"
                    }`}
                    style={{ borderColor: "var(--line-subtle)" }}
                    type="button"
                    onClick={() => setSelectedAnchorId(anchor.id)}
                  >
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="display-title text-lg font-semibold">{anchor.id}</h3>
                      <StatusPill tone="info">Source v{previewedAnchor?.instruction_version_id}</StatusPill>
                    </div>

                    <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                      {formatAnchorAddressing(anchor.addressing)}
                    </p>
                    <p className="mt-2 text-xs uppercase tracking-[0.14em] text-[var(--text-muted)]">
                      {summaryActiveAsset
                        ? `Active asset ${summaryActiveAsset.id} • ${summaryActiveAsset.kind}`
                        : summaryActiveAssetId
                          ? `Active asset ${summaryActiveAssetId} • refreshing history`
                          : "No active asset linked"}
                    </p>
                  </button>
                );
              })}
            </div>

            <div className="space-y-4">
              {detailStatus === "loading" && selectedAnchorSummary && !selectedAnchor ? (
                <LoadingState
                  description="Loading anchor details, asset history, and version visibility projection."
                  title="Loading anchor detail"
                />
              ) : null}

              {detailStatus === "error" ? (
                <ErrorState
                  action={
                    <Button size="compact" variant="secondary" onClick={refresh}>
                      Retry detail
                    </Button>
                  }
                  description={detailFeedback?.description ?? "Anchor detail could not be loaded."}
                  title={detailFeedback?.title ?? "Anchor detail unavailable"}
                />
              ) : null}

              {projectedSelectedAnchor ? (
                <>
                  <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="display-title text-xl font-semibold">{projectedSelectedAnchor.id}</h3>
                      {projectedSelectedAnchor.resolution ? (
                        <StatusPill tone={getAnchorResolutionTone(projectedSelectedAnchor.resolution.resolution_state)}>
                          {projectedSelectedAnchor.resolution.resolution_state}
                        </StatusPill>
                      ) : null}
                    </div>

                    <dl className="mt-4 grid gap-3 text-sm leading-6 text-[var(--text-secondary)]">
                      <div>
                        <dt className="eyebrow text-[var(--text-muted)]">Addressing</dt>
                        <dd>{formatAnchorAddressing(projectedSelectedAnchor.addressing)}</dd>
                      </div>
                      <div>
                        <dt className="eyebrow text-[var(--text-muted)]">Source version</dt>
                        <dd>v{projectedSelectedAnchor.instruction_version_id}</dd>
                      </div>
                      <div>
                        <dt className="eyebrow text-[var(--text-muted)]">Attach target version</dt>
                        <dd>v{currentInstructionVersion}</dd>
                      </div>
                      <div>
                        <dt className="eyebrow text-[var(--text-muted)]">Visibility target version</dt>
                        <dd>{visibilityTargetVersionId ? `v${visibilityTargetVersionId}` : "Unavailable"}</dd>
                      </div>
                      <div>
                        <dt className="eyebrow text-[var(--text-muted)]">Created</dt>
                        <dd>{formatDateTime(projectedSelectedAnchor.created_at)}</dd>
                      </div>
                      <div>
                        <dt className="eyebrow text-[var(--text-muted)]">Updated</dt>
                        <dd>{formatDateTime(projectedSelectedAnchor.updated_at)}</dd>
                      </div>
                    </dl>
                  </div>

                  {resolutionFeedback ? (
                    <div
                      className={`rounded-[var(--radius-card)] px-4 py-4 ${
                        resolutionFeedback.tone === "success"
                          ? "bg-[var(--status-success-soft)] text-[var(--status-success)]"
                          : resolutionFeedback.tone === "warning"
                            ? "bg-[var(--status-warning-soft)] text-[var(--status-warning)]"
                            : "bg-[var(--status-info-soft)] text-[var(--status-info)]"
                      }`}
                    >
                      <h3 className="display-title text-lg font-semibold">{resolutionFeedback.title}</h3>
                      <p className="mt-2 text-sm leading-6">{resolutionFeedback.description}</p>
                    </div>
                  ) : null}

                  {projectedSelectedAnchor.resolution?.trace ? (
                    <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                      <h3 className="display-title text-lg font-semibold">Resolution trace</h3>
                      <dl className="mt-3 grid gap-3 text-sm leading-6 text-[var(--text-secondary)]">
                        {Object.entries(projectedSelectedAnchor.resolution.trace).map(([key, value]) => (
                          <div key={key}>
                            <dt className="eyebrow text-[var(--text-muted)]">{key}</dt>
                            <dd style={{ fontFamily: "var(--font-mono)" }}>{renderTraceValue(value)}</dd>
                          </div>
                        ))}
                      </dl>
                    </div>
                  ) : null}

                  <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <h3 className="display-title text-lg font-semibold">Active asset</h3>
                      {activeAssetId ? (
                        <StatusPill tone={activeAsset ? "success" : "info"}>{activeAssetId}</StatusPill>
                      ) : (
                        <StatusPill tone="warning">No active asset</StatusPill>
                      )}
                    </div>

                    {activeAsset ? (
                      <dl className="mt-3 grid gap-3 text-sm leading-6 text-[var(--text-secondary)]">
                        <div>
                          <dt className="eyebrow text-[var(--text-muted)]">Asset ID</dt>
                          <dd style={{ fontFamily: "var(--font-mono)" }}>{activeAsset.id}</dd>
                        </div>
                        <div>
                          <dt className="eyebrow text-[var(--text-muted)]">Version</dt>
                          <dd>{activeAsset.version}</dd>
                        </div>
                        <div>
                          <dt className="eyebrow text-[var(--text-muted)]">Kind</dt>
                          <dd>{activeAsset.kind}</dd>
                        </div>
                        <div>
                          <dt className="eyebrow text-[var(--text-muted)]">Dimensions</dt>
                          <dd>
                            {activeAsset.width} x {activeAsset.height}
                          </dd>
                        </div>
                        <div>
                          <dt className="eyebrow text-[var(--text-muted)]">Image URI</dt>
                          <dd style={{ fontFamily: "var(--font-mono)" }}>{activeAsset.image_uri}</dd>
                        </div>
                      </dl>
                    ) : activeAssetPendingRefresh && activeAssetId ? (
                      <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
                        Active asset changed to {activeAssetId}. History is refreshing from the backend.
                      </p>
                    ) : (
                      <p className="mt-3 text-sm leading-6 text-[var(--text-secondary)]">
                        This anchor does not currently have an active asset.
                      </p>
                    )}
                  </div>

                  <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="display-title text-lg font-semibold">Annotate active asset</h3>
                        <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                          Annotation remains operation-log driven. Howera submits supported
                          contract fields only, normalizes the operation order deterministically, and
                          keeps the current asset view unchanged if rendering fails.
                        </p>
                      </div>
                      <StatusPill tone={lifecycle.annotationIsSubmitting ? "warning" : "info"}>
                        {lifecycle.annotationIsSubmitting ? "Rendering" : "Ready"}
                      </StatusPill>
                    </div>

                    <div className="mt-4 space-y-4">
                      <label className="block">
                        <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
                          Annotation idempotency key
                        </span>
                        <div className="flex flex-wrap gap-3">
                          <Input
                            autoComplete="off"
                            className="min-w-[220px] flex-1"
                            name="annotationIdempotencyKey"
                            onChange={(event) => setAnnotationIdempotencyKey(event.currentTarget.value)}
                            value={annotationIdempotencyKey}
                          />
                          <Button
                            size="compact"
                            variant="secondary"
                            onClick={() => setAnnotationIdempotencyKey(createScreenshotIdempotencyKey("annotate"))}
                          >
                            New key
                          </Button>
                        </div>
                      </label>

                      <div className="rounded-[var(--radius-card)] bg-[rgba(84,70,49,0.08)] px-4 py-4 text-sm leading-6 text-[var(--text-secondary)]">
                        <p>Base asset for render: {activeAssetId ?? "No active asset available"}</p>
                        {annotationOperations ? (
                          <p>
                            {annotationOperations.length} normalized operation
                            {annotationOperations.length === 1 ? "" : "s"} ready to submit.
                          </p>
                        ) : (
                          <p>At least one valid operation is required before rendering.</p>
                        )}
                      </div>

                      <div className="space-y-3">
                        <div className="flex flex-wrap gap-3">
                          {ANNOTATION_OPERATION_OPTIONS.map((opType) => (
                            <Button
                              key={opType}
                              disabled={mutationLocked}
                              size="compact"
                              variant="secondary"
                              onClick={() =>
                                setAnnotationDrafts((current) => [...current, createAnnotationDraft(opType)])
                              }
                            >
                              Add {formatAnnotationOperationLabel(opType)}
                            </Button>
                          ))}
                        </div>

                        {annotationDrafts.length > 0 ? (
                          <div className="space-y-3">
                            {annotationDrafts.map((draft, index) => (
                              <article
                                key={draft.id}
                                className="rounded-[var(--radius-card)] border bg-white/55 px-4 py-4"
                                style={{ borderColor: "var(--line-subtle)" }}
                              >
                                <div className="flex flex-wrap items-start justify-between gap-3">
                                  <div>
                                    <p className="eyebrow text-[var(--text-muted)]">
                                      Operation {index + 1}
                                    </p>
                                    <h4 className="display-title text-base font-semibold">
                                      {summarizeAnnotationDraft(draft)}
                                    </h4>
                                  </div>
                                  <Button
                                    disabled={mutationLocked}
                                    size="compact"
                                    variant="ghost"
                                    onClick={() =>
                                      setAnnotationDrafts((current) =>
                                        current.filter((candidate) => candidate.id !== draft.id),
                                      )
                                    }
                                  >
                                    Remove
                                  </Button>
                                </div>

                                <div className="mt-4 space-y-4">
                                  <div className="space-y-3">
                                    <span className="block text-sm font-medium text-[var(--text-primary)]">
                                      Operation type
                                    </span>
                                    <div className="flex flex-wrap gap-3">
                                      {ANNOTATION_OPERATION_OPTIONS.map((opType) => (
                                        <Button
                                          key={opType}
                                          disabled={mutationLocked}
                                          size="compact"
                                          variant={draft.op_type === opType ? "primary" : "secondary"}
                                          onClick={() =>
                                            setAnnotationDrafts((current) =>
                                              current.map((candidate) =>
                                                candidate.id === draft.id
                                                  ? changeAnnotationDraftType(candidate, opType)
                                                  : candidate,
                                              ),
                                            )
                                          }
                                        >
                                          {formatAnnotationOperationLabel(opType)}
                                        </Button>
                                      ))}
                                    </div>
                                  </div>

                                  {renderAnnotationDraftFields({
                                    disabled: mutationLocked,
                                    draft,
                                    onChange: (nextDraft) =>
                                      setAnnotationDrafts((current) =>
                                        current.map((candidate) =>
                                          candidate.id === nextDraft.id ? nextDraft : candidate,
                                        ),
                                      ),
                                  })}
                                </div>
                              </article>
                            ))}
                          </div>
                        ) : (
                          <div className="rounded-[var(--radius-card)] bg-[var(--status-warning-soft)] px-4 py-3 text-sm text-[var(--status-warning)]">
                            Add at least one supported annotation operation before rendering.
                          </div>
                        )}
                      </div>

                      {!activeAssetId ? (
                        <div className="rounded-[var(--radius-card)] bg-[var(--status-warning-soft)] px-4 py-3 text-sm text-[var(--status-warning)]">
                          This anchor does not have an active asset to annotate.
                        </div>
                      ) : null}

                      {annotationDrafts.length > 0 && annotationOperations === null ? (
                        <div className="rounded-[var(--radius-card)] bg-[var(--status-warning-soft)] px-4 py-3 text-sm text-[var(--status-warning)]">
                          Complete every draft with supported contract fields only. Points must use
                          `x,y` pairs on separate lines.
                        </div>
                      ) : null}

                      {annotationOperations ? (
                        <div className="rounded-[var(--radius-card)] bg-[rgba(29,31,29,0.96)] px-4 py-4 text-sm leading-7 text-[var(--text-inverse)]">
                          <p className="eyebrow text-[rgba(249,246,239,0.62)]">
                            Normalized annotation payload
                          </p>
                          <pre className="mt-3 overflow-x-auto whitespace-pre-wrap">
                            {JSON.stringify(annotationOperations, null, 2)}
                          </pre>
                        </div>
                      ) : null}

                      <div className="flex flex-wrap gap-3">
                        <Button
                          disabled={!canAnnotate}
                          onClick={() => {
                            if (!projectedSelectedAnchor || !activeAssetId || !annotationOperations) {
                              return;
                            }

                            void lifecycle.submitAnnotation({
                              anchorId: projectedSelectedAnchor.id,
                              payload: {
                                base_asset_id: activeAssetId,
                                idempotency_key: annotationIdempotencyKey.trim(),
                                operations: annotationOperations,
                              },
                              previousActiveAssetId: activeAssetId,
                            });
                          }}
                        >
                          {lifecycle.annotationIsSubmitting ? "Rendering..." : "Render annotations"}
                        </Button>
                      </div>

                      {lifecycle.annotationFeedback
                        ? renderFeedbackCard(
                            lifecycle.annotationFeedback,
                            lifecycle.dismissAnnotationFeedback,
                          )
                        : null}

                      {lifecycle.annotationResult ? (
                        <div className="rounded-[var(--radius-card)] bg-[rgba(84,70,49,0.08)] px-4 py-4 text-sm leading-6 text-[var(--text-secondary)]">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <h4 className="display-title text-base font-semibold">
                              Last annotation outcome
                            </h4>
                            <StatusPill tone={annotationMatchesCurrentView ? "success" : "info"}>
                              {annotationMatchesCurrentView ? "Current view" : "Preserved result"}
                            </StatusPill>
                          </div>

                          <dl className="mt-3 grid gap-3">
                            <div>
                              <dt className="eyebrow text-[var(--text-muted)]">Base asset</dt>
                              <dd style={{ fontFamily: "var(--font-mono)" }}>
                                {lifecycle.annotationResult.base_asset_id}
                              </dd>
                            </div>
                            <div>
                              <dt className="eyebrow text-[var(--text-muted)]">Rendered asset</dt>
                              <dd style={{ fontFamily: "var(--font-mono)" }}>
                                {lifecycle.annotationResult.rendered_asset_id}
                              </dd>
                            </div>
                            <div>
                              <dt className="eyebrow text-[var(--text-muted)]">Active asset</dt>
                              <dd style={{ fontFamily: "var(--font-mono)" }}>
                                {lifecycle.annotationResult.active_asset_id}
                              </dd>
                            </div>
                            <div>
                              <dt className="eyebrow text-[var(--text-muted)]">Ops hash</dt>
                              <dd style={{ fontFamily: "var(--font-mono)" }}>
                                {lifecycle.annotationResult.ops_hash}
                              </dd>
                            </div>
                          </dl>

                          {lifecycle.annotationLastIdempotencyKey ? (
                            <p className="mt-4">
                              Last annotation idempotency key: {lifecycle.annotationLastIdempotencyKey}
                            </p>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  </div>

                  <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="display-title text-lg font-semibold">Replace active asset</h3>
                        <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                          Replacement preserves anchor identity and asks the backend to compute the
                          next active asset from the selected anchor&apos;s source version.
                        </p>
                      </div>
                      {replaceTask ? (
                        <StatusPill tone={getScreenshotTaskStatusTone(replaceTask.status)}>
                          {replaceTask.status}
                        </StatusPill>
                      ) : (
                        <StatusPill tone="info">Idle</StatusPill>
                      )}
                    </div>

                    <div className="mt-4 space-y-4">
                      <label className="block">
                        <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
                          Idempotency key
                        </span>
                        <div className="flex flex-wrap gap-3">
                          <Input
                            autoComplete="off"
                            className="min-w-[220px] flex-1"
                            name="replaceIdempotencyKey"
                            onChange={(event) => setReplaceIdempotencyKey(event.currentTarget.value)}
                            value={replaceIdempotencyKey}
                          />
                          <Button
                            size="compact"
                            variant="secondary"
                            onClick={() => setReplaceIdempotencyKey(createScreenshotIdempotencyKey("replace"))}
                          >
                            New key
                          </Button>
                        </div>
                      </label>

                      <div className="grid gap-3 md:grid-cols-2">
                        <label className="block">
                          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
                            Timestamp (ms)
                          </span>
                          <Input
                            autoComplete="off"
                            inputMode="numeric"
                            min={0}
                            name="replaceTimestampMs"
                            onChange={(event) => setReplaceTimestampMs(event.currentTarget.value)}
                            placeholder="12500"
                            type="number"
                            value={replaceTimestampMs}
                          />
                        </label>

                        <label className="block">
                          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
                            Offset (ms)
                          </span>
                          <Input
                            autoComplete="off"
                            inputMode="numeric"
                            name="replaceOffsetMs"
                            onChange={(event) => setReplaceOffsetMs(event.currentTarget.value)}
                            placeholder="0"
                            step={1}
                            type="number"
                            value={replaceOffsetMs}
                          />
                        </label>
                      </div>

                      <div className="grid gap-4 lg:grid-cols-2">
                        <div className="space-y-3">
                          <span className="block text-sm font-medium text-[var(--text-primary)]">
                            Strategy
                          </span>
                          <div className="flex flex-wrap gap-3">
                            {STRATEGY_OPTIONS.map((candidate) => (
                              <Button
                                key={candidate}
                                size="compact"
                                variant={replaceStrategy === candidate ? "primary" : "secondary"}
                                onClick={() => setReplaceStrategy(candidate)}
                              >
                                {candidate}
                              </Button>
                            ))}
                          </div>
                        </div>

                        <div className="space-y-3">
                          <span className="block text-sm font-medium text-[var(--text-primary)]">
                            Format
                          </span>
                          <div className="flex flex-wrap gap-3">
                            {FORMAT_OPTIONS.map((candidate) => (
                              <Button
                                key={candidate}
                                size="compact"
                                variant={replaceFormat === candidate ? "primary" : "secondary"}
                                onClick={() => setReplaceFormat(candidate)}
                              >
                                {candidate}
                              </Button>
                            ))}
                          </div>
                        </div>
                      </div>

                      {!activeAssetId ? (
                        <div className="rounded-[var(--radius-card)] bg-[var(--status-warning-soft)] px-4 py-3 text-sm text-[var(--status-warning)]">
                          This anchor does not have an active asset to replace. Upload and attach a
                          custom asset first if you need to re-seed this anchor.
                        </div>
                      ) : null}

                      {!hasValidReplaceTimestamp || !hasValidReplaceOffset ? (
                        <div className="rounded-[var(--radius-card)] bg-[var(--status-warning-soft)] px-4 py-3 text-sm text-[var(--status-warning)]">
                          Timestamp must be a non-negative integer in milliseconds, and offset must
                          be an integer in milliseconds.
                        </div>
                      ) : null}

                      <div className="flex flex-wrap gap-3">
                        <Button
                          disabled={!canReplace}
                          onClick={() => {
                            if (!projectedSelectedAnchor || !hasValidReplaceTimestamp || !hasValidReplaceOffset) {
                              return;
                            }

                            void lifecycle.submitReplace({
                              anchorId: projectedSelectedAnchor.id,
                              payload: {
                                format: replaceFormat,
                                idempotency_key: replaceIdempotencyKey.trim(),
                                instruction_version_id: projectedSelectedAnchor.instruction_version_id,
                                offset_ms: replaceOffsetValue,
                                strategy: replaceStrategy,
                                timestamp_ms: replaceTimestampValue,
                              },
                            });
                          }}
                        >
                          {lifecycle.replaceIsSubmitting ? "Submitting..." : "Replace active asset"}
                        </Button>
                      </div>

                      {lifecycle.replaceFeedback
                        ? renderFeedbackCard(lifecycle.replaceFeedback, lifecycle.dismissReplaceFeedback)
                        : null}

                      {replaceTask ? (
                        <div className="rounded-[var(--radius-card)] bg-[rgba(84,70,49,0.08)] px-4 py-4 text-sm leading-6 text-[var(--text-secondary)]">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <h4 className="display-title text-base font-semibold">
                              Task {replaceTask.task_id}
                            </h4>
                            {replaceTask.replayed ? <StatusPill tone="info">Replay</StatusPill> : null}
                          </div>

                          <dl className="mt-3 grid gap-3">
                            <div>
                              <dt className="eyebrow text-[var(--text-muted)]">Operation</dt>
                              <dd>{replaceTask.operation}</dd>
                            </div>
                            <div>
                              <dt className="eyebrow text-[var(--text-muted)]">Status</dt>
                              <dd>{replaceTask.status}</dd>
                            </div>
                            {replaceTask.anchor_id ? (
                              <div>
                                <dt className="eyebrow text-[var(--text-muted)]">Anchor ID</dt>
                                <dd style={{ fontFamily: "var(--font-mono)" }}>{replaceTask.anchor_id}</dd>
                              </div>
                            ) : null}
                            {replaceTask.asset_id ? (
                              <div>
                                <dt className="eyebrow text-[var(--text-muted)]">Asset ID</dt>
                                <dd style={{ fontFamily: "var(--font-mono)" }}>{replaceTask.asset_id}</dd>
                              </div>
                            ) : null}
                          </dl>

                          <div className="mt-4 space-y-2">
                            <p>{describeScreenshotPolling(lifecycle.replacePolling)}</p>
                            {lifecycle.replacePolling.startedAt ? (
                              <p>Tracking started: {formatDateTime(lifecycle.replacePolling.startedAt)}</p>
                            ) : null}
                            {lifecycle.replacePolling.lastPolledAt ? (
                              <p>Last poll tick: {formatDateTime(lifecycle.replacePolling.lastPolledAt)}</p>
                            ) : null}
                            {lifecycle.replaceLastIdempotencyKey ? (
                              <p>Last idempotency key: {lifecycle.replaceLastIdempotencyKey}</p>
                            ) : null}
                          </div>

                          <div className="mt-4 flex flex-wrap gap-3">
                            <Button
                              size="compact"
                              variant="secondary"
                              onClick={() => {
                                void lifecycle.refreshReplaceTask();
                              }}
                            >
                              Refresh task
                            </Button>
                            {lifecycle.replacePolling.active ? (
                              <Button size="compact" variant="ghost" onClick={lifecycle.stopReplacePolling}>
                                Stop polling
                              </Button>
                            ) : null}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  </div>

                  <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                    <h3 className="display-title text-lg font-semibold">Upload and attach custom asset</h3>
                    <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                      Signed upload URLs stay ephemeral in memory only. Successful attach moves the
                      selected anchor to currently loaded instruction version v{currentInstructionVersion}.
                    </p>

                    <div className="mt-4 space-y-4">
                      <label className="block">
                        <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
                          Custom image file
                        </span>
                        <Input
                          accept={ACCEPTED_UPLOAD_TYPES}
                          name="customScreenshotFile"
                          onChange={(event) => setUploadFile(event.currentTarget.files?.[0] ?? null)}
                          ref={fileInputRef}
                          type="file"
                        />
                      </label>

                      {uploadFile ? (
                        <div className="rounded-[var(--radius-card)] bg-[rgba(84,70,49,0.08)] px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
                          <p>
                            Selected file: {uploadFile.name} ({uploadFile.size} bytes)
                          </p>
                          <p>MIME type: {uploadFile.type || "Unavailable"}</p>
                        </div>
                      ) : null}

                      {uploadFile && selectedUploadMimeType === null ? (
                        <div className="rounded-[var(--radius-card)] bg-[var(--status-warning-soft)] px-4 py-3 text-sm text-[var(--status-warning)]">
                          Only PNG, JPEG, and WebP uploads are supported by the screenshot asset contract.
                        </div>
                      ) : null}

                      <label className="block">
                        <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
                          Attach idempotency key
                        </span>
                        <div className="flex flex-wrap gap-3">
                          <Input
                            autoComplete="off"
                            className="min-w-[220px] flex-1"
                            name="attachIdempotencyKey"
                            onChange={(event) => setAttachIdempotencyKey(event.currentTarget.value)}
                            value={attachIdempotencyKey}
                          />
                          <Button
                            size="compact"
                            variant="secondary"
                            onClick={() => setAttachIdempotencyKey(createScreenshotIdempotencyKey("attach"))}
                          >
                            New key
                          </Button>
                        </div>
                      </label>

                      <div className="flex flex-wrap gap-3">
                        <Button
                          disabled={!canUploadAndAttach}
                          onClick={() => {
                            if (!projectedSelectedAnchor || !uploadFile || !selectedUploadMimeType) {
                              return;
                            }

                            void lifecycle
                              .submitUploadAndAttach({
                                anchorId: projectedSelectedAnchor.id,
                                attachInstructionVersionId: String(currentInstructionVersion),
                                file: uploadFile,
                                idempotencyKey: attachIdempotencyKey.trim(),
                                jobId,
                              })
                              .then((succeeded) => {
                                if (!succeeded) {
                                  return;
                                }

                                setUploadFile(null);
                                setAttachIdempotencyKey(createScreenshotIdempotencyKey("attach"));
                                if (fileInputRef.current) {
                                  fileInputRef.current.value = "";
                                }
                              });
                          }}
                        >
                          {lifecycle.uploadIsSubmitting ? "Uploading..." : "Upload and attach"}
                        </Button>
                      </div>

                      {lifecycle.uploadFeedback
                        ? renderFeedbackCard(lifecycle.uploadFeedback, lifecycle.dismissUploadFeedback)
                        : null}

                      {lifecycle.uploadLastIdempotencyKey ? (
                        <div className="rounded-[var(--radius-card)] bg-[rgba(84,70,49,0.08)] px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
                          Last attach idempotency key: {lifecycle.uploadLastIdempotencyKey}
                        </div>
                      ) : null}
                    </div>
                  </div>

                  {lifecycle.deleteFeedback
                    ? renderFeedbackCard(lifecycle.deleteFeedback, lifecycle.dismissDeleteFeedback)
                    : null}

                  <div className="space-y-3">
                    <h3 className="display-title text-lg font-semibold">Asset history</h3>
                    {projectedSelectedAnchor.assets?.length ? (
                      projectedSelectedAnchor.assets.map((asset) => (
                        <article
                          key={asset.id}
                          className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div className="flex flex-wrap items-center gap-2">
                              <h4 className="display-title text-base font-semibold">{asset.id}</h4>
                              <StatusPill tone={asset.is_deleted ? "warning" : "info"}>
                                {asset.is_deleted ? "Deleted" : "Visible"}
                              </StatusPill>
                              {asset.id === projectedSelectedAnchor.active_asset_id ? (
                                <StatusPill tone="success">Active</StatusPill>
                              ) : null}
                            </div>

                            <Button
                              disabled={asset.is_deleted || mutationLocked}
                              size="compact"
                              variant="secondary"
                              onClick={() => {
                                void lifecycle.deleteAsset({
                                  anchorId: projectedSelectedAnchor.id,
                                  assetId: asset.id,
                                });
                              }}
                            >
                              {lifecycle.pendingDeleteAssetId === asset.id ? "Deleting..." : "Delete asset"}
                            </Button>
                          </div>

                          <dl className="mt-3 grid gap-3 text-sm leading-6 text-[var(--text-secondary)]">
                            <div>
                              <dt className="eyebrow text-[var(--text-muted)]">Kind</dt>
                              <dd>{asset.kind}</dd>
                            </div>
                            <div>
                              <dt className="eyebrow text-[var(--text-muted)]">Version</dt>
                              <dd>{asset.version}</dd>
                            </div>
                            <div>
                              <dt className="eyebrow text-[var(--text-muted)]">Created</dt>
                              <dd>{formatDateTime(asset.created_at)}</dd>
                            </div>
                            <div>
                              <dt className="eyebrow text-[var(--text-muted)]">Image URI</dt>
                              <dd style={{ fontFamily: "var(--font-mono)" }}>{asset.image_uri}</dd>
                            </div>
                          </dl>
                        </article>
                      ))
                    ) : (
                      <EmptyState
                        description="No asset history is attached to this anchor yet."
                        title="No assets"
                      />
                    )}
                  </div>
                </>
              ) : projectedSelectedAnchorSummary ? (
                <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4 text-sm leading-6 text-[var(--text-secondary)]">
                  Anchor {projectedSelectedAnchorSummary.id} is selected. Detail will appear after the
                  current projection finishes loading.
                </div>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
