import { ApiClientError } from "@/shared/api/errors";
import {
  parseTranscriptNotReadyDetails,
  type JobStatus,
  type TranscriptPage,
  type TranscriptSegment,
} from "@/features/jobs/api";

export type TranscriptPanelStatus = "error" | "idle" | "loading" | "not-ready" | "success";

export interface TranscriptPanelState {
  currentStatus: JobStatus | null;
  error: string | null;
  hasLoadedOnce: boolean;
  isLoadingMore: boolean;
  isRefreshing: boolean;
  items: TranscriptSegment[];
  limit: number;
  nextCursor: string | null;
  settledRevision: number;
  status: TranscriptPanelStatus;
}

export function createTranscriptPanelState(limit: number): TranscriptPanelState {
  return {
    currentStatus: null,
    error: null,
    hasLoadedOnce: false,
    isLoadingMore: false,
    isRefreshing: false,
    items: [],
    limit,
    nextCursor: null,
    settledRevision: 0,
    status: "idle",
  };
}

function toSegmentKey(segment: TranscriptSegment): string {
  return `${segment.start_ms}:${segment.end_ms}:${segment.text}`;
}

export function appendTranscriptSegments(
  existingSegments: TranscriptSegment[],
  incomingSegments: TranscriptSegment[],
): TranscriptSegment[] {
  const seen = new Set(existingSegments.map(toSegmentKey));
  const nextSegments = [...existingSegments];

  for (const segment of incomingSegments) {
    const key = toSegmentKey(segment);
    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    nextSegments.push(segment);
  }

  return nextSegments;
}

export function applyTranscriptPage(
  currentState: TranscriptPanelState,
  page: TranscriptPage,
  mode: "append" | "replace",
): TranscriptPanelState {
  return {
    ...currentState,
    currentStatus: null,
    error: null,
    hasLoadedOnce: true,
    isLoadingMore: false,
    isRefreshing: false,
    items:
      mode === "append"
        ? appendTranscriptSegments(currentState.items, page.items)
        : [...page.items],
    limit: page.limit,
    nextCursor: page.next_cursor ?? null,
    settledRevision: currentState.settledRevision + 1,
    status: "success",
  };
}

export function applyTranscriptNotReady(
  currentState: TranscriptPanelState,
  error: ApiClientError,
): TranscriptPanelState {
  const details = parseTranscriptNotReadyDetails(error.details);

  return {
    ...currentState,
    currentStatus: details?.current_status ?? null,
    error: error.message,
    hasLoadedOnce: true,
    isLoadingMore: false,
    isRefreshing: false,
    items: [],
    nextCursor: null,
    settledRevision: currentState.settledRevision + 1,
    status: "not-ready",
  };
}

export function formatTranscriptTimestamp(milliseconds: number): string {
  const totalMilliseconds = Math.max(0, milliseconds);
  const totalSeconds = Math.floor(totalMilliseconds / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const remainderMilliseconds = totalMilliseconds % 1000;

  const secondsLabel = String(seconds).padStart(2, "0");
  const millisecondsLabel = String(remainderMilliseconds).padStart(3, "0");

  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${secondsLabel}.${millisecondsLabel}`;
  }

  return `${minutes}:${secondsLabel}.${millisecondsLabel}`;
}
