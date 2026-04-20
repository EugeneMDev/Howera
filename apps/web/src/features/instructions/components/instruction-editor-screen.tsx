"use client";

import { useEffect, useRef, useState } from "react";

import { useRouter } from "next/navigation";

import { InstructionTranscriptPanel } from "@/features/instructions/components/instruction-transcript-panel";
import { InstructionRegeneratePanel } from "@/features/instructions/components/instruction-regenerate-panel";
import { InstructionValidationPanel } from "@/features/instructions/components/instruction-validation-panel";
import { InstructionWorkspaceQuickNav } from "@/features/instructions/components/instruction-workspace-quick-nav";
import { useInstructionEditor } from "@/features/instructions/hooks";
import { InstructionExportPanel } from "@/features/exports/components/instruction-export-panel";
import { useInstructionExports } from "@/features/exports/hooks";
import {
  captureTextSelection,
  restoreTextSelection,
  type TextSelectionSnapshot,
} from "@/features/instructions/selection";
import {
  buildBlockIdSelection,
  buildCharRangeSelection,
  createRegenerateClientRequestId,
} from "@/features/instructions/regenerate";
import { useInstructionRegenerate } from "@/features/instructions/regenerate-hooks";
import { useInstructionTranscript } from "@/features/instructions/transcript-hooks";
import { useInstructionAnchors } from "@/features/screenshots/anchor-hooks";
import { useScreenshotAssetLifecycle } from "@/features/screenshots/asset-hooks";
import { InstructionAnchorPanel } from "@/features/screenshots/components/instruction-anchor-panel";
import { InstructionScreenshotPanel } from "@/features/screenshots/components/instruction-screenshot-panel";
import type { ScreenshotFormat, ScreenshotStrategy } from "@/features/screenshots/api";
import {
  buildScreenshotCharRange,
  createScreenshotIdempotencyKey,
  normalizeScreenshotBlockId,
} from "@/features/screenshots/extraction";
import { useScreenshotExtraction } from "@/features/screenshots/hooks";
import { formatDateTime } from "@/shared/lib/format-date";
import { Button } from "@/shared/ui/button";
import { ErrorState, LoadingState } from "@/shared/ui/async-state";
import { NoLeakNotFoundState } from "@/shared/ui/no-leak-not-found-state";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { StatusPill } from "@/shared/ui/status-pill";
import { Textarea } from "@/shared/ui/textarea";

function getValidationTone(status: "PASS" | "FAIL") {
  return status === "PASS" ? "success" : "warning";
}

function getDirtyTone(isDirty: boolean) {
  return isDirty ? "warning" : "success";
}

