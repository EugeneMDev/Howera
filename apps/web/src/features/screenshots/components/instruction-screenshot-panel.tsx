"use client";

import React from "react";

import type { TextSelectionSnapshot } from "@/features/instructions/selection";
import type { useScreenshotExtraction } from "@/features/screenshots/hooks";
import {
  describeScreenshotPolling,
  getScreenshotTaskStatusTone,
} from "@/features/screenshots/extraction";
import type { ScreenshotFormat, ScreenshotStrategy } from "@/features/screenshots/api";
import { formatDateTime } from "@/shared/lib/format-date";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { StatusPill } from "@/shared/ui/status-pill";

interface InstructionScreenshotPanelProps {
  blockId: string;
  contextMode: "block_id" | "char_range";
  format: ScreenshotFormat;
  idempotencyKey: string;
  isDirty: boolean;
  offsetMs: string;
  onBlockIdChange: (value: string) => void;
  onContextModeChange: (mode: "block_id" | "char_range") => void;
  onDismissFeedback: () => void;
  onFormatChange: (format: ScreenshotFormat) => void;
  onGenerateIdempotencyKey: () => void;
  onIdempotencyKeyChange: (value: string) => void;
  onOffsetMsChange: (value: string) => void;
  onRefreshCurrentTask: () => void;
  onStopPolling: () => void;
  onStrategyChange: (strategy: ScreenshotStrategy) => void;
  onSubmit: () => void;
  onTimestampMsChange: (value: string) => void;
  screenshot: ReturnType<typeof useScreenshotExtraction>;
  selectedText: string;
  selection: TextSelectionSnapshot | null;
  strategy: ScreenshotStrategy;
  timestampMs: string;
}

const FORMAT_OPTIONS: ScreenshotFormat[] = ["png", "jpg", "webp"];
const STRATEGY_OPTIONS: ScreenshotStrategy[] = ["precise", "nearest_keyframe"];

