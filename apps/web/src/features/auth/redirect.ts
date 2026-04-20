const DEFAULT_NEXT_PATH = "/projects";

export function normalizeNextPath(value: string | null | undefined): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/sign-in")) {
    return DEFAULT_NEXT_PATH;
  }

  return value;
}

export function buildSignInPath(nextPath: string): string {
  return `/sign-in?next=${encodeURIComponent(normalizeNextPath(nextPath))}`;
}
