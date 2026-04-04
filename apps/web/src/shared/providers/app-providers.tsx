"use client";

import {
  createContext,
  useContext,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { useAuth } from "@/features/auth/auth-provider";
import { createApiClient, type ApiClient } from "@/shared/api/client";
import {
  publicRuntimeConfig,
  type PublicRuntimeConfig,
} from "@/shared/config/runtime";
import {
  createConsoleTelemetryEmitter,
  createTelemetryClient,
  type TelemetryClient,
} from "@/shared/lib/telemetry";

interface QueryStateContextValue {
  getVersion: (key: string) => number;
  invalidateQuery: (key: string) => void;
}

const RuntimeConfigContext = createContext<PublicRuntimeConfig | null>(null);
const ApiClientContext = createContext<ApiClient | null>(null);
const QueryStateContext = createContext<QueryStateContextValue | null>(null);
const TelemetryContext = createContext<TelemetryClient | null>(null);

interface AppProvidersProps {
  children: ReactNode;
}

export function AppProviders({ children }: AppProvidersProps) {
  const runtimeConfig = publicRuntimeConfig;
  const auth = useAuth();
  const apiClientRef = useRef<ApiClient | null>(null);
  const telemetryClientRef = useRef<TelemetryClient | null>(null);
  const accessTokenRef = useRef(auth.getAccessToken);
  const unauthorizedHandlerRef = useRef(auth.handleUnauthorized);
  const queryVersionsRef = useRef<Map<string, number>>(new Map());
  const [, setProviderRevision] = useState(0);

  accessTokenRef.current = auth.getAccessToken;
  unauthorizedHandlerRef.current = auth.handleUnauthorized;

  if (apiClientRef.current === null) {
    apiClientRef.current = createApiClient({
      baseUrl: runtimeConfig.apiBaseUrl,
      getAccessToken: async () => accessTokenRef.current(),
      onUnauthorized: async (error) => unauthorizedHandlerRef.current(error),
    });
  }

  if (telemetryClientRef.current === null) {
    telemetryClientRef.current = createTelemetryClient({
      defaults: {
        appEnv: runtimeConfig.appEnv,
        authProvider: runtimeConfig.authProvider,
        hostingTarget: runtimeConfig.hostingTarget,
      },
      emit: createConsoleTelemetryEmitter(),
      enabled: runtimeConfig.telemetryEnabled,
    });
  }

  const queryState: QueryStateContextValue = {
    getVersion(key: string) {
      return queryVersionsRef.current.get(key) ?? 0;
    },
    invalidateQuery(key: string) {
      const currentVersion = queryVersionsRef.current.get(key) ?? 0;
      queryVersionsRef.current.set(key, currentVersion + 1);
      setProviderRevision((value) => value + 1);
    },
  };

  return (
    <RuntimeConfigContext.Provider value={runtimeConfig}>
      <TelemetryContext.Provider value={telemetryClientRef.current}>
        <ApiClientContext.Provider value={apiClientRef.current}>
          <QueryStateContext.Provider value={queryState}>{children}</QueryStateContext.Provider>
        </ApiClientContext.Provider>
      </TelemetryContext.Provider>
    </RuntimeConfigContext.Provider>
  );
}

export function useRuntimeConfig(): PublicRuntimeConfig {
  const context = useContext(RuntimeConfigContext);
  if (context === null) {
    throw new Error("useRuntimeConfig must be used within AppProviders");
  }

  return context;
}

export function useApiClient(): ApiClient {
  const context = useContext(ApiClientContext);
  if (context === null) {
    throw new Error("useApiClient must be used within AppProviders");
  }

  return context;
}

export function useInvalidateQuery(): QueryStateContextValue["invalidateQuery"] {
  const context = useContext(QueryStateContext);
  if (context === null) {
    throw new Error("useInvalidateQuery must be used within AppProviders");
  }

  return context.invalidateQuery;
}

export function useQueryVersion(key: string): number {
  const context = useContext(QueryStateContext);
  if (context === null) {
    throw new Error("useQueryVersion must be used within AppProviders");
  }

  return context.getVersion(key);
}

export function useTelemetry(): TelemetryClient {
  const context = useContext(TelemetryContext);
  if (context === null) {
    throw new Error("useTelemetry must be used within AppProviders");
  }

  return context;
}
