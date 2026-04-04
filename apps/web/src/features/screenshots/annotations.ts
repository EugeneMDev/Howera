import type {
  AnnotationOperation,
  AnnotationOperationType,
} from "@/features/screenshots/api";

export interface AnnotationPoint {
  x: number;
  y: number;
}

export interface BlurAnnotationDraft {
  height: string;
  id: string;
  op_type: "blur";
  radius: string;
  width: string;
  x: string;
  y: string;
}

export interface ArrowAnnotationDraft {
  color: string;
  id: string;
  op_type: "arrow";
  width: string;
  x1: string;
  x2: string;
  y1: string;
  y2: string;
}

export interface MarkerAnnotationDraft {
  color: string;
  id: string;
  op_type: "marker";
  opacity: string;
  points: string;
}

export interface PencilAnnotationDraft {
  color: string;
  id: string;
  op_type: "pencil";
  points: string;
  width: string;
}

export type AnnotationDraft =
  | ArrowAnnotationDraft
  | BlurAnnotationDraft
  | MarkerAnnotationDraft
  | PencilAnnotationDraft;

function createAnnotationDraftId(): string {
  return `annotation-${Date.now().toString(36)}-${Math.random().toString(16).slice(2, 10)}`;
}

export function createAnnotationDraft(
  opType: AnnotationOperationType = "arrow",
  id = createAnnotationDraftId(),
): AnnotationDraft {
  if (opType === "blur") {
    return {
      height: "",
      id,
      op_type: "blur",
      radius: "8",
      width: "",
      x: "",
      y: "",
    };
  }

  if (opType === "marker") {
    return {
      color: "#ffd54a",
      id,
      op_type: "marker",
      opacity: "0.4",
      points: "10,10\n40,28",
    };
  }

  if (opType === "pencil") {
    return {
      color: "#111111",
      id,
      op_type: "pencil",
      points: "10,10\n40,28",
      width: "3",
    };
  }

  return {
    color: "#ff0000",
    id,
    op_type: "arrow",
    width: "4",
    x1: "",
    x2: "",
    y1: "",
    y2: "",
  };
}

function getAnnotationDraftColor(draft: AnnotationDraft): string | null {
  return "color" in draft ? draft.color : null;
}

function getAnnotationDraftPoints(draft: AnnotationDraft): string | null {
  return "points" in draft ? draft.points : null;
}

function getAnnotationDraftWidth(draft: AnnotationDraft): string | null {
  if (draft.op_type === "arrow" || draft.op_type === "blur" || draft.op_type === "pencil") {
    return draft.width;
  }

  return null;
}

export function changeAnnotationDraftType(
  draft: AnnotationDraft,
  nextType: AnnotationOperationType,
): AnnotationDraft {
  if (draft.op_type === nextType) {
    return draft;
  }

  if (nextType === "arrow") {
    const nextDraft = createAnnotationDraft("arrow", draft.id) as ArrowAnnotationDraft;
    return {
      color: getAnnotationDraftColor(draft) ?? nextDraft.color,
      id: draft.id,
      op_type: "arrow",
      width: getAnnotationDraftWidth(draft) ?? nextDraft.width,
      x1: nextDraft.x1,
      x2: nextDraft.x2,
      y1: nextDraft.y1,
      y2: nextDraft.y2,
    };
  }

  if (nextType === "blur") {
    return createAnnotationDraft("blur", draft.id);
  }

  if (nextType === "marker") {
    const nextDraft = createAnnotationDraft("marker", draft.id) as MarkerAnnotationDraft;
    return {
      color: getAnnotationDraftColor(draft) ?? nextDraft.color,
      id: draft.id,
      op_type: "marker",
      opacity: nextDraft.opacity,
      points: getAnnotationDraftPoints(draft) ?? nextDraft.points,
    };
  }

  const nextDraft = createAnnotationDraft("pencil", draft.id) as PencilAnnotationDraft;
  return {
    color: getAnnotationDraftColor(draft) ?? nextDraft.color,
    id: draft.id,
    op_type: "pencil",
    points: getAnnotationDraftPoints(draft) ?? nextDraft.points,
    width: getAnnotationDraftWidth(draft) ?? nextDraft.width,
  };
}

