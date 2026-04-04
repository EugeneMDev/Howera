"use client";

import React from "react";

import type { TextSelectionSnapshot } from "@/features/instructions/selection";
import type { useInstructionRegenerate } from "@/features/instructions/regenerate-hooks";
import { describeRegeneratePolling, getRegenerateTaskStatusTone } from "@/features/instructions/regenerate";
import { formatDateTime } from "@/shared/lib/format-date";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { StatusPill } from "@/shared/ui/status-pill";

interface InstructionRegeneratePanelProps {
  blockId: string;
  clientRequestId: string;
  isDirty: boolean;
  mode: "block_id" | "char_range";
  onBlockIdChange: (value: string) => void;
  onClientRequestIdChange: (value: string) => void;
  onGenerateClientRequestId: () => void;
  onModeChange: (mode: "block_id" | "char_range") => void;
  onRefreshLatestInstruction: () => void;
  onSubmitBlockId: () => void;
  onSubmitCharRange: () => void;
  regenerate: ReturnType<typeof useInstructionRegenerate>;
  selection: TextSelectionSnapshot | null;
  selectedText: string;
}

export function InstructionRegeneratePanel({
  blockId,
  clientRequestId,
  isDirty,
  mode,
  onBlockIdChange,
  onClientRequestIdChange,
  onGenerateClientRequestId,
  onModeChange,
  onRefreshLatestInstruction,
  onSubmitBlockId,
  onSubmitCharRange,
  regenerate,
  selection,
  selectedText,
}: InstructionRegeneratePanelProps) {
  const hasValidCharRange = selection !== null && selection.end > selection.start;
  const hasValidBlockId = blockId.trim().length > 0;
  const task = regenerate.task;

  return (
    <Panel>
      <PanelHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="eyebrow text-[var(--text-muted)]">Targeted regenerate</p>
            <PanelTitle>Refine a selected fragment</PanelTitle>
            <PanelDescription>
              Regenerate uses the saved instruction version as its base. Unsaved local draft changes
              must be saved or discarded first.
            </PanelDescription>
          </div>

          {task ? (
            <StatusPill tone={getRegenerateTaskStatusTone(task.status)}>{task.status}</StatusPill>
          ) : (
            <StatusPill tone="info">Idle</StatusPill>
          )}
        </div>
      </PanelHeader>

      <div className="space-y-4">
        <div className="flex flex-wrap gap-3">
          <Button
            aria-pressed={mode === "char_range"}
            size="compact"
            variant={mode === "char_range" ? "primary" : "secondary"}
            onClick={() => onModeChange("char_range")}
          >
            Char range
          </Button>
          <Button
            aria-pressed={mode === "block_id"}
            size="compact"
            variant={mode === "block_id" ? "primary" : "secondary"}
            onClick={() => onModeChange("block_id")}
          >
            Block ID
          </Button>
        </div>

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
            Client request ID
          </span>
          <div className="flex flex-wrap gap-3">
            <Input
              autoComplete="off"
              className="min-w-[220px] flex-1"
              name="clientRequestId"
              onChange={(event) => onClientRequestIdChange(event.currentTarget.value)}
              value={clientRequestId}
            />
            <Button size="compact" variant="secondary" onClick={onGenerateClientRequestId}>
              New request ID
            </Button>
          </div>
        </label>

        {isDirty ? (
          <div className="rounded-[var(--radius-card)] bg-[var(--status-warning-soft)] px-4 py-3 text-sm text-[var(--status-warning)]">
            Save or discard unsaved local markdown changes before requesting regenerate. The backend
            only regenerates against persisted instruction versions.
          </div>
        ) : null}

        {mode === "char_range" ? (
          <div className="space-y-3">
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
                  ? "The current textarea selection will be sent as char_range."
                  : "Select a non-empty range inside the editor to enable char_range regenerate."}
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

            <div className="flex flex-wrap gap-3">
              <Button
                disabled={isDirty || !hasValidCharRange || !clientRequestId.trim() || regenerate.isSubmitting}
                onClick={onSubmitCharRange}
              >
                {regenerate.isSubmitting ? "Submitting..." : "Regenerate selected range"}
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            <label className="block">
              <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
                Block ID
              </span>
              <Input
                autoComplete="off"
                name="blockId"
                onChange={(event) => onBlockIdChange(event.currentTarget.value)}
                placeholder="step-3"
                value={blockId}
              />
            </label>

            <div className="flex flex-wrap gap-3">
              <Button
                disabled={isDirty || !hasValidBlockId || !clientRequestId.trim() || regenerate.isSubmitting}
                onClick={onSubmitBlockId}
              >
                {regenerate.isSubmitting ? "Submitting..." : "Regenerate block"}
              </Button>
            </div>
          </div>
        )}

        {regenerate.feedback ? (
          <div
            className={`rounded-[var(--radius-card)] px-4 py-4 ${
              regenerate.feedback.tone === "success"
                ? "bg-[var(--status-success-soft)] text-[var(--status-success)]"
                : regenerate.feedback.tone === "warning"
                  ? "bg-[var(--status-warning-soft)] text-[var(--status-warning)]"
                  : regenerate.feedback.tone === "danger"
                    ? "bg-[var(--status-danger-soft)] text-[var(--status-danger)]"
                    : "bg-[var(--status-info-soft)] text-[var(--status-info)]"
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h3 className="display-title text-lg font-semibold">{regenerate.feedback.title}</h3>
                <p className="mt-2 text-sm leading-6">{regenerate.feedback.description}</p>
              </div>
              <Button size="compact" variant="ghost" onClick={regenerate.dismissFeedback}>
                Dismiss
              </Button>
            </div>
          </div>
        ) : null}

        {task ? (
          <div className="space-y-3">
            <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="display-title text-lg font-semibold">Task {task.id}</h3>
                {task.replayed ? <StatusPill tone="info">Replay</StatusPill> : null}
              </div>

              <dl className="mt-3 grid gap-3 text-sm leading-6 text-[var(--text-secondary)]">
                <div>
                  <dt className="eyebrow text-[var(--text-muted)]">Status</dt>
                  <dd>{task.status}</dd>
                </div>
                <div>
                  <dt className="eyebrow text-[var(--text-muted)]">Requested</dt>
                  <dd>{formatDateTime(task.requested_at)}</dd>
                </div>
                {task.updated_at ? (
                  <div>
                    <dt className="eyebrow text-[var(--text-muted)]">Updated</dt>
                    <dd>{formatDateTime(task.updated_at)}</dd>
                  </div>
                ) : null}
                {task.progress_pct !== undefined && task.progress_pct !== null ? (
                  <div>
                    <dt className="eyebrow text-[var(--text-muted)]">Progress</dt>
                    <dd>{task.progress_pct}%</dd>
                  </div>
                ) : null}
                {task.instruction_version ? (
                  <div>
                    <dt className="eyebrow text-[var(--text-muted)]">New instruction version</dt>
                    <dd>{task.instruction_version}</dd>
                  </div>
                ) : null}
                {task.failed_stage ? (
                  <div>
                    <dt className="eyebrow text-[var(--text-muted)]">Failed stage</dt>
                    <dd>{task.failed_stage}</dd>
                  </div>
                ) : null}
              </dl>

              <div className="mt-4 space-y-2 text-sm leading-6 text-[var(--text-secondary)]">
                <p>{describeRegeneratePolling(regenerate.polling)}</p>
                {regenerate.polling.lastPolledAt ? (
                  <p>Last poll tick: {formatDateTime(regenerate.polling.lastPolledAt)}</p>
                ) : null}
                {regenerate.lastClientRequestId ? (
                  <p>Last request ID: {regenerate.lastClientRequestId}</p>
                ) : null}
              </div>

              <div className="mt-4 flex flex-wrap gap-3">
                <Button size="compact" variant="secondary" onClick={() => void regenerate.refreshCurrentTask()}>
                  Refresh task
                </Button>
                <Button size="compact" variant="ghost" onClick={onRefreshLatestInstruction}>
                  Refresh latest instruction
                </Button>
                {regenerate.polling.active ? (
                  <Button size="compact" variant="ghost" onClick={regenerate.stopPolling}>
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
