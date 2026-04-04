export const workspaceNavigation = [
  {
    href: "/projects",
    label: "Projects",
    description: "Create and scope owned workspaces.",
  },
  {
    href: "/jobs",
    label: "Jobs",
    description: "Track upload, run, and lifecycle state.",
  },
  {
    href: "/instructions",
    label: "Instructions",
    description: "Edit draft output with visible validation context.",
  },
] as const;

export const workspaceSignals = [
  {
    label: "Async contract",
    value: "Shared polling and retry language will live here.",
  },
  {
    label: "Security posture",
    value: "No secrets, signed URLs, or raw transcripts are persisted client-side.",
  },
  {
    label: "Accessibility",
    value: "Keyboard-first controls, visible focus, explicit status labels.",
  },
] as const;

export const workspaceChecklist = [
  "Navigation rail",
  "Main workspace region",
  "Operational context panel",
  "Tokenized color and type system",
  "Reusable base primitives",
] as const;

export function isActiveWorkspacePath(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
