export interface TextSelectionSnapshot {
  direction: "backward" | "forward" | "none" | null;
  end: number;
  start: number;
}

export interface TextSelectionTarget {
  selectionDirection?: "backward" | "forward" | "none" | null;
  selectionEnd: number | null;
  selectionStart: number | null;
  setSelectionRange: (
    start: number,
    end: number,
    direction?: "backward" | "forward" | "none",
  ) => void;
}

export function captureTextSelection(target: TextSelectionTarget | null): TextSelectionSnapshot | null {
  if (target === null || target.selectionStart === null || target.selectionEnd === null) {
    return null;
  }

  return {
    direction: target.selectionDirection ?? null,
    end: target.selectionEnd,
    start: target.selectionStart,
  };
}

export function restoreTextSelection(
  target: TextSelectionTarget | null,
  snapshot: TextSelectionSnapshot | null,
): boolean {
  if (target === null || snapshot === null) {
    return false;
  }

  target.setSelectionRange(snapshot.start, snapshot.end, snapshot.direction ?? undefined);
  return true;
}