function FeedbackPanel({
  description,
  title,
  tone,
  onDismiss,
}: {
  description: string;
  onDismiss: () => void;
  title: string;
  tone: "danger" | "info" | "success" | "warning";
}) {
  const toneClass =
    tone === "success"
      ? "bg-[var(--status-success-soft)] text-[var(--status-success)]"
      : tone === "warning"
        ? "bg-[var(--status-warning-soft)] text-[var(--status-warning)]"
        : tone === "danger"
          ? "bg-[var(--status-danger-soft)] text-[var(--status-danger)]"
          : "bg-[var(--status-info-soft)] text-[var(--status-info)]";

  return (
    <div className={`rounded-[var(--radius-card)] px-4 py-4 ${toneClass}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="display-title text-xl font-semibold">{title}</h3>
          <p className="mt-2 text-sm leading-6">{description}</p>
        </div>
        <Button size="compact" variant="ghost" onClick={onDismiss}>
          Dismiss
        </Button>
      </div>
    </div>
  );
}

export function InstructionEditorScreen({ instructionId }: { instructionId: string }) {
  const router = useRouter();
  const editor = useInstructionEditor(instructionId);
  const [transcriptOpen, setTranscriptOpen] = useState(false);
  const [selectionState, setSelectionState] = useState<TextSelectionSnapshot | null>(null);
  const [regenerateMode, setRegenerateMode] = useState<"block_id" | "char_range">("char_range");
  const [blockId, setBlockId] = useState("");
  const [clientRequestId, setClientRequestId] = useState("");
  const [screenshotContextMode, setScreenshotContextMode] = useState<"block_id" | "char_range">(
    "char_range",
  );
  const [screenshotBlockId, setScreenshotBlockId] = useState("");
  const [screenshotIdempotencyKey, setScreenshotIdempotencyKey] = useState("");
  const [screenshotTimestampMs, setScreenshotTimestampMs] = useState("");
  const [screenshotOffsetMs, setScreenshotOffsetMs] = useState("0");
  const [screenshotStrategy, setScreenshotStrategy] = useState<ScreenshotStrategy>("precise");
  const [screenshotFormat, setScreenshotFormat] = useState<ScreenshotFormat>("png");
  const editorTextareaRef = useRef<HTMLTextAreaElement | null>(null);
  const selectionSnapshotRef = useRef<TextSelectionSnapshot | null>(null);
  const transcript = useInstructionTranscript(
    editor.instruction?.job_id ?? "",
    transcriptOpen && editor.instruction !== null,
  );
  const regenerate = useInstructionRegenerate({
    instructionId,
    onTaskSucceeded: () => {
      editor.refreshLatestInstruction();
    },
    onVersionConflict: () => {
      editor.refreshLatestInstruction();
    },
  });
  const screenshot = useScreenshotExtraction(instructionId, editor.instruction?.job_id ?? "");
  const exportsState = useInstructionExports({
    jobId: editor.instruction?.job_id ?? "",
    scopeKey: instructionId,
  });
  const anchors = useInstructionAnchors({
    instructionId,
    refreshToken: screenshot.task ? `${screenshot.task.task_id}:${screenshot.task.status}` : null,
    targetInstructionVersionId: editor.instruction ? String(editor.instruction.version) : null,
  });
  const assetLifecycle = useScreenshotAssetLifecycle({
    onAssetStateChanged: anchors.refresh,
    scopeKey: `${instructionId}:${anchors.selectedAnchorId ?? "none"}`,
  });

  useEffect(() => {
    restoreTextSelection(editorTextareaRef.current, selectionSnapshotRef.current);
  }, [transcript.settledRevision]);

  useEffect(() => {
    if (clientRequestId.length > 0) {
      return;
    }

    setClientRequestId(createRegenerateClientRequestId());
  }, [clientRequestId]);

  useEffect(() => {
    if (screenshotIdempotencyKey.length > 0) {
      return;
    }

    setScreenshotIdempotencyKey(createScreenshotIdempotencyKey());
  }, [screenshotIdempotencyKey]);

  if (editor.status === "loading") {
    return (
      <LoadingState
        description="Loading the latest instruction version and preparing editor-local draft state."
        title="Loading instruction"
      />
    );
  }

  if (editor.notFound) {
    return (
      <NoLeakNotFoundState
        resourceName="instruction"
        returnHref="/instructions"
        returnLabel="Back to instruction hub"
      />
    );
  }

  if (editor.status === "error" && editor.instruction === null) {
    return (
      <ErrorState
        action={
          <Button variant="secondary" onClick={editor.retryLoad}>
            Retry load
          </Button>
        }
        description={editor.error ?? "Instruction details could not be loaded."}
        title="Instruction load failed"
      />
    );
  }

  if (editor.instruction === null) {
    return null;
  }

  const instruction = editor.instruction;
  const latestServerVersion = editor.latestInstruction?.version ?? instruction.version;
  const selectedText =
    selectionState && selectionState.end > selectionState.start
      ? editor.draftMarkdown.slice(selectionState.start, selectionState.end)
      : "";

  function updateSelectionSnapshot() {
    const nextSelection = captureTextSelection(editorTextareaRef.current);
    selectionSnapshotRef.current = nextSelection;
    setSelectionState(nextSelection);
  }

  async function submitCharRangeRegenerate(): Promise<void> {
    const selection = buildCharRangeSelection(selectionState?.start, selectionState?.end);
    if (selection === null) {
      return;
    }

    await regenerate.submit({
      base_version: instruction.version,
      client_request_id: clientRequestId.trim(),
      selection,
    });
  }

  async function submitBlockIdRegenerate(): Promise<void> {
    const selection = buildBlockIdSelection(blockId);
    if (selection === null) {
      return;
    }

    await regenerate.submit({
      base_version: instruction.version,
      client_request_id: clientRequestId.trim(),
      selection,
    });
  }

  async function submitScreenshotExtraction(): Promise<void> {
    const normalizedTimestamp = Number(screenshotTimestampMs.trim());
    const normalizedOffset =
      screenshotOffsetMs.trim().length === 0 ? 0 : Number(screenshotOffsetMs.trim());

    if (
      !Number.isInteger(normalizedTimestamp) ||
      normalizedTimestamp < 0 ||
      !Number.isInteger(normalizedOffset)
    ) {
      return;
    }

    const charRange = buildScreenshotCharRange(selectionState?.start, selectionState?.end);
    const normalizedScreenshotBlockId = normalizeScreenshotBlockId(screenshotBlockId);
    const contextPayload =
      screenshotContextMode === "char_range"
        ? charRange
          ? { char_range: charRange }
          : null
        : normalizedScreenshotBlockId
          ? { block_id: normalizedScreenshotBlockId }
          : null;

    if (contextPayload === null) {
      return;
    }

    await screenshot.submit({
      ...contextPayload,
      format: screenshotFormat,
      idempotency_key: screenshotIdempotencyKey.trim(),
      instruction_id: instruction.instruction_id,
      instruction_version_id: String(instruction.version),
      offset_ms: normalizedOffset,
      strategy: screenshotStrategy,
      timestamp_ms: normalizedTimestamp,
    });
  }

  return (
    <div className="flex flex-col gap-4">
      <Panel variant="strong">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="eyebrow text-[var(--brand-primary-strong)]">Instruction editor</p>
            <h2 className="display-title mt-3 text-4xl font-semibold">
              Editing {instruction.instruction_id}
            </h2>
            <p className="mt-4 text-sm leading-6 text-[var(--text-secondary)] md:text-base">
              Save requests use `base_version={instruction.version}`. Local draft state stays in the
              editor even if the API rejects the save with `VERSION_CONFLICT`.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <StatusPill tone="info">v{instruction.version}</StatusPill>
            <StatusPill tone={getDirtyTone(editor.isDirty)}>
              {editor.isDirty ? "Unsaved changes" : "Saved"}
            </StatusPill>
            <StatusPill tone={getValidationTone(instruction.validation_status)}>
              {instruction.validation_status}
            </StatusPill>
            {editor.conflict ? <StatusPill tone="warning">Conflict</StatusPill> : null}
          </div>
        </div>
      </Panel>

      {editor.feedback ? (
        <FeedbackPanel
          description={editor.feedback.description}
          onDismiss={editor.dismissFeedback}
          title={editor.feedback.title}
          tone={editor.feedback.tone}
        />
      ) : null}

      <InstructionWorkspaceQuickNav />

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <section
          id="instruction-draft-section"
          className="scroll-mt-6"
          aria-label="Instruction draft editor"
        >
          <Panel>
            <PanelHeader>
              <p className="eyebrow text-[var(--text-muted)]">Markdown draft</p>
              <PanelTitle>Editor-local working copy</PanelTitle>
              <PanelDescription>
                Contract identity: {instruction.instruction_id}. Job {instruction.job_id}. Updated{" "}
                {formatDateTime(instruction.updated_at)}.
              </PanelDescription>
            </PanelHeader>

            <div className="space-y-4">
              <Textarea
                aria-label="Instruction markdown editor"
                className="min-h-[520px] bg-[rgba(29,31,29,0.96)] text-[var(--text-inverse)] placeholder:text-[rgba(249,246,239,0.52)]"
                onClick={updateSelectionSnapshot}
                onChange={(event) => editor.setDraftMarkdown(event.currentTarget.value)}
                onKeyUp={updateSelectionSnapshot}
                onSelect={updateSelectionSnapshot}
                placeholder="# Add instruction markdown"
                ref={editorTextareaRef}
                spellCheck={false}
                value={editor.draftMarkdown}
              />

              <div className="flex flex-wrap gap-3">
                <Button
                  aria-controls="instruction-transcript-section"
                  aria-expanded={transcriptOpen}
                  variant="ghost"
                  onClick={() => setTranscriptOpen((current) => !current)}
                >
                  {transcriptOpen ? "Hide transcript" : "Open transcript"}
                </Button>
                <Button
                  disabled={!editor.isDirty || editor.isSaving}
                  onClick={() => void editor.saveDraft()}
                >
                  {editor.isSaving ? "Saving..." : "Save instruction"}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    router.push("/instructions");
                  }}
                >
                  Open another instruction
                </Button>
              </div>
            </div>
          </Panel>
        </section>

        <div className="space-y-4">
          <section
            id="instruction-anchor-section"
            className="scroll-mt-6"
            aria-label="Instruction anchor tools"
          >
            <InstructionAnchorPanel
              anchorsState={anchors}
              currentInstructionVersion={instruction.version}
              jobId={instruction.job_id}
              lifecycle={assetLifecycle}
              latestServerVersion={latestServerVersion}
            />
          </section>

          <section
            id="instruction-screenshot-section"
            className="scroll-mt-6"
            aria-label="Instruction screenshot tools"
          >
            <InstructionScreenshotPanel
              blockId={screenshotBlockId}
              contextMode={screenshotContextMode}
              format={screenshotFormat}
              idempotencyKey={screenshotIdempotencyKey}
              isDirty={editor.isDirty}
              offsetMs={screenshotOffsetMs}
              onBlockIdChange={setScreenshotBlockId}
              onContextModeChange={setScreenshotContextMode}
              onDismissFeedback={screenshot.dismissFeedback}
              onFormatChange={setScreenshotFormat}
              onGenerateIdempotencyKey={() =>
                setScreenshotIdempotencyKey(createScreenshotIdempotencyKey())
              }
              onIdempotencyKeyChange={setScreenshotIdempotencyKey}
              onOffsetMsChange={setScreenshotOffsetMs}
              onRefreshCurrentTask={() => {
                void screenshot.refreshCurrentTask();
              }}
              onStopPolling={screenshot.stopPolling}
              onStrategyChange={setScreenshotStrategy}
              onSubmit={() => {
                void submitScreenshotExtraction();
              }}
              onTimestampMsChange={setScreenshotTimestampMs}
              screenshot={screenshot}
              selectedText={selectedText}
              selection={selectionState}
              strategy={screenshotStrategy}
              timestampMs={screenshotTimestampMs}
            />
          </section>

          <section
            id="instruction-export-section"
            className="scroll-mt-6"
            aria-label="Instruction export tools"
          >
            <InstructionExportPanel
              currentInstructionVersion={instruction.version}
              exportsState={exportsState}
              isDirty={editor.isDirty}
              jobId={instruction.job_id}
            />
          </section>

          <section
            id="instruction-regenerate-section"
            className="scroll-mt-6"
            aria-label="Instruction regenerate tools"
          >
            <InstructionRegeneratePanel
              blockId={blockId}
              clientRequestId={clientRequestId}
              isDirty={editor.isDirty}
              mode={regenerateMode}
              onBlockIdChange={setBlockId}
              onClientRequestIdChange={setClientRequestId}
              onGenerateClientRequestId={() =>
                setClientRequestId(createRegenerateClientRequestId())
              }
              onModeChange={setRegenerateMode}
              onRefreshLatestInstruction={editor.refreshLatestInstruction}
              onSubmitBlockId={() => {
                void submitBlockIdRegenerate();
              }}
              onSubmitCharRange={() => {
                void submitCharRangeRegenerate();
              }}
              regenerate={regenerate}
              selectedText={selectedText}
              selection={selectionState}
            />
          </section>

          <section
            id="instruction-transcript-section"
            className="scroll-mt-6"
            aria-label="Instruction transcript context"
          >
            <InstructionTranscriptPanel
              onToggle={() => setTranscriptOpen((current) => !current)}
              transcript={transcript}
              transcriptOpen={transcriptOpen}
            />
          </section>

          <section aria-label="Instruction persistence metadata">
            <Panel variant="muted">
              <PanelHeader>
                <p className="eyebrow text-[var(--text-muted)]">Version metadata</p>
                <PanelTitle>Persistence state</PanelTitle>
              </PanelHeader>

              <div className="space-y-4 text-sm leading-6 text-[var(--text-secondary)]">
                <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                  <p className="eyebrow text-[var(--brand-primary-strong)]">Current save base</p>
                  <p className="mt-2">
                    Local saves currently target version {instruction.version}. Latest known server
                    version is {latestServerVersion}.
                  </p>
                </div>
              </div>
            </Panel>
          </section>

          <section
            id="instruction-validation-section"
            className="scroll-mt-6"
            aria-label="Instruction validation state"
          >
            <InstructionValidationPanel
              instruction={instruction}
              latestServerVersion={latestServerVersion}
            />
          </section>

          {editor.conflict ? (
            <section aria-label="Instruction conflict recovery" className="scroll-mt-6">
              <Panel>
                <PanelHeader>
                  <p className="eyebrow text-[var(--status-warning)]">Conflict recovery</p>
                  <PanelTitle>Version {editor.conflict.current_version} is already live</PanelTitle>
                  <PanelDescription>
                    Your draft still contains local edits based on version{" "}
                    {editor.conflict.base_version}. Choose whether to discard those edits or keep
                    them and manually merge against the latest server content.
                  </PanelDescription>
                </PanelHeader>

                <div className="space-y-4">
                  <div className="flex flex-wrap gap-3">
                    <Button variant="secondary" onClick={() => void editor.reloadLatestIntoEditor()}>
                      Reload latest into editor
                    </Button>
                    <Button variant="ghost" onClick={editor.useLatestAsMergeBase}>
                      Keep draft and use latest as base
                    </Button>
                  </div>

                  <div className="rounded-[var(--radius-card)] bg-[rgba(29,31,29,0.96)] p-4 text-[var(--text-inverse)]">
                    <p className="eyebrow text-[rgba(249,246,239,0.62)]">Latest server markdown</p>
                    <pre
                      className="mt-3 overflow-x-auto whitespace-pre-wrap text-sm leading-7"
                      style={{ fontFamily: "var(--font-mono)" }}
                    >
                      {editor.latestInstruction?.markdown ?? "Latest server markdown is unavailable."}
                    </pre>
                  </div>
                </div>
              </Panel>
            </section>
          ) : null}
        </div>
      </div>
    </div>
  );
}
