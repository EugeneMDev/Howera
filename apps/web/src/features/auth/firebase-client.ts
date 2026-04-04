import { getApp, getApps, initializeApp, type FirebaseApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, type Auth } from "firebase/auth";

import type { PublicFirebaseConfig } from "@/shared/config/runtime";

let googleProvider: GoogleAuthProvider | null = null;

export function getFirebaseApp(config: PublicFirebaseConfig): FirebaseApp {
  if (getApps().length > 0) {
    return getApp();
  }

  return initializeApp({
    apiKey: config.apiKey,
    authDomain: config.authDomain,
    projectId: config.projectId,
    storageBucket: config.storageBucket,
    messagingSenderId: config.messagingSenderId,
    appId: config.appId,
    measurementId: config.measurementId ?? undefined,
  });
}

export function getFirebaseAuth(config: PublicFirebaseConfig): Auth {
  return getAuth(getFirebaseApp(config));
}

export function getGoogleProvider(): GoogleAuthProvider {
  if (googleProvider) {
    return googleProvider;
  }

  googleProvider = new GoogleAuthProvider();
  googleProvider.setCustomParameters({ prompt: "select_account" });
  return googleProvider;
}
