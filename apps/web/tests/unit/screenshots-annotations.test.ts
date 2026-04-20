import assert from "node:assert/strict";
import test from "node:test";

import {
  buildAnnotationOperations,
  parseAnnotationPoints,
} from "../../src/features/screenshots/annotations";

test("annotation helpers parse supported draft shapes and normalize operation ordering", () => {
  const operations = buildAnnotationOperations([
    {
      color: "#111111",
      id: "pencil-1",
      op_type: "pencil",
      points: "30,40\n10,20",
      width: "3",
    },
    {
      color: "#ff0000",
      id: "arrow-1",
      op_type: "arrow",
      width: "4",
      x1: "12",
      x2: "120",
      y1: "24",
      y2: "96",
    },
  ]);

  assert.deepEqual(operations, [
    {
      geometry: {
        points: [
          { x: 30, y: 40 },
          { x: 10, y: 20 },
        ],
      },
      op_type: "pencil",
      style: {
        color: "#111111",
        width: 3,
      },
    },
    {
      geometry: {
        x1: 12,
        x2: 120,
        y1: 24,
        y2: 96,
      },
      op_type: "arrow",
      style: {
        color: "#ff0000",
        width: 4,
      },
    },
  ]);
});

test("annotation helpers reject incomplete drafts and malformed point lists", () => {
  assert.equal(parseAnnotationPoints("10,10"), null);
  assert.equal(parseAnnotationPoints("10,10\n20"), null);

  assert.equal(
    buildAnnotationOperations([
      {
        color: "#ffd54a",
        id: "marker-1",
        op_type: "marker",
        opacity: "",
        points: "10,10\n20,20",
      },
    ]),
    null,
  );

  assert.equal(
    buildAnnotationOperations([
      {
        color: "#111111",
        id: "pencil-1",
        op_type: "pencil",
        points: "10,ten\n20,20",
        width: "3",
      },
    ]),
    null,
  );
});
