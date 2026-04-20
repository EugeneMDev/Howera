import assert from "node:assert/strict";
import test from "node:test";

import {
  filterRecentJobRecords,
  parseRecentJobRecords,
  readRecentJobRecords,
  rememberRecentJobRecord,
  writeRecentJobRecords,
  type RecentJobRecord,
} from "../../src/features/jobs/recent-jobs-session";

function createMemoryStorage() {
  const state = new Map<string, string>();

  return {
    getItem(key: string) {
      return state.get(key) ?? null;
    },
    removeItem(key: string) {
      state.delete(key);
    },
    setItem(key: string, value: string) {
      state.set(key, value);
    },
  };
}

test("recent-jobs parser ignores invalid payloads", () => {
  assert.deepEqual(parseRecentJobRecords(null), []);
  assert.deepEqual(parseRecentJobRecords("not-json"), []);
  assert.deepEqual(parseRecentJobRecords(JSON.stringify({ foo: "bar" })), []);
});

test("recent-jobs registry deduplicates and keeps newest entry first", () => {
  const firstRecord: RecentJobRecord = {
    jobId: "job-1",
    projectId: "project-a",
    touchedAt: "2026-03-24T10:00:00Z",
  };
  const secondRecord: RecentJobRecord = {
    jobId: "job-2",
    projectId: "project-b",
    touchedAt: "2026-03-24T11:00:00Z",
  };
  const updatedFirstRecord: RecentJobRecord = {
    jobId: "job-1",
    projectId: "project-a",
    touchedAt: "2026-03-24T12:00:00Z",
  };

  const records = rememberRecentJobRecord(
    rememberRecentJobRecord([firstRecord], secondRecord),
    updatedFirstRecord,
  );

  assert.deepEqual(records, [updatedFirstRecord, secondRecord]);
  assert.deepEqual(filterRecentJobRecords(records, "project-a"), [updatedFirstRecord]);
});

test("recent-jobs storage round-trips records", () => {
  const storage = createMemoryStorage();
  const records: RecentJobRecord[] = [
    {
      jobId: "job-1",
      projectId: "project-a",
      touchedAt: "2026-03-24T10:00:00Z",
    },
  ];

  writeRecentJobRecords(storage, records);
  assert.deepEqual(readRecentJobRecords(storage), records);

  writeRecentJobRecords(storage, []);
  assert.deepEqual(readRecentJobRecords(storage), []);
});
