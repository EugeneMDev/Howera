"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiClientError, isNoLeakNotFoundError } from "@/shared/api/errors";
import { useApiClient } from "@/shared/providers/app-providers";
import { getJobTranscript } from "@/features/jobs/api";
import {
  applyTranscriptNotReady,
  applyTranscriptPage,
  createTranscriptPanelState,
  type TranscriptPanelState,
} from "@/features/instructions/transcript-state";

function toErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

export function useInstructionTranscript(jobId: string, enabled: boolean, pageLimit = 120) {
  const apiClient = useApiClient();
  const [state, setState] = useState<TranscriptPanelState>(() => createTranscriptPanelState(pageLimit));

  useEffect(() => {
    setState(createTranscriptPanelState(pageLimit));
  }, [jobId, pageLimit]);

  const loadFirstPage = useCallback(
    async (mode: "initial" | "refresh"): Promise<void> => {
      setState((current) => ({
        ...current,
        currentStatus: null,
        error: null,
        isLoadingMore: false,
        isRefreshing: mode === "refresh" && current.items.length > 0,
        status: current.items.length > 0 && mode === "refresh" ? current.status : "loading",
      }));

      try {
        const page = await getJobTranscript(apiClient, jobId, { limit: pageLimit });
        setState((current) => applyTranscriptPage(current, page, "replace"));
      } catch (error) {
        if (error instanceof ApiClientError && error.status === 409 && error.code === "TRANSCRIPT_NOT_READY") {
          setState((current) => applyTranscriptNotReady(current, error));
          return;
        }

        setState((current) => ({
          ...current,
          currentStatus: null,
          error: isNoLeakNotFoundError(error)
            ? "Transcript is unavailable for this job."
            : toErrorMessage(error, "Transcript segments could not be loaded."),
          hasLoadedOnce: true,
          isLoadingMore: false,
          isRefreshing: false,
          items: isNoLeakNotFoundError(error) ? [] : current.items,
          nextCursor: isNoLeakNotFoundError(error) ? null : current.nextCursor,
          settledRevision: current.settledRevision + 1,
          status: "error",
        }));
      }
    },
    [apiClient, jobId, pageLimit],
  );

  const loadMore = useCallback(async (): Promise<void> => {
    if (!state.nextCursor || state.isLoadingMore) {
      return;
    }

    setState((current) => ({
      ...current,
      error: null,
      isLoadingMore: true,
    }));

    try {
      const page = await getJobTranscript(apiClient, jobId, {
        cursor: state.nextCursor,
        limit: state.limit,
      });
      setState((current) => applyTranscriptPage(current, page, "append"));
    } catch (error) {
      setState((current) => ({
        ...current,
        error: toErrorMessage(error, "More transcript segments could not be loaded."),
        isLoadingMore: false,
        settledRevision: current.settledRevision + 1,
        status: current.items.length > 0 ? "success" : "error",
      }));
    }
  }, [apiClient, jobId, state.isLoadingMore, state.limit, state.nextCursor]);

  useEffect(() => {
    if (!enabled || state.hasLoadedOnce) {
      return;
    }

    void loadFirstPage("initial");
  }, [enabled, loadFirstPage, state.hasLoadedOnce]);

  return {
    ...state,
    hasMore: state.nextCursor !== null,
    loadMore,
    refresh() {
      void loadFirstPage("refresh");
    },
  };
}
