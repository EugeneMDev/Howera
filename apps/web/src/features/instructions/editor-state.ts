import type { Instruction, VersionConflictDetails } from "@/features/instructions/api";

export interface InstructionEditorFeedback {
  description: string;
  title: string;
  tone: "danger" | "info" | "success" | "warning";
}

export interface InstructionEditorState {
  conflict: VersionConflictDetails | null;
  draftMarkdown: string;
  feedback: InstructionEditorFeedback | null;
  instruction: Instruction | null;
  latestInstruction: Instruction | null;
}

export function createInstructionEditorState(): InstructionEditorState {
  return {
    conflict: null,
    draftMarkdown: "",
    feedback: null,
    instruction: null,
    latestInstruction: null,
  };
}

export function isInstructionEditorDirty(state: InstructionEditorState): boolean {
  return state.instruction !== null && state.draftMarkdown !== state.instruction.markdown;
}

export function applyLoadedInstructionSnapshot(
  state: InstructionEditorState,
  instruction: Instruction,
): InstructionEditorState {
  if (
    state.instruction === null ||
    state.instruction.instruction_id !== instruction.instruction_id ||
    !isInstructionEditorDirty(state)
  ) {
    return {
      conflict: null,
      draftMarkdown: instruction.markdown,
      feedback: null,
      instruction,
      latestInstruction: instruction,
    };
  }

  return {
    ...state,
    latestInstruction: instruction,
  };
}

export function updateInstructionDraft(
  state: InstructionEditorState,
  markdown: string,
): InstructionEditorState {
  return {
    ...state,
    draftMarkdown: markdown,
  };
}

export function applyInstructionSaveSuccess(
  state: InstructionEditorState,
  instruction: Instruction,
): InstructionEditorState {
  return {
    ...state,
    conflict: null,
    draftMarkdown: instruction.markdown,
    feedback: {
      description: `Instruction saved as version ${instruction.version} without a full page reload.`,
      title: "Save complete",
      tone: "success",
    },
    instruction,
    latestInstruction: instruction,
  };
}

export function applyInstructionVersionConflict(
  state: InstructionEditorState,
  conflict: VersionConflictDetails,
  latestInstruction: Instruction | null,
): InstructionEditorState {
  return {
    ...state,
    conflict,
    feedback: {
      description: `Your draft still holds the unsaved local content based on version ${conflict.base_version}, while the server is already on version ${conflict.current_version}.`,
      title: "Version conflict",
      tone: "warning",
    },
    latestInstruction: latestInstruction ?? state.latestInstruction,
  };
}

export function reloadInstructionEditorFromLatest(
  state: InstructionEditorState,
): InstructionEditorState {
  if (state.latestInstruction === null) {
    return state;
  }

  return {
    ...state,
    conflict: null,
    draftMarkdown: state.latestInstruction.markdown,
    feedback: {
      description: `The editor now reflects server version ${state.latestInstruction.version}. Previous local draft content was discarded by explicit user action.`,
      title: "Latest version loaded",
      tone: "info",
    },
    instruction: state.latestInstruction,
  };
}

export function adoptLatestInstructionBase(
  state: InstructionEditorState,
): InstructionEditorState {
  if (state.latestInstruction === null) {
    return state;
  }

  return {
    ...state,
    conflict: null,
    feedback: {
      description: `Your local draft was kept, and saves will now use server version ${state.latestInstruction.version} as the new base. Merge server changes into the draft before saving.`,
      title: "Draft kept for manual merge",
      tone: "warning",
    },
    instruction: state.latestInstruction,
  };
}

export function dismissInstructionEditorFeedback(
  state: InstructionEditorState,
): InstructionEditorState {
  return {
    ...state,
    feedback: null,
  };
}
