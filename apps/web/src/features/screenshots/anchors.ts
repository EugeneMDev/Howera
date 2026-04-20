import { describeCommonApiError } from "@/shared/api/error-feedback";

import type {
  AnchorAddress,
  AnchorResolution,
  AnchorResolutionState,
  ScreenshotAnchor,
  ScreenshotAsset,
} from "@/features/screenshots/api";

export interface AnchorInspectorFeedback {
  description: string;
  title: string;
  tone: "danger" | "info" | "success" | "warning";
}

export interface AnchorAssetPreview {
  active_asset_id: string | null;
  anchor_id: string;
  deleted_asset_id?: string | null;
}

export function reconcileSelectedAnchorId(
  currentSelectedAnchorId: string | null,
  anchors: ScreenshotAnchor[],
): string | null {
  if (currentSelectedAnchorId && anchors.some((anchor) => anchor.id === currentSelectedAnchorId)) {
    return currentSelectedAnchorId;
  }

  return anchors[0]?.id ?? null;
}

export function findActiveAnchorAsset(anchor: ScreenshotAnchor | null | undefined): ScreenshotAsset | null {
  if (!anchor?.active_asset_id || !anchor.assets?.length) {
    return null;
  }

  return anchor.assets.find((asset) => asset.id === anchor.active_asset_id) ?? null;
}

export function applyAnchorAssetPreview(
  anchor: ScreenshotAnchor | null | undefined,
  preview: AnchorAssetPreview | null | undefined,
): ScreenshotAnchor | null {
  if (!anchor) {
    return null;
  }

  if (!preview || preview.anchor_id !== anchor.id) {
    return anchor;
  }

  return {
    ...anchor,
    active_asset_id: preview.active_asset_id,
    assets:
      anchor.assets?.map((asset) =>
        asset.id === preview.deleted_asset_id ? { ...asset, is_deleted: true } : asset,
      ) ?? anchor.assets,
  };
}

export function formatAnchorAddressing(addressing: AnchorAddress): string {
  if (addressing.address_type === "block_id") {
    return addressing.block_id ? `Block ID: ${addressing.block_id}` : "Block ID";
  }

  if (addressing.char_range) {
    return `Char range: ${addressing.char_range.start_offset}-${addressing.char_range.end_offset}`;
  }

  return "Char range";
}

export function getAnchorResolutionTone(
  state: AnchorResolutionState | null | undefined,
): "info" | "success" | "warning" {
  if (state === "unresolved") {
    return "warning";
  }

  if (state === "retain") {
    return "success";
  }

  return "info";
}

export function describeAnchorResolution(
  resolution: AnchorResolution | null | undefined,
): AnchorInspectorFeedback | null {
  if (!resolution) {
    return null;
  }

  if (resolution.resolution_state === "retain") {
    return {
      description: `Anchor visibility is preserved from source version ${resolution.source_instruction_version_id} into target version ${resolution.target_instruction_version_id}.`,
      title: "Anchor retained in current view",
      tone: "success",
    };
  }

  if (resolution.resolution_state === "remap") {
    return {
      description: `Anchor visibility was remapped from source version ${resolution.source_instruction_version_id} into target version ${resolution.target_instruction_version_id}. Review the trace details, but no intervention is currently required.`,
      title: "Anchor remapped for current view",
      tone: "info",
    };
  }

  return {
    description: `Anchor visibility could not be resolved from source version ${resolution.source_instruction_version_id} into target version ${resolution.target_instruction_version_id}. User action is required before relying on this reference.`,
    title: "Anchor requires attention",
    tone: "warning",
  };
}

export function describeAnchorQueryError(error: unknown): AnchorInspectorFeedback {
  return describeCommonApiError(error, {
    actionLabel: "Anchor load",
    fallbackDescription: "Anchor data could not be loaded.",
    failedTitle: "Anchor load failed",
    invalidRequestTitle: "Anchor load rejected",
    noLeakDescription:
      "The requested anchor context is either missing or no longer accessible to this editor. Howera intentionally uses the same response for both cases.",
    noLeakTitle: "Anchor context unavailable",
    rejectedTitle: "Anchor load rejected",
  });
}
