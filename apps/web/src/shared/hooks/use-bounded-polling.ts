"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import type { FeedbackMessage } from "@/shared/ui/feedback";

export interface BoundedPollingState {
  active: boolean;
  attemptsRemaining: number;
  intervalMs: number;
  lastPolledAt: string | null;
  maxAttempts: number;
  reason: string | null;
  startedAt: string | null;
  watchValue: string | null;
}

interface StartPollingOptions {
  intervalMs?: number;
  maxAttempts?: number;
  reason: string;
  watchValue: string | null;
}

const DEFAULT_INTERVAL_MS = 2500;
const DEFAULT_MAX_ATTEMPTS = 6;

const INITIAL_STATE: BoundedPollingState = {
  active: false,
  attemptsRemaining: 0,
  intervalMs: DEFAULT_INTERVAL_MS,
  lastPolledAt: null,
  maxAttempts: DEFAULT_MAX_ATTEMPTS,
  reason: null,
  startedAt: null,
  watchValue: null,
};

interface PollingActivityOptions {
  activePrefix?: string;
  idleMessage?: string;
  stoppedPrefix?: string;
}

export function hasPollingAttemptWindowEnded(
  polling: Pick<BoundedPollingState, "active" | "attemptsRemaining" | "startedAt">,
): boolean {
  return !polling.active && polling.startedAt !== null && polling.attemptsRemaining <= 0;
}

export function describePollingActivity(
  polling: Pick<BoundedPollingState, "active" | "attemptsRemaining" | "maxAttempts" | "startedAt">,
  { activePrefix, idleMessage = "Polling is idle.", stoppedPrefix }: PollingActivityOptions = {},
): string {
  if (polling.active) {
    const message = `Polling active with ${polling.attemptsRemaining} of ${polling.maxAttempts} attempts remaining.`;
    return activePrefix ? `${activePrefix}. ${message}` : message;
  }

  if (polling.startedAt) {
    const message = `Polling stopped after ${polling.maxAttempts} attempts.`;
    return stoppedPrefix ? `${stoppedPrefix}. ${message}` : message;
  }

  return idleMessage;
}

export function createPollingPausedFeedback(nextStepDescription: string): FeedbackMessage {
  return {
    description: `Polling stopped after the bounded retry window. ${nextStepDescription}`,
    title: "Polling paused",
    tone: "warning",
  };
}

export function useBoundedPolling({ onPoll }: { onPoll: () => void }) {
  const [polling, setPolling] = useState<BoundedPollingState>(INITIAL_STATE);
  const onPollRef = useRef(onPoll);

  onPollRef.current = onPoll;

  useEffect(() => {
    if (!polling.active) {
      return;
    }

    if (polling.attemptsRemaining <= 0) {
      setPolling((current) => (current.active ? { ...current, active: false } : current));
      return;
    }

    const timeoutId = window.setTimeout(() => {
      onPollRef.current();
      setPolling((current) =>
        current.active
          ? {
              ...current,
              attemptsRemaining: current.attemptsRemaining - 1,
              lastPolledAt: new Date().toISOString(),
            }
          : current,
      );
    }, polling.intervalMs);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [polling.active, polling.attemptsRemaining, polling.intervalMs]);

  const startPolling = useCallback(
    ({
      intervalMs = DEFAULT_INTERVAL_MS,
      maxAttempts = DEFAULT_MAX_ATTEMPTS,
      reason,
      watchValue,
    }: StartPollingOptions) => {
      setPolling({
        active: true,
        attemptsRemaining: maxAttempts,
        intervalMs,
        lastPolledAt: null,
        maxAttempts,
        reason,
        startedAt: new Date().toISOString(),
        watchValue,
      });
    },
    [],
  );

  const stopPolling = useCallback(() => {
    setPolling((current) => (current.active ? { ...current, active: false } : current));
  }, []);

  return {
    polling,
    startPolling,
    stopPolling,
  };
}
