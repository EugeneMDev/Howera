"use client";

import { useEffect, useState } from "react";

import { useApiClient } from "@/shared/providers/app-providers";
import {
  getScreenshotAnchor,
  listScreenshotAnchors,
  type ScreenshotAnchor,
} from "@/features/screenshots/api";
import {
  describeAnchorQueryError,
  reconcileSelectedAnchorId,
  type AnchorInspectorFeedback,
} from "@/features/screenshots/anchors";

type QueryStatus = "idle" | "loading" | "success" | "error";

export function useInstructionAnchors({
  instructionId,
  refreshToken,
  targetInstructionVersionId,
}: {
  instructionId: string;
  refreshToken?: string | null;
  targetInstructionVersionId: string | null;
}) {
  const apiClient = useApiClient();
  const [anchors, setAnchors] = useState<ScreenshotAnchor[]>([]);
  const [selectedAnchorId, setSelectedAnchorId] = useState<string | null>(null);
  const [selectedAnchor, setSelectedAnchor] = useState<ScreenshotAnchor | null>(null);
  const [listFeedback, setListFeedback] = useState<AnchorInspectorFeedback | null>(null);
  const [detailFeedback, setDetailFeedback] = useState<AnchorInspectorFeedback | null>(null);
  const [listStatus, setListStatus] = useState<QueryStatus>("loading");
  const [detailStatus, setDetailStatus] = useState<QueryStatus>("idle");
  const [refreshRevision, setRefreshRevision] = useState(0);

  useEffect(() => {
    setAnchors([]);
    setSelectedAnchorId(null);
    setSelectedAnchor(null);
    setListFeedback(null);
    setDetailFeedback(null);
    setListStatus("loading");
    setDetailStatus("idle");
  }, [instructionId]);

  useEffect(() => {
    let cancelled = false;

    setListStatus("loading");
    setListFeedback(null);

    void listScreenshotAnchors(apiClient, instructionId, {
      include_deleted_assets: true,
    })
      .then((nextAnchors) => {
        if (cancelled) {
          return;
        }

        setAnchors(nextAnchors);
        setSelectedAnchorId((currentSelectedAnchorId) =>
          reconcileSelectedAnchorId(currentSelectedAnchorId, nextAnchors),
        );
        setListStatus("success");
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }

        setAnchors([]);
        setSelectedAnchorId(null);
        setSelectedAnchor(null);
        setListFeedback(describeAnchorQueryError(error));
        setListStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [apiClient, instructionId, refreshRevision, refreshToken]);

  useEffect(() => {
    if (!selectedAnchorId || !targetInstructionVersionId) {
      setSelectedAnchor(null);
      setDetailFeedback(null);
      setDetailStatus("idle");
      return;
    }

    let cancelled = false;

    setDetailStatus("loading");
    setDetailFeedback(null);

    void getScreenshotAnchor(apiClient, selectedAnchorId, {
      target_instruction_version_id: targetInstructionVersionId,
    })
      .then((anchor) => {
        if (cancelled) {
          return;
        }

        setSelectedAnchor(anchor);
        setDetailStatus("success");
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }

        setSelectedAnchor(null);
        setDetailFeedback(describeAnchorQueryError(error));
        setDetailStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [apiClient, selectedAnchorId, targetInstructionVersionId]);

  const selectedAnchorSummary = anchors.find((anchor) => anchor.id === selectedAnchorId) ?? null;

  return {
    anchors,
    detailFeedback,
    detailStatus,
    hasAnchors: anchors.length > 0,
    listFeedback,
    listStatus,
    refresh() {
      setRefreshRevision((current) => current + 1);
    },
    selectedAnchor,
    selectedAnchorId,
    selectedAnchorSummary,
    setSelectedAnchorId,
    visibilityContextDescription:
      targetInstructionVersionId === null
        ? "Current visibility context will load once the instruction version is available."
        : targetInstructionVersionId === selectedAnchor?.instruction_version_id
        ? `Current view targets source version ${targetInstructionVersionId}.`
        : `Current view projects anchors into instruction version ${targetInstructionVersionId}.`,
    visibilityTargetVersionId: targetInstructionVersionId,
  };
}
