export interface PublicFirebaseConfig {
  apiKey: string;
  authDomain: string;
  projectId: string;
  storageBucket: string;
  messagingSenderId: string;
  appId: string;
  measurementId: string | null;
}

export type PublicAuthProvider = "firebase" | "mock";

export interface PublicRuntimeConfig {
  apiBaseUrl: string;
  appEnv: string;
  authProvider: PublicAuthProvider;
  firebase: PublicFirebaseConfig;
  hostingTarget: string;
  isConfigured: boolean;
  missingKeys: string[];
  mockUserId: string;
  telemetryEnabled: boolean;
}

type EnvSource = Record<string, string | undefined>;

const SHARED_REQUIRED_RUNTIME_KEYS = ["NEXT_PUBLIC_API_BASE_URL"] as const;

const REQUIRED_FIREBASE_RUNTIME_KEYS = [
  "NEXT_PUBLIC_API_BASE_URL",
  "NEXT_PUBLIC_FIREBASE_API_KEY",
  "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN",
  "NEXT_PUBLIC_FIREBASE_PROJECT_ID",
  "NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET",
  "NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID",
  "NEXT_PUBLIC_FIREBASE_APP_ID",
] as const;

function readEnvValue(source: EnvSource, key: string): string {
  return (source[key] ?? "").trim();
}

function readAuthProvider(source: EnvSource): PublicAuthProvider {
  return readEnvValue(source, "NEXT_PUBLIC_AUTH_PROVIDER") === "mock" ? "mock" : "firebase";
}

function readBooleanEnvValue(source: EnvSource, key: string): boolean {
  const value = readEnvValue(source, key).toLowerCase();
  return value === "1" || value === "true" || value === "yes" || value === "on";
}

export function readPublicRuntimeConfig(source: EnvSource = process.env): PublicRuntimeConfig {
  const authProvider = readAuthProvider(source);
  const requiredKeys =
    authProvider === "mock" ? SHARED_REQUIRED_RUNTIME_KEYS : REQUIRED_FIREBASE_RUNTIME_KEYS;
  const missingKeys = requiredKeys.filter((key) => readEnvValue(source, key).length === 0);

  return {
    apiBaseUrl: readEnvValue(source, "NEXT_PUBLIC_API_BASE_URL"),
    appEnv: readEnvValue(source, "NEXT_PUBLIC_APP_ENV") || "development",
    authProvider,
    firebase: {
      apiKey: readEnvValue(source, "NEXT_PUBLIC_FIREBASE_API_KEY"),
      authDomain: readEnvValue(source, "NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN"),
      projectId: readEnvValue(source, "NEXT_PUBLIC_FIREBASE_PROJECT_ID"),
      storageBucket: readEnvValue(source, "NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET"),
      messagingSenderId: readEnvValue(source, "NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID"),
      appId: readEnvValue(source, "NEXT_PUBLIC_FIREBASE_APP_ID"),
      measurementId: readEnvValue(source, "NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID") || null,
    },
    hostingTarget: readEnvValue(source, "NEXT_PUBLIC_HOSTING_TARGET") || "firebase-hosting",
    isConfigured: missingKeys.length === 0,
    missingKeys,
    mockUserId: readEnvValue(source, "NEXT_PUBLIC_MOCK_USER_ID") || "local-editor",
    telemetryEnabled: readBooleanEnvValue(source, "NEXT_PUBLIC_TELEMETRY_ENABLED"),
  };
}

export function readProcessPublicRuntimeConfig(): PublicRuntimeConfig {
  return readPublicRuntimeConfig({
    // Next.js only exposes NEXT_PUBLIC_* values in the client bundle for static property reads.
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
  });
}

export const publicRuntimeConfig = readProcessPublicRuntimeConfig();
