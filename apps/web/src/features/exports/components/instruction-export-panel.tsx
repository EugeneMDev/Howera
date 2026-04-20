"use client";

import React, { useEffect, useState } from "react";

import type { useInstructionExports } from "@/features/exports/hooks";
import {
  createExportIdempotencyKey,
  describeExportPolling,
  getExportDownloadAvailability,
  getExportStatusTone,
} from "@/features/exports/feedback";
import type { ExportFormat } from "@/features/exports/api";
import { formatDateTime } from "@/shared/lib/format-date";
import { EmptyState } from "@/shared/ui/async-state";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { StatusPill } from "@/shared/ui/status-pill";

interface InstructionExportPanelProps {
  currentInstructionVersion: number;
  exportsState: ReturnType<typeof useInstructionExports>;
  isDirty: boolean;
  jobId: string;
}

const EXPORT_FORMATS: ExportFormat[] = ["MD_ZIP", "PDF"];

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

function getGuidanceToneClass(tone: "danger" | "info" | "success" | "warning"): string {
  if (tone === "success") {
    return "text-[var(--status-success)]";
  }

  if (tone === "warning") {
    return "text-[var(--status-warning)]";
  }

  if (tone === "danger") {
    return "text-[var(--status-danger)]";
  }

  return "text-[var(--status-info)]";
}

