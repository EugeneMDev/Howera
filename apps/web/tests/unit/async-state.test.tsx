import assert from "node:assert/strict";
import test from "node:test";

import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { EmptyState, ErrorState, LoadingState } from "../../src/shared/ui/async-state";

test("loading state renders a title and description", () => {
  const html = renderToStaticMarkup(
    <LoadingState
      description="Loads project data."
      title="Loading state"
    />,
  );

  assert.match(html, /Loading state/);
  assert.match(html, /Loads project data\./);
});

test("empty and error states render action affordances", () => {
  const emptyHtml = renderToStaticMarkup(
    <EmptyState
      actionHint="Create a first item"
      actionLabel="Create"
      description="Nothing exists yet."
      title="Empty state"
    />,
  );
  const errorHtml = renderToStaticMarkup(
    <ErrorState
      actionHint="Retry the request"
      actionLabel="Retry"
      description="Something failed."
      title="Error state"
    />,
  );

  assert.match(emptyHtml, /Create/);
  assert.match(emptyHtml, /Nothing exists yet\./);
  assert.match(errorHtml, /Retry/);
  assert.match(errorHtml, /Something failed\./);
});
