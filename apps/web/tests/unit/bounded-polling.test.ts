import assert from "node:assert/strict";
import test from "node:test";

import {
  createPollingPausedFeedback,
  describePollingActivity,
  hasPollingAttemptWindowEnded,
} from "../../src/shared/hooks/use-bounded-polling";

test("bounded polling helpers report active, stopped, and idle states consistently", () => {
  assert.equal(
    describePollingActivity(
      {
        active: true,
        attemptsRemaining: 4,
        maxAttempts: 8,
        startedAt: "2026-04-03T10:00:00Z",
      },
      { activePrefix: "Watching regenerate progression" },
    ),
    "Watching regenerate progression. Polling active with 4 of 8 attempts remaining.",
  );

  assert.equal(
    describePollingActivity(
      {
        active: false,
        attemptsRemaining: 0,
        maxAttempts: 8,
        startedAt: "2026-04-03T10:00:00Z",
      },
      { stoppedPrefix: "Watching regenerate progression" },
    ),
    "Watching regenerate progression. Polling stopped after 8 attempts.",
  );

  assert.equal(
    describePollingActivity(
      {
        active: false,
        attemptsRemaining: 0,
        maxAttempts: 8,
        startedAt: null,
      },
      { idleMessage: "Auto-refresh is idle." },
    ),
    "Auto-refresh is idle.",
  );
});

test("bounded polling helpers expose timeout feedback and attempt-window exhaustion", () => {
  assert.equal(
    hasPollingAttemptWindowEnded({
      active: false,
      attemptsRemaining: 0,
      startedAt: "2026-04-03T10:00:00Z",
    }),
    true,
  );
  assert.equal(
    hasPollingAttemptWindowEnded({
      active: true,
      attemptsRemaining: 2,
      startedAt: "2026-04-03T10:00:00Z",
    }),
    false,
  );

  assert.deepEqual(
    createPollingPausedFeedback(
      "Refresh task status manually to continue tracking this regenerate request.",
    ),
    {
      description:
        "Polling stopped after the bounded retry window. Refresh task status manually to continue tracking this regenerate request.",
      title: "Polling paused",
      tone: "warning",
    },
  );
});
