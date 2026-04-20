export function triggerImmediateDownload(url: string): void {
  if (!url) {
    throw new Error("A signed download URL is required.");
  }

  if (typeof document === "undefined" || !document.body) {
    throw new Error("Browser download handling is unavailable in this environment.");
  }

  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.rel = "noreferrer";
  anchor.referrerPolicy = "no-referrer";
  anchor.style.display = "none";

  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
}