function parseFiniteNumber(value: string): number | null {
  const normalized = value.trim();
  if (!normalized) {
    return null;
  }

  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

export function parseAnnotationPoints(pointsText: string): AnnotationPoint[] | null {
  const lines = pointsText
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  if (lines.length < 2) {
    return null;
  }

  const points: AnnotationPoint[] = [];

  for (const line of lines) {
    const [xValue, yValue, ...rest] = line.split(",").map((part) => part.trim());
    if (rest.length > 0) {
      return null;
    }

    const x = parseFiniteNumber(xValue ?? "");
    const y = parseFiniteNumber(yValue ?? "");
    if (x === null || y === null) {
      return null;
    }

    points.push({ x, y });
  }

  return points;
}

export function toAnnotationOperation(draft: AnnotationDraft): AnnotationOperation | null {
  if (draft.op_type === "blur") {
    const x = parseFiniteNumber(draft.x);
    const y = parseFiniteNumber(draft.y);
    const width = parseFiniteNumber(draft.width);
    const height = parseFiniteNumber(draft.height);
    const radius = parseFiniteNumber(draft.radius);

    if (x === null || y === null || width === null || height === null || radius === null) {
      return null;
    }

    return {
      geometry: { height, width, x, y },
      op_type: "blur",
      style: { radius },
    };
  }

  if (draft.op_type === "arrow") {
    const x1 = parseFiniteNumber(draft.x1);
    const y1 = parseFiniteNumber(draft.y1);
    const x2 = parseFiniteNumber(draft.x2);
    const y2 = parseFiniteNumber(draft.y2);
    const width = parseFiniteNumber(draft.width);
    const color = draft.color.trim();

    if (x1 === null || y1 === null || x2 === null || y2 === null || width === null || !color) {
      return null;
    }

    return {
      geometry: { x1, x2, y1, y2 },
      op_type: "arrow",
      style: { color, width },
    };
  }

  if (draft.op_type === "marker") {
    const points = parseAnnotationPoints(draft.points);
    const opacity = parseFiniteNumber(draft.opacity);
    const color = draft.color.trim();

    if (points === null || opacity === null || !color) {
      return null;
    }

    return {
      geometry: { points },
      op_type: "marker",
      style: { color, opacity },
    };
  }

  const points = parseAnnotationPoints(draft.points);
  const width = parseFiniteNumber(draft.width);
  const color = draft.color.trim();

  if (points === null || width === null || !color) {
    return null;
  }

  return {
    geometry: { points },
    op_type: "pencil",
    style: { color, width },
  };
}

export function buildAnnotationOperations(drafts: AnnotationDraft[]): AnnotationOperation[] | null {
  if (drafts.length === 0) {
    return null;
  }

  const operations: AnnotationOperation[] = [];
  for (const draft of drafts) {
    const operation = toAnnotationOperation(draft);
    if (operation === null) {
      return null;
    }

    operations.push(operation);
  }

  return normalizeAnnotationOperations(operations);
}

function normalizeAnnotationValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => normalizeAnnotationValue(item));
  }

  if (typeof value === "object" && value !== null) {
    const record = value as Record<string, unknown>;
    const normalized = Object.keys(record)
      .sort()
      .reduce<Record<string, unknown>>((accumulator, key) => {
        accumulator[key] = normalizeAnnotationValue(record[key]);
        return accumulator;
      }, {});
    return normalized;
  }

  return value;
}

function stableSerialize(value: unknown): string {
  return JSON.stringify(normalizeAnnotationValue(value));
}

export function normalizeAnnotationOperations(
  operations: AnnotationOperation[],
): AnnotationOperation[] {
  return operations
    .map((operation) => ({
      geometry: normalizeAnnotationValue(operation.geometry) as Record<string, unknown>,
      op_type: operation.op_type,
      style: normalizeAnnotationValue(operation.style) as Record<string, unknown>,
    }))
    .sort((left, right) => stableSerialize(left).localeCompare(stableSerialize(right)));
}

export function summarizeAnnotationDraft(draft: AnnotationDraft): string {
  if (draft.op_type === "blur") {
    return "Blur region";
  }

  if (draft.op_type === "arrow") {
    return "Arrow callout";
  }

  if (draft.op_type === "marker") {
    return "Marker highlight";
  }

  return "Pencil stroke";
}
