import assert from "node:assert/strict";
import test from "node:test";

import { describeCommonApiError, toUserSafeErrorMessage } from "../../src/shared/api/error-feedback";
import { ApiClientError } from "../../src/shared/api/errors";

const baseOptions = {
  actionLabel: "Export request",
  fallbackDescription: "Export request could not be completed.",
  failedTitle: "Export request failed",
  invalidRequestTitle: "Export request rejected",
  noLeakDescription:
    "The export context is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
  noLeakTitle: "Export context unavailable",
  rejectedTitle: "Export request rejected",
};

test("shared error feedback maps common API statuses into user-safe messages", () => {
  assert.deepEqual(
    describeCommonApiError(
      new ApiClientError(400, {
        code: "EXPORT_REQUEST_INVALID",
        message: "Unsupported format or invalid instruction version.",
      }),
      baseOptions,
    ),
    {
      description: "Unsupported format or invalid instruction version.",
      title: "Export request rejected",
      tone: "warning",
    },
  );

  assert.deepEqual(
    describeCommonApiError(
      new ApiClientError(401, {
        code: "UNAUTHORIZED",
        message: "Expired Firebase session",
      }),
      baseOptions,
    ),
    {
      description: "Your session expired or was rejected by the API. Sign in again.",
      title: "Session unavailable",
      tone: "warning",
    },
  );

  assert.deepEqual(
    describeCommonApiError(
      new ApiClientError(404, {
        code: "RESOURCE_NOT_FOUND",
        message: "Resource not found",
      }),
      baseOptions,
    ),
    {
      description:
        "The export context is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
      title: "Export context unavailable",
      tone: "danger",
    },
  );

  assert.deepEqual(
    describeCommonApiError(
      new ApiClientError(409, {
        code: "VERSION_CONFLICT",
        message: "Instruction version changed.",
      }),
      {
        ...baseOptions,
        conflictTitle: "Export request conflicted",
      },
    ),
    {
      description: "Instruction version changed.",
      title: "Export request conflicted",
      tone: "warning",
    },
  );

  assert.deepEqual(
    describeCommonApiError(
      new ApiClientError(502, {
        code: "UPSTREAM_ERROR",
        message: "Temporary workflow outage.",
      }),
      {
        ...baseOptions,
        upstreamTitle: "Export request failed",
      },
    ),
    {
      description: "Temporary workflow outage.",
      title: "Export request failed",
      tone: "danger",
    },
  );
});

test("shared error feedback preserves safe fallback messages for non-api errors", () => {
  assert.equal(
    toUserSafeErrorMessage(new Error("Network interrupted"), "Fallback message"),
    "Network interrupted",
  );
  assert.equal(toUserSafeErrorMessage(null, "Fallback message"), "Fallback message");

  assert.deepEqual(describeCommonApiError(new Error("Boom"), baseOptions), {
    description: "Boom",
    title: "Export request failed",
    tone: "danger",
  });
});
