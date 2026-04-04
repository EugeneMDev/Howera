import assert from "node:assert/strict";
import test from "node:test";

import { triggerImmediateDownload } from "../../src/shared/lib/download";

test("triggerImmediateDownload uses the signed URL immediately without touching browser storage", (t) => {
  const originalDocument = Object.getOwnPropertyDescriptor(globalThis, "document");
  const originalLocalStorage = Object.getOwnPropertyDescriptor(globalThis, "localStorage");
  const originalSessionStorage = Object.getOwnPropertyDescriptor(globalThis, "sessionStorage");

  t.after(() => {
    if (originalDocument) {
      Object.defineProperty(globalThis, "document", originalDocument);
    } else {
      delete (globalThis as { document?: Document }).document;
    }

    if (originalLocalStorage) {
      Object.defineProperty(globalThis, "localStorage", originalLocalStorage);
    } else {
      delete (globalThis as { localStorage?: Storage }).localStorage;
    }

    if (originalSessionStorage) {
      Object.defineProperty(globalThis, "sessionStorage", originalSessionStorage);
    } else {
      delete (globalThis as { sessionStorage?: Storage }).sessionStorage;
    }
  });

  let localStorageTouches = 0;
  let sessionStorageTouches = 0;
  let clickCount = 0;
  const appended: unknown[] = [];
  const removed: unknown[] = [];

  const anchor = {
    click() {
      clickCount += 1;
    },
    href: "",
    referrerPolicy: "",
    rel: "",
    style: {
      display: "",
    },
  };

  const body = {
    appendChild(node: unknown) {
      appended.push(node);
      return node;
    },
    removeChild(node: unknown) {
      removed.push(node);
      return node;
    },
  };

  Object.defineProperty(globalThis, "localStorage", {
    configurable: true,
    get() {
      localStorageTouches += 1;
      return null;
    },
  });

  Object.defineProperty(globalThis, "sessionStorage", {
    configurable: true,
    get() {
      sessionStorageTouches += 1;
      return null;
    },
  });

  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: {
      body,
      createElement(tagName: string) {
        assert.equal(tagName, "a");
        return anchor;
      },
    } as unknown as Pick<Document, "body" | "createElement">,
  });

  triggerImmediateDownload("https://downloads.howera.local/export-ready-123?sig=abc");

  assert.equal(anchor.href, "https://downloads.howera.local/export-ready-123?sig=abc");
  assert.equal(anchor.rel, "noreferrer");
  assert.equal(anchor.referrerPolicy, "no-referrer");
  assert.equal(anchor.style.display, "none");
  assert.equal(clickCount, 1);
  assert.deepEqual(appended, [anchor]);
  assert.deepEqual(removed, [anchor]);
  assert.equal(localStorageTouches, 0);
  assert.equal(sessionStorageTouches, 0);
});

test("triggerImmediateDownload rejects missing browser prerequisites", () => {
  assert.throws(() => triggerImmediateDownload(""), /signed download URL is required/i);

  const originalDocument = Object.getOwnPropertyDescriptor(globalThis, "document");

  try {
    delete (globalThis as { document?: Document }).document;
    assert.throws(
      () => triggerImmediateDownload("https://downloads.howera.local/export-ready-123?sig=abc"),
      /Browser download handling is unavailable in this environment\./,
    );
  } finally {
    if (originalDocument) {
      Object.defineProperty(globalThis, "document", originalDocument);
    }
  }
});
