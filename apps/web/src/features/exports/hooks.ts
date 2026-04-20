"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { useApiClient, useTelemetry } from "@/shared/providers/app-providers";
import {
  createPollingPausedFeedback,
  hasPollingAttemptWindowEnded,
  useBoundedPolling,
} from "@/shared/hooks/use-bounded-polling";
import { triggerImmediateDownload } from "@/shared/lib/download";
import {
  getExport,
  isExportTerminal,
  requestExport,
  type CreateExportRequestInput,
  type ExportRecord,
} from "@/features/exports/api";
import {
  describeExportError,
  getExportDownloadAvailability,
  describeExportRecord,
  type ExportFeedback,
} from "@/features/exports/feedback";

function sortExportRecords(records: ExportRecord[]): ExportRecord[] {
  return [...records].sort((left, right) => {
    const rightTime = Date.parse(right.updated_at || right.created_at);
    const leftTime = Date.parse(left.updated_at || left.created_at);
    return rightTime - leftTime;
  });
}

function mergeExportRecords(records: ExportRecord[], nextRecord: ExportRecord): ExportRecord[] {
  const currentRecord = records.find((record) => record.id === nextRecord.id);
  const mergedRecord: ExportRecord = {
    ...currentRecord,
    ...nextRecord,
    replayed: nextRecord.replayed ?? currentRecord?.replayed ?? false,
  };

  return sortExportRecords([...records.filter((record) => record.id !== nextRecord.id), mergedRecord]);
}

