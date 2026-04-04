"use client";

import React from "react";

import type { useInstructionTranscript } from "@/features/instructions/transcript-hooks";
import { formatTranscriptTimestamp } from "@/features/instructions/transcript-state";
import { EmptyState, ErrorState, LoadingState } from "@/shared/ui/async-state";
import { Button } from "@/shared/ui/button";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/shared/ui/panel";
import { StatusPill } from "@/shared/ui/status-pill";

interface InstructionTranscriptPanelProps {
  onToggle: () => void;
  transcript: ReturnType<typeof useInstructionTranscript>;
  transcriptOpen: boolean;
}

export function InstructionTranscriptPanel({
  onToggle,
  transcript,
  transcriptOpen,
}: InstructionTranscriptPanelProps) {
  if (!transcriptOpen) {
    return (
      <Panel variant="muted">
        <PanelHeader>
          <p className="eyebrow text-[var(--text-muted)]">Transcript context</p>
          <PanelTitle>Keep source audio nearby</PanelTitle>
          <PanelDescription>
            Open the transcript panel to compare source wording with the current instruction draft.
          </PanelDescription>
        </PanelHeader>

        <div className="flex flex-wrap gap-3">
          <Button
            aria-controls="instruction-transcript-section"
            aria-expanded={transcriptOpen}
            variant="secondary"
            onClick={onToggle}
          >
            Open transcript
          </Button>
        </div>
      </Panel>
    );
  }

  return (
    <Panel>
      <PanelHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="eyebrow text-[var(--text-muted)]">Transcript context</p>
            <PanelTitle>Source segments</PanelTitle>
            <PanelDescription>
              Refreshing transcript data keeps the editor usable and leaves local draft state intact.
            </PanelDescription>
          </div>

          <div className="flex flex-wrap gap-2">
            {transcript.currentStatus ? <StatusPill tone="warning">{transcript.currentStatus}</StatusPill> : null}
            {transcript.isRefreshing ? <StatusPill tone="info">Refreshing</StatusPill> : null}
          </div>
        </div>
      </PanelHeader>

      <div className="space-y-4">
        <div className="flex flex-wrap gap-3">
          <Button size="compact" variant="secondary" onClick={transcript.refresh}>
            Refresh transcript
          </Button>
          <Button
            aria-controls="instruction-transcript-section"
            aria-expanded={transcriptOpen}
            size="compact"
            variant="ghost"
            onClick={onToggle}
          >
            Hide transcript
          </Button>
        </div>

        {transcript.status === "loading" && transcript.items.length === 0 ? (
          <LoadingState
            description="Loading transcript segments with contract pagination."
            title="Loading transcript"
          />
        ) : null}

        {transcript.status === "not-ready" ? (
          <EmptyState
            action={
              <Button size="compact" variant="secondary" onClick={transcript.refresh}>
                Try again
              </Button>
            }
            description={
              transcript.currentStatus
                ? `Transcript is not available while the job is in ${transcript.currentStatus}.`
                : "Transcript is not available for the current job state yet."
            }
            title="Transcript not ready"
          />
        ) : null}

        {transcript.status === "error" && transcript.items.length === 0 ? (
          <ErrorState
            action={
              <Button size="compact" variant="secondary" onClick={transcript.refresh}>
                Retry transcript
              </Button>
            }
            description={transcript.error ?? "Transcript segments could not be loaded."}
            title="Transcript unavailable"
          />
        ) : null}

        {transcript.status === "success" && transcript.items.length === 0 ? (
          <EmptyState
            action={
              <Button size="compact" variant="secondary" onClick={transcript.refresh}>
                Refresh transcript
              </Button>
            }
            description="The API returned no transcript segments for this job yet."
            title="Transcript is empty"
          />
        ) : null}

        {transcript.items.length > 0 ? (
          <div className="space-y-3">
            <div className="rounded-[var(--radius-card)] bg-white/45 px-4 py-3 text-sm leading-6 text-[var(--text-secondary)]">
              Showing {transcript.items.length} segment{transcript.items.length === 1 ? "" : "s"}.
              {transcript.nextCursor ? " More pages are available." : " End of transcript reached."}
            </div>

            <div className="space-y-3">
              {transcript.items.map((segment, index) => (
                <article
                  key={`${segment.start_ms}-${segment.end_ms}-${index}`}
                  className="rounded-[var(--radius-card)] bg-white/45 px-4 py-4"
                >
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="display-title text-lg font-semibold">
                      {formatTranscriptTimestamp(segment.start_ms)} - {formatTranscriptTimestamp(segment.end_ms)}
                    </h3>
                    <StatusPill tone="info">{Math.max(0, segment.end_ms - segment.start_ms)} ms</StatusPill>
                  </div>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-[var(--text-primary)]">
                    {segment.text}
                  </p>
                </article>
              ))}
            </div>

            {transcript.error ? (
              <div className="rounded-[var(--radius-card)] bg-[var(--status-warning-soft)] px-4 py-3 text-sm text-[var(--status-warning)]">
                {transcript.error}
              </div>
            ) : null}

            {transcript.hasMore ? (
              <div className="flex flex-wrap gap-3">
                <Button
                  disabled={transcript.isLoadingMore}
                  size="compact"
                  variant="secondary"
                  onClick={() => void transcript.loadMore()}
                >
                  {transcript.isLoadingMore ? "Loading more..." : "Load more segments"}
                </Button>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