export function InstructionExportPanel({
  currentInstructionVersion,
  exportsState,
  isDirty,
  jobId,
}: InstructionExportPanelProps) {
  const [idempotencyKey, setIdempotencyKey] = useState("");
  const pendingExportCount = exportsState.records.filter((record) => record.status === "REQUESTED" || record.status === "RUNNING").length;

  useEffect(() => {
    setIdempotencyKey(createExportIdempotencyKey());
  }, [currentInstructionVersion]);

  async function requestExport(format: ExportFormat): Promise<void> {
    const succeeded = await exportsState.submit({
      format,
      idempotency_key: idempotencyKey.trim(),
      instruction_version_id: String(currentInstructionVersion),
    });

    if (succeeded) {
      setIdempotencyKey(createExportIdempotencyKey());
    }
  }

  return (
    <Panel>
      <PanelHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="eyebrow text-[var(--text-muted)]">Export control</p>
            <PanelTitle>Request deliverables and track export state</PanelTitle>
            <PanelDescription>
              Export requests stay bound to saved instruction version {currentInstructionVersion}
              while the rest of the editor workspace remains available.
            </PanelDescription>
          </div>

          <StatusPill tone={pendingExportCount > 0 ? "warning" : "info"}>
            {pendingExportCount > 0 ? `${pendingExportCount} active` : "Idle"}
          </StatusPill>
        </div>
      </PanelHeader>

      <div className="space-y-4">
        <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4 text-sm leading-6 text-[var(--text-secondary)]">
          <p>Job context: {jobId}</p>
          <p>Saved instruction version: v{currentInstructionVersion}</p>
          <p>Formats supported by contract: MD_ZIP and PDF.</p>
        </div>

        {isDirty ? (
          <div className="rounded-[var(--radius-card)] bg-[var(--status-warning-soft)] px-4 py-3 text-sm text-[var(--status-warning)]">
            Unsaved draft edits are not included in export requests. The API always exports the
            latest saved instruction version shown above.
          </div>
        ) : null}

        <label className="block">
          <span className="mb-2 block text-sm font-medium text-[var(--text-primary)]">
            Export idempotency key
          </span>
          <div className="flex flex-wrap gap-3">
            <Input
              autoComplete="off"
              className="min-w-[220px] flex-1"
              name="exportIdempotencyKey"
              onChange={(event) => setIdempotencyKey(event.currentTarget.value)}
              value={idempotencyKey}
            />
            <Button
              size="compact"
              variant="secondary"
              onClick={() => setIdempotencyKey(createExportIdempotencyKey())}
            >
              New key
            </Button>
          </div>
        </label>

        <div className="flex flex-wrap gap-3">
          {EXPORT_FORMATS.map((format) => (
            <Button
              key={format}
              disabled={exportsState.isSubmitting || idempotencyKey.trim().length === 0}
              onClick={() => {
                void requestExport(format);
              }}
            >
              {exportsState.isSubmitting ? "Submitting..." : `Request ${format}`}
            </Button>
          ))}
        </div>

        {exportsState.feedback
          ? renderFeedbackCard(exportsState.feedback, exportsState.dismissFeedback)
          : null}

        <div className="rounded-[var(--radius-card)] bg-[rgba(84,70,49,0.08)] px-4 py-4 text-sm leading-6 text-[var(--text-secondary)]">
          <p>{describeExportPolling(exportsState.polling, pendingExportCount)}</p>
          {exportsState.polling.startedAt ? (
            <p>Tracking started: {formatDateTime(exportsState.polling.startedAt)}</p>
          ) : null}
          {exportsState.polling.lastPolledAt ? (
            <p>Last poll tick: {formatDateTime(exportsState.polling.lastPolledAt)}</p>
          ) : null}
          {exportsState.lastIdempotencyKey ? (
            <p>Last idempotency key: {exportsState.lastIdempotencyKey}</p>
          ) : null}
          {exportsState.polling.active ? (
            <div className="mt-3 flex flex-wrap gap-3">
              <Button size="compact" variant="ghost" onClick={exportsState.stopPolling}>
                Stop polling
              </Button>
            </div>
          ) : null}
        </div>

        {exportsState.records.length > 0 ? (
          <div className="space-y-3">
            <h3 className="display-title text-lg font-semibold">Export records</h3>
            {exportsState.records.map((record) => {
              const downloadAvailability = getExportDownloadAvailability(record);
              const isPreparingDownload = exportsState.pendingDownloadExportId === record.id;
              const downloadGuidanceId = `export-download-guidance-${record.id}`;

              return (
                <article key={record.id} className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4 className="display-title text-base font-semibold">{record.format}</h4>
                      <StatusPill tone={getExportStatusTone(record.status)}>{record.status}</StatusPill>
                      {record.replayed ? <StatusPill tone="info">Replay</StatusPill> : null}
                      {downloadAvailability.canDownload ? (
                        <StatusPill tone="success">Ready for secure download</StatusPill>
                      ) : null}
                    </div>

                    <div className="flex flex-wrap gap-3">
                      <Button
                        aria-describedby={downloadGuidanceId}
                        disabled={record.status !== "SUCCEEDED" || isPreparingDownload}
                        size="compact"
                        onClick={() => {
                          void exportsState.downloadExport(record.id);
                        }}
                      >
                        {isPreparingDownload ? "Preparing..." : "Download export"}
                      </Button>
                      <Button
                        size="compact"
                        variant="secondary"
                        onClick={() => {
                          void exportsState.refreshExport(record.id);
                        }}
                      >
                        Refresh status
                      </Button>
                      {record.status === "FAILED" ? (
                        <Button
                          size="compact"
                          onClick={() => {
                            void requestExport(record.format);
                          }}
                        >
                          Request again
                        </Button>
                      ) : null}
                    </div>
                  </div>

                  <dl className="mt-3 grid gap-3 text-sm leading-6 text-[var(--text-secondary)]">
                    <div>
                      <dt className="eyebrow text-[var(--text-muted)]">Export ID</dt>
                      <dd style={{ fontFamily: "var(--font-mono)" }}>{record.id}</dd>
                    </div>
                    <div>
                      <dt className="eyebrow text-[var(--text-muted)]">Instruction version</dt>
                      <dd>v{record.instruction_version_id}</dd>
                    </div>
                    <div>
                      <dt className="eyebrow text-[var(--text-muted)]">Updated</dt>
                      <dd>{formatDateTime(record.updated_at)}</dd>
                    </div>
                    {record.download_url_expires_at ? (
                      <div>
                        <dt className="eyebrow text-[var(--text-muted)]">Signed URL expiry</dt>
                        <dd>{formatDateTime(record.download_url_expires_at)}</dd>
                      </div>
                    ) : null}
                    <div>
                      <dt className="eyebrow text-[var(--text-muted)]">Created</dt>
                      <dd>{formatDateTime(record.created_at)}</dd>
                    </div>
                    <div>
                      <dt className="eyebrow text-[var(--text-muted)]">Identity key</dt>
                      <dd style={{ fontFamily: "var(--font-mono)" }}>{record.identity_key}</dd>
                    </div>
                    <div>
                      <dt className="eyebrow text-[var(--text-muted)]">Screenshot set hash</dt>
                      <dd style={{ fontFamily: "var(--font-mono)" }}>{record.screenshot_set_hash}</dd>
                    </div>
                    {record.last_audit_event ? (
                      <div>
                        <dt className="eyebrow text-[var(--text-muted)]">Last audit event</dt>
                        <dd>{record.last_audit_event}</dd>
                      </div>
                    ) : null}
                    {record.provenance ? (
                      <div>
                        <dt className="eyebrow text-[var(--text-muted)]">Provenance</dt>
                        <dd>
                          {record.provenance.anchors.length} anchor
                          {record.provenance.anchors.length === 1 ? "" : "s"} frozen from snapshot{" "}
                          {record.provenance.instruction_snapshot_id}.
                        </dd>
                      </div>
                    ) : null}
                  </dl>

                  <p
                    id={downloadGuidanceId}
                    className={`mt-4 text-sm leading-6 ${getGuidanceToneClass(downloadAvailability.tone)}`}
                  >
                    {downloadAvailability.description}
                  </p>
                </article>
              );
            })}
          </div>
        ) : (
          <EmptyState
            description="No exports have been requested from this instruction workspace yet."
            title="No export records"
          />
        )}
      </div>
    </Panel>
  );
}
