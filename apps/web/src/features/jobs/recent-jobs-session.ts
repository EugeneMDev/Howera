export interface RecentJobRecord {
  jobId: string;
  projectId: string;
  touchedAt: string;
}

interface StorageLike {
  getItem(key: string): string | null;
  removeItem(key: string): void;
  setItem(key: string, value: string): void;
}

const RECENT_JOBS_STORAGE_KEY = "howera.recent-jobs";
const MAX_RECENT_JOBS = 24;

function isRecentJobRecord(value: unknown): value is RecentJobRecord {
  if (typeof value !== "object" || value === null) {
    return false;
  }

  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.jobId === "string" &&
    typeof candidate.projectId === "string" &&
    typeof candidate.touchedAt === "string"
  );
}

export function parseRecentJobRecords(rawValue: string | null): RecentJobRecord[] {
  if (!rawValue) {
    return [];
  }

  try {
    const parsed = JSON.parse(rawValue) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter(isRecentJobRecord).slice(0, MAX_RECENT_JOBS);
  } catch {
    return [];
  }
}

export function readRecentJobRecords(storage: StorageLike | null): RecentJobRecord[] {
  if (!storage) {
    return [];
  }

  return parseRecentJobRecords(storage.getItem(RECENT_JOBS_STORAGE_KEY));
}

export function filterRecentJobRecords(
  records: RecentJobRecord[],
  projectId?: string,
): RecentJobRecord[] {
  if (!projectId) {
    return records;
  }

  return records.filter((record) => record.projectId === projectId);
}

export function rememberRecentJobRecord(
  records: RecentJobRecord[],
  nextRecord: RecentJobRecord,
): RecentJobRecord[] {
  return [nextRecord, ...records.filter((record) => record.jobId !== nextRecord.jobId)].slice(
    0,
    MAX_RECENT_JOBS,
  );
}

export function writeRecentJobRecords(
  storage: StorageLike | null,
  records: RecentJobRecord[],
): void {
  if (!storage) {
    return;
  }

  if (records.length === 0) {
    storage.removeItem(RECENT_JOBS_STORAGE_KEY);
    return;
  }

  storage.setItem(RECENT_JOBS_STORAGE_KEY, JSON.stringify(records));
}