export function InstructionScreenshotPanel({
  blockId,
  contextMode,
  format,
  idempotencyKey,
  isDirty,
  offsetMs,
  onBlockIdChange,
  onContextModeChange,
  onDismissFeedback,
  onFormatChange,
  onGenerateIdempotencyKey,
  onIdempotencyKeyChange,
  onOffsetMsChange,
  onRefreshCurrentTask,
  onStopPolling,
  onStrategyChange,
  onSubmit,
  onTimestampMsChange,
  screenshot,
  selectedText,
  selection,
  strategy,
  timestampMs,
}: InstructionScreenshotPanelProps) {
  const hasValidCharRange = selection !== null && selection.end > selection.start;
  const hasValidBlockId = blockId.trim().length > 0;
  const timestampValue = Number(timestampMs.trim());
  const offsetValue = offsetMs.trim().length === 0 ? 0 : Number(offsetMs.trim());
  const hasValidTimestamp =
    timestampMs.trim().length > 0 && Number.isInteger(timestampValue) && timestampValue >= 0;
  const hasValidOffset = Number.isInteger(offsetValue);
  const hasValidContext = contextMode === "char_range" ? hasValidCharRange : hasValidBlockId;
  const task = screenshot.task;

  return (
    <Panel>
      <PanelHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="eyebrow text-[var(--text-muted)]">Screenshot extraction</p>
            <PanelTitle>Capture visual evidence</PanelTitle>
            <PanelDescription>
              Extraction stays in the editor workspace. Polling updates land here without resetting
              your surrounding editor state or transcript context.
            </PanelDescription>
          </div>

          {task ? (
            <StatusPill tone={getScreenshotTaskStatusTone(task.status)}>{task.status}</StatusPill>
          ) : (
            <StatusPill tone="info">Idle</StatusPill>
          )}
        </div>
      </PanelHeader>

      <div className="space-y-4">
        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
            Idempotency key
          </span>
          <div className="flex flex-wrap gap-3">
            <Input
              autoComplete="off"
              className="min-w-[220px] flex-1"
              name="screenshotIdempotencyKey"
              onChange={(event) => onIdempotencyKeyChange(event.currentTarget.value)}
              value={idempotencyKey}
            />
            <Button size="compact" variant="secondary" onClick={onGenerateIdempotencyKey}>
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
              name="timestampMs"
              onChange={(event) => onTimestampMsChange(event.currentTarget.value)}
              placeholder="12500"
              type="number"
              value={timestampMs}
            />
          </label>

          <label className="block">
            <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
              Offset (ms)
            </span>
            <Input
              autoComplete="off"
              inputMode="numeric"
              name="offsetMs"
              onChange={(event) => onOffsetMsChange(event.currentTarget.value)}
              placeholder="0"
              step={1}
              type="number"
              value={offsetMs}
            />
          </label>
        </div>

        <div className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-3">
            <span className="block text-sm font-medium text-[var(--text-primary)]">Strategy</span>
            <div className="flex flex-wrap gap-3">
              {STRATEGY_OPTIONS.map((candidate) => (
                <Button
                  key={candidate}
                  aria-pressed={strategy === candidate}
                  size="compact"
                  variant={strategy === candidate ? "primary" : "secondary"}
                  onClick={() => onStrategyChange(candidate)}
                >
                  {candidate}
                </Button>
              ))}
            </div>
          </div>

          <div className="space-y-3">
            <span className="block text-sm font-medium text-[var(--text-primary)]">Format</span>
            <div className="flex flex-wrap gap-3">
              {FORMAT_OPTIONS.map((candidate) => (
                <Button
                  key={candidate}
                  aria-pressed={format === candidate}
                  size="compact"
                  variant={format === candidate ? "primary" : "secondary"}
                  onClick={() => onFormatChange(candidate)}
                >
                  {candidate}
                </Button>
              ))}
            </div>
          </div>
        </div>

        {isDirty ? (
          <div className="rounded-[var(--radius-card)] bg-[var(--status-warning-soft)] px-4 py-3 text-sm text-[var(--status-warning)]">
            Save or discard unsaved markdown changes before extracting with anchor context. The API
            validates screenshot linkage against persisted instruction versions.
          </div>
        ) : null}

        <div className="space-y-3">
          <div className="flex flex-wrap gap-3">
            <Button
              aria-pressed={contextMode === "char_range"}
              size="compact"
              variant={contextMode === "char_range" ? "primary" : "secondary"}
              onClick={() => onContextModeChange("char_range")}
            >
              Char range
            </Button>
            <Button
              aria-pressed={contextMode === "block_id"}
              size="compact"
              variant={contextMode === "block_id" ? "primary" : "secondary"}
              onClick={() => onContextModeChange("block_id")}
            >
              Block ID
            </Button>
          </div>

          {contextMode === "char_range" ? (
            <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="display-title text-lg font-semibold">Selected text range</h3>
                {hasValidCharRange ? (
                  <StatusPill tone="success">
                    {selection?.start}-{selection?.end}
                  </StatusPill>
                ) : (
                  <StatusPill tone="warning">No selection</StatusPill>
                )}
              </div>
              <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">
                {hasValidCharRange
                  ? "The current textarea selection will be linked as char_range."
                  : "Select a non-empty range inside the editor to enable char_range extraction."}
              </p>
              {hasValidCharRange ? (
                <pre
                  className="mt-3 overflow-x-auto whitespace-pre-wrap rounded-[var(--radius-card)] bg-[rgba(29,31,29,0.96)] px-4 py-3 text-sm leading-7 text-[var(--text-inverse)]"
                  style={{ fontFamily: "var(--font-mono)" }}
                >
                  {selectedText}
                </pre>
              ) : null}
            </div>
          ) : (
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
                Block ID
              </span>
              <Input
                autoComplete="off"
                name="screenshotBlockId"
                onChange={(event) => onBlockIdChange(event.currentTarget.value)}
                placeholder="step-3"
                value={blockId}
              />
            </label>
          )}
        </div>

        <div className="flex flex-wrap gap-3">
          <Button
            disabled={
              isDirty ||
              !hasValidTimestamp ||
              !hasValidOffset ||
              !idempotencyKey.trim() ||
              !hasValidContext ||
              screenshot.isSubmitting
            }
            onClick={onSubmit}
          >
            {screenshot.isSubmitting ? "Submitting..." : "Extract screenshot"}
          </Button>
        </div>

        {!hasValidTimestamp || !hasValidOffset ? (
          <div className="rounded-[var(--radius-card)] bg-[var(--status-warning-soft)] px-4 py-3 text-sm text-[var(--status-warning)]">
            Timestamp must be a non-negative integer in milliseconds, and offset must be an integer
            in milliseconds.
          </div>
        ) : null}

        {screenshot.feedback ? (
          <div
            className={`rounded-[var(--radius-card)] px-4 py-4 ${
              screenshot.feedback.tone === "success"
                ? "bg-[var(--status-success-soft)] text-[var(--status-success)]"
                : screenshot.feedback.tone === "warning"
                  ? "bg-[var(--status-warning-soft)] text-[var(--status-warning)]"
                  : screenshot.feedback.tone === "danger"
                    ? "bg-[var(--status-danger-soft)] text-[var(--status-danger)]"
                    : "bg-[var(--status-info-soft)] text-[var(--status-info)]"
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="display-title text-lg font-semibold">{screenshot.feedback.title}</h3>
                <p className="mt-2 text-sm leading-6">{screenshot.feedback.description}</p>
              </div>
              <Button size="compact" variant="ghost" onClick={onDismissFeedback}>
                Dismiss
              </Button>
            </div>
          </div>
        ) : null}

        {task ? (
          <div className="space-y-3">
            <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="display-title text-lg font-semibold">Task {task.task_id}</h3>
                {task.replayed ? <StatusPill tone="info">Replay</StatusPill> : null}
              </div>

              <dl className="mt-3 grid gap-3 text-sm leading-6 text-[var(--text-secondary)]">
                <div>
                  <dt className="eyebrow text-[var(--text-muted)]">Operation</dt>
                  <dd>{task.operation}</dd>
                </div>
                <div>
                  <dt className="eyebrow text-[var(--text-muted)]">Status</dt>
                  <dd>{task.status}</dd>
                </div>
                {task.anchor_id ? (
                  <div>
                    <dt className="eyebrow text-[var(--text-muted)]">Anchor linkage</dt>
                    <dd style={{ fontFamily: "var(--font-mono)" }}>{task.anchor_id}</dd>
                  </div>
                ) : null}
                {task.asset_id ? (
                  <div>
                    <dt className="eyebrow text-[var(--text-muted)]">Asset linkage</dt>
                    <dd style={{ fontFamily: "var(--font-mono)" }}>{task.asset_id}</dd>
                  </div>
                ) : null}
                {task.failure_code ? (
                  <div>
                    <dt className="eyebrow text-[var(--text-muted)]">Failure code</dt>
                    <dd>{task.failure_code}</dd>
                  </div>
                ) : null}
              </dl>

              <div className="mt-4 space-y-2 text-sm leading-6 text-[var(--text-secondary)]">
                <p>{describeScreenshotPolling(screenshot.polling)}</p>
                {screenshot.polling.startedAt ? (
                  <p>Tracking started: {formatDateTime(screenshot.polling.startedAt)}</p>
                ) : null}
                {screenshot.polling.lastPolledAt ? (
                  <p>Last poll tick: {formatDateTime(screenshot.polling.lastPolledAt)}</p>
                ) : null}
                {screenshot.lastIdempotencyKey ? (
                  <p>Last idempotency key: {screenshot.lastIdempotencyKey}</p>
                ) : null}
              </div>

              <div className="mt-4 flex flex-wrap gap-3">
                <Button size="compact" variant="secondary" onClick={onRefreshCurrentTask}>
                  Refresh task
                </Button>
                {screenshot.polling.active ? (
                  <Button size="compact" variant="ghost" onClick={onStopPolling}>
                    Stop polling
                  </Button>
                ) : null}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
