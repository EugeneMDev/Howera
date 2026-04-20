"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import type { User } from "firebase/auth";
import {
  getRedirectResult,
  onIdTokenChanged,
  signInWithRedirect,
  signOut,
} from "firebase/auth";

import { publicRuntimeConfig } from "@/shared/config/runtime";
import type { ApiClientError } from "@/shared/api/errors";
import { getFirebaseAuth, getGoogleProvider } from "@/features/auth/firebase-client";

type AuthStatus = "loading" | "authenticated" | "unauthenticated" | "error";

interface AuthContextValue {
  error: string | null;
  getAccessToken: () => Promise<string | null>;
  handleUnauthorized: (_error: ApiClientError) => Promise<void>;
  hasFirebaseConfig: boolean;
  missingFirebaseKeys: string[];
  signIn: () => Promise<void>;
  signOutUser: () => Promise<void>;
  status: AuthStatus;
  user: User | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function formatAuthError(error: unknown): string {
  if (typeof error === "object" && error !== null && "code" in error) {
    const code = String((error as { code?: string }).code ?? "");
    if (code.includes("popup")) {
      return "Firebase sign-in must complete in a redirect flow.";
    }
    if (code.includes("network")) {
      return "Firebase sign-in failed because the network request was interrupted.";
    }
  }

  return "Authentication failed. Try signing in again.";
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [missingFirebaseKeys, setMissingFirebaseKeys] = useState<string[]>([]);
  const authProvider = publicRuntimeConfig.authProvider;
  const hasFirebaseConfig = missingFirebaseKeys.length === 0;
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authProvider === "mock") {
      setMissingFirebaseKeys([]);
      setUser(null);
      setError(null);
      setStatus("authenticated");
      return;
    }

    const nextMissingFirebaseKeys = publicRuntimeConfig.missingKeys.filter((key) =>
      key.startsWith("NEXT_PUBLIC_FIREBASE_"),
    );

    setMissingFirebaseKeys(nextMissingFirebaseKeys);
    if (nextMissingFirebaseKeys.length > 0) {
      setUser(null);
      setError(`Missing Firebase config: ${nextMissingFirebaseKeys.join(", ")}`);
      setStatus("error");
      return;
    }

    const auth = getFirebaseAuth(publicRuntimeConfig.firebase);
    let isMounted = true;

    void getRedirectResult(auth).catch((redirectError) => {
      if (!isMounted) {
        return;
      }
      setError(formatAuthError(redirectError));
      setStatus("error");
    });

    const unsubscribe = onIdTokenChanged(auth, (nextUser) => {
      if (!isMounted) {
        return;
      }

      setUser(nextUser);
      setStatus(nextUser ? "authenticated" : "unauthenticated");
      setError(null);
    });

    return () => {
      isMounted = false;
      unsubscribe();
    };
  }, [authProvider]);

  async function signIn(): Promise<void> {
    if (authProvider === "mock") {
      setError(null);
      setStatus("authenticated");
      return;
    }

    if (!hasFirebaseConfig) {
      setStatus("error");
      setError(`Missing Firebase config: ${missingFirebaseKeys.join(", ")}`);
      return;
    }

    try {
      setError(null);
      await signInWithRedirect(getFirebaseAuth(publicRuntimeConfig.firebase), getGoogleProvider());
    } catch (signInError) {
      setError(formatAuthError(signInError));
      setStatus("error");
    }
  }

  async function signOutUser(): Promise<void> {
    if (authProvider === "mock") {
      setUser(null);
      setError(null);
      setStatus("unauthenticated");
      return;
    }

    if (!hasFirebaseConfig) {
      setUser(null);
      setStatus("unauthenticated");
      return;
    }

    try {
      await signOut(getFirebaseAuth(publicRuntimeConfig.firebase));
    } finally {
      setUser(null);
      setStatus("unauthenticated");
    }
  }

  async function getAccessToken(): Promise<string | null> {
    if (authProvider === "mock") {
      return `test:${publicRuntimeConfig.mockUserId}:editor`;
    }

    if (!hasFirebaseConfig) {
      return null;
    }

    const auth = getFirebaseAuth(publicRuntimeConfig.firebase);
    if (!auth.currentUser) {
      return null;
    }

    return auth.currentUser.getIdToken();
  }

  async function handleUnauthorized(apiError: ApiClientError): Promise<void> {
    void apiError;

    if (authProvider === "mock") {
      setError(
        "Mock auth token was rejected by the API. Set NEXT_PUBLIC_AUTH_PROVIDER=mock with a valid NEXT_PUBLIC_MOCK_USER_ID, or run the backend with HOWERA_AUTH_PROVIDER=firebase.",
      );
      setStatus("error");
      return;
    }

    setError("Your session expired or was rejected by the API. Sign in again.");
    await signOutUser();
  }

  return (
    <AuthContext.Provider
      value={{
        error,
        getAccessToken,
        handleUnauthorized,
        hasFirebaseConfig,
        missingFirebaseKeys,
        signIn,
        signOutUser,
        status,
        user,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}
