import assert from "node:assert/strict";
import test from "node:test";

import {
  readProcessPublicRuntimeConfig,
  readPublicRuntimeConfig,
} from "../../src/shared/config/runtime";

test("runtime config reports missing required keys", () => {
  const config = readPublicRuntimeConfig({});

  assert.equal(config.isConfigured, false);
  assert.deepEqual(config.missingKeys, [
    "NEXT_PUBLIC_API_BASE_URL",
    "NEXT_PUBLIC_FIREBASE_API_KEY",
    "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN",
    "NEXT_PUBLIC_FIREBASE_PROJECT_ID",
    "NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET",
    "NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID",
    "NEXT_PUBLIC_FIREBASE_APP_ID",
  ]);
});

test("runtime config normalizes required public values", () => {
  const config = readPublicRuntimeConfig({
    NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000/api/v1",
    NEXT_PUBLIC_APP_ENV: "production",
    NEXT_PUBLIC_FIREBASE_API_KEY: "api-key",
    NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: "example.firebaseapp.com",
    NEXT_PUBLIC_FIREBASE_PROJECT_ID: "howera-b930c",
    NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET: "howera-b930c.firebasestorage.app",
    NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID: "1054512329294",
    NEXT_PUBLIC_FIREBASE_APP_ID: "1:1054512329294:web:test",
    NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID: "G-TEST123",
    NEXT_PUBLIC_HOSTING_TARGET: "firebase-preview",
    NEXT_PUBLIC_TELEMETRY_ENABLED: "yes",
  });

  assert.equal(config.isConfigured, true);
  assert.equal(config.apiBaseUrl, "http://localhost:8000/api/v1");
  assert.equal(config.appEnv, "production");
  assert.equal(config.firebase.projectId, "howera-b930c");
  assert.equal(config.firebase.measurementId, "G-TEST123");
  assert.equal(config.hostingTarget, "firebase-preview");
  assert.equal(config.telemetryEnabled, true);
  assert.deepEqual(config.missingKeys, []);
});

test("runtime config only requires api base url in mock auth mode", () => {
  const config = readPublicRuntimeConfig({
    NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000/api/v1",
    NEXT_PUBLIC_AUTH_PROVIDER: "mock",
  });

  assert.equal(config.authProvider, "mock");
  assert.equal(config.isConfigured, true);
  assert.equal(config.mockUserId, "local-editor");
  assert.deepEqual(config.missingKeys, []);
});

test("runtime config applies safe defaults for optional public values", () => {
  const config = readPublicRuntimeConfig({
    NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000/api/v1",
    NEXT_PUBLIC_AUTH_PROVIDER: "mock",
  });

  assert.equal(config.appEnv, "development");
  assert.equal(config.hostingTarget, "firebase-hosting");
  assert.equal(config.telemetryEnabled, false);
});

test("runtime config reads NEXT_PUBLIC values from process.env via static keys", () => {
  const previousValues = {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_APP_ENV: process.env.NEXT_PUBLIC_APP_ENV,
    NEXT_PUBLIC_AUTH_PROVIDER: process.env.NEXT_PUBLIC_AUTH_PROVIDER,
    NEXT_PUBLIC_FIREBASE_API_KEY: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
    NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
    NEXT_PUBLIC_FIREBASE_PROJECT_ID: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
    NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
    NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
    NEXT_PUBLIC_FIREBASE_APP_ID: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
    NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID: process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID,
    NEXT_PUBLIC_HOSTING_TARGET: process.env.NEXT_PUBLIC_HOSTING_TARGET,
    NEXT_PUBLIC_MOCK_USER_ID: process.env.NEXT_PUBLIC_MOCK_USER_ID,
    NEXT_PUBLIC_TELEMETRY_ENABLED: process.env.NEXT_PUBLIC_TELEMETRY_ENABLED,
  };

  process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000/api/v1";
  process.env.NEXT_PUBLIC_APP_ENV = "staging";
  process.env.NEXT_PUBLIC_AUTH_PROVIDER = "firebase";
  process.env.NEXT_PUBLIC_FIREBASE_API_KEY = "api-key";
  process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN = "example.firebaseapp.com";
  process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID = "howera-b930c";
  process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET = "howera-b930c.firebasestorage.app";
  process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID = "1054512329294";
  process.env.NEXT_PUBLIC_FIREBASE_APP_ID = "1:1054512329294:web:test";
  process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID = "G-TEST123";
  process.env.NEXT_PUBLIC_HOSTING_TARGET = "firebase-preview";
  process.env.NEXT_PUBLIC_MOCK_USER_ID = "dev-editor";
  process.env.NEXT_PUBLIC_TELEMETRY_ENABLED = "true";

  try {
    const config = readProcessPublicRuntimeConfig();

    assert.equal(config.isConfigured, true);
    assert.equal(config.apiBaseUrl, "http://localhost:8000/api/v1");
    assert.equal(config.appEnv, "staging");
    assert.equal(config.authProvider, "firebase");
    assert.equal(config.firebase.authDomain, "example.firebaseapp.com");
    assert.equal(config.firebase.measurementId, "G-TEST123");
    assert.equal(config.hostingTarget, "firebase-preview");
    assert.equal(config.mockUserId, "dev-editor");
    assert.equal(config.telemetryEnabled, true);
    assert.deepEqual(config.missingKeys, []);
  } finally {
    for (const [key, value] of Object.entries(previousValues)) {
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  }
});