export function useInstructionExports({
  jobId,
  scopeKey,
}: {
  jobId: string;
  scopeKey: string;
}) {
  const apiClient = useApiClient();
  const telemetry = useTelemetry();
  const [records, setRecords] = useState<ExportRecord[]>([]);
  const [feedback, setFeedback] = useState<ExportFeedback | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [lastIdempotencyKey, setLastIdempotencyKey] = useState<string | null>(null);
  const [pendingDownloadExportId, setPendingDownloadExportId] = useState<string | null>(null);
  const reportedTerminalExportsRef = useRef<Set<string>>(new Set());
  const pendingExportIds = records
    .filter((record) => !isExportTerminal(record.status))
    .map((record) => record.id)
    .sort();

  const reportTerminalRecord = useCallback(
    (record: ExportRecord) => {
      const telemetryKey = `${record.id}:${record.status}`;
      if (!reportedTerminalExportsRef.current.has(telemetryKey)) {
        reportedTerminalExportsRef.current.add(telemetryKey);
        telemetry.track({
          attributes: {
            exportId: record.id,
            format: record.format,
            jobId,
            result: record.status === "SUCCEEDED" ? "succeeded" : "failed",
            status: record.status,
          },
          name: record.status === "SUCCEEDED" ? "export.succeeded" : "export.failed",
        });
      }

      setFeedback(describeExportRecord(record));
    },
    [jobId, telemetry],
  );

  const { polling, startPolling, stopPolling } = useBoundedPolling({
    onPoll: () => {
      if (pendingExportIds.length === 0) {
        return;
      }

      void Promise.all(pendingExportIds.map((exportId) => getExport(apiClient, exportId)))
        .then((nextRecords) => {
          let mergedRecords: ExportRecord[] = [];

          setRecords((current) => {
            mergedRecords = nextRecords.reduce(
              (accumulator, nextRecord) => mergeExportRecords(accumulator, nextRecord),
              current,
            );
            return mergedRecords;
          });

          const hasPending = mergedRecords.some((record) => !isExportTerminal(record.status));
          if (!hasPending) {
            stopPolling();
            const latestRecord = mergedRecords[0];
            if (latestRecord) {
              reportTerminalRecord(latestRecord);
            }
          }
        })
        .catch((error) => {
          setFeedback(describeExportError(error, "refresh"));
          stopPolling();
        });
    },
  });

  const syncPolling = useCallback(
    (nextRecords: ExportRecord[]) => {
      const nextPendingIds = nextRecords
        .filter((record) => !isExportTerminal(record.status))
        .map((record) => record.id)
        .sort();

      if (nextPendingIds.length === 0) {
        stopPolling();
        return;
      }

      const watchValue = nextPendingIds.join(",");
      if (polling.active && polling.watchValue === watchValue) {
        return;
      }

      startPolling({
        intervalMs: 2500,
        maxAttempts: 10,
        reason: "export-status",
        watchValue,
      });
    },
    [polling.active, polling.watchValue, startPolling, stopPolling],
  );

  useEffect(() => {
    if (hasPollingAttemptWindowEnded(polling) && pendingExportIds.length > 0) {
      setFeedback(
        createPollingPausedFeedback(
          "Refresh export status manually or request the export again to continue tracking progress.",
        ),
      );
    }
  }, [pendingExportIds.length, polling]);

  useEffect(() => {
    setRecords([]);
    setFeedback(null);
    setIsSubmitting(false);
    setLastIdempotencyKey(null);
    setPendingDownloadExportId(null);
    reportedTerminalExportsRef.current.clear();
    stopPolling();
  }, [scopeKey, stopPolling]);

  const loadExportRecord = useCallback(
    async (exportId: string): Promise<ExportRecord> => {
      const nextRecord = await getExport(apiClient, exportId);
      let mergedRecords: ExportRecord[] = [];

      setRecords((current) => {
        mergedRecords = mergeExportRecords(current, nextRecord);
        return mergedRecords;
      });

      if (isExportTerminal(nextRecord.status)) {
        reportTerminalRecord(nextRecord);
      }

      syncPolling(mergedRecords);
      return nextRecord;
    },
    [apiClient, reportTerminalRecord, syncPolling],
  );

  return {
    dismissFeedback() {
      setFeedback(null);
    },
    feedback,
    isSubmitting,
    lastIdempotencyKey,
    pendingDownloadExportId,
    polling,
    records,
    async downloadExport(exportId: string): Promise<boolean> {
      try {
        setPendingDownloadExportId(exportId);

        const nextRecord = await loadExportRecord(exportId);
        const availability = getExportDownloadAvailability(nextRecord);
        if (!availability.canDownload || !nextRecord.download_url) {
          setFeedback({
            description: availability.description,
            title: availability.title,
            tone: availability.tone,
          });
          return false;
        }

        triggerImmediateDownload(nextRecord.download_url);
        telemetry.track({
          attributes: {
            exportId: nextRecord.id,
            format: nextRecord.format,
            jobId,
            result: "download-started",
            status: nextRecord.status,
          },
          name: "export.download.started",
        });
        setFeedback({
          description:
            "The signed URL was used immediately from in-memory state and was not persisted in browser storage.",
          title: "Download started",
          tone: "success",
        });
        return true;
      } catch (error) {
        telemetry.track({
          attributes: {
            exportId,
            jobId,
            result: "failed",
          },
          error,
          name: "export.download.failed",
        });
        setFeedback(describeExportError(error, "download"));
        return false;
      } finally {
        setPendingDownloadExportId(null);
      }
    },
    async refreshExport(exportId: string): Promise<void> {
      try {
        await loadExportRecord(exportId);
      } catch (error) {
        setFeedback(describeExportError(error, "refresh"));
      }
    },
    async submit(input: CreateExportRequestInput): Promise<boolean> {
      try {
        setIsSubmitting(true);
        setFeedback(null);
        setLastIdempotencyKey(input.idempotency_key ?? null);

        const nextRecord = await requestExport(apiClient, jobId, input);
        let mergedRecords: ExportRecord[] = [];

        setRecords((current) => {
          mergedRecords = mergeExportRecords(current, nextRecord);
          return mergedRecords;
        });

        telemetry.track({
          attributes: {
            exportId: nextRecord.id,
            format: nextRecord.format,
            jobId,
            replayed: nextRecord.replayed ?? false,
            result: nextRecord.replayed ? "replayed" : "requested",
            status: nextRecord.status,
          },
          name: nextRecord.replayed ? "export.replayed" : "export.requested",
        });
        if (isExportTerminal(nextRecord.status)) {
          reportTerminalRecord(nextRecord);
        } else {
          setFeedback(describeExportRecord(nextRecord));
        }
        syncPolling(mergedRecords);
        return true;
      } catch (error) {
        telemetry.track({
          attributes: {
            format: input.format,
            jobId,
            result: "failed",
          },
          error,
          name: "export.request-failed",
        });
        setFeedback(describeExportError(error, "request"));
        return false;
      } finally {
        setIsSubmitting(false);
      }
    },
    stopPolling,
  };
}
