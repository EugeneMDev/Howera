"""Authentication dependency and adapter tests for Story 1.1."""

from __future__ import annotations

from datetime import UTC, datetime
import os
import sys
import types
import unittest
from unittest.mock import patch

from fastapi import Request
from fastapi.testclient import TestClient

from app.adapters.auth.base import AuthVerificationError
from app.adapters.auth.firebase_auth import FirebaseTokenVerifier
from app.adapters.auth.mock_auth import MockTokenVerifier
from app.core.config import Settings, get_settings
from app.main import create_app
from app.routes.dependencies import get_project_service, get_token_verifier
from app.schemas.project import Project


class _CapturingProjectService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def create_project(self, *, owner_id: str, name: str) -> Project:
        self.calls.append((owner_id, name))
        return Project(id="project-1", name=name, created_at=datetime.now(UTC))


class _SettingsEnvCase(unittest.TestCase):
    _env_keys = (
        "HOWERA_AUTH_PROVIDER",
        "HOWERA_CALLBACK_SECRET",
        "HOWERA_FIREBASE_PROJECT_ID",
        "HOWERA_FIREBASE_AUDIENCE",
    )

    def setUp(self) -> None:
        self._old_env = {k: os.environ.get(k) for k in self._env_keys}
        os.environ["HOWERA_AUTH_PROVIDER"] = "mock"
        os.environ["HOWERA_CALLBACK_SECRET"] = "test-callback-secret"
        os.environ["HOWERA_FIREBASE_PROJECT_ID"] = "test-project"
        os.environ["HOWERA_FIREBASE_AUDIENCE"] = "test-audience"
        get_settings.cache_clear()

    def tearDown(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        get_settings.cache_clear()


class AuthApiTests(_SettingsEnvCase):
    def test_openapi_includes_story_paths_and_contract_response_codes(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.get("/openapi.json")
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]

        self.assertIn("/api/v1/projects", paths)
        self.assertIn("/api/v1/projects/{projectId}/jobs", paths)
        self.assertIn("/api/v1/internal/jobs/{jobId}/status", paths)

        self.assertEqual(set(paths["/api/v1/projects"]["post"]["responses"].keys()), {"201", "401"})
        self.assertEqual(
            set(paths["/api/v1/projects/{projectId}/jobs"]["post"]["responses"].keys()),
            {"201", "401", "404"},
        )
        self.assertEqual(
            set(paths["/api/v1/internal/jobs/{jobId}/status"]["post"]["responses"].keys()),
            {"200", "204", "401", "404", "409"},
        )

    def test_missing_authorization_header_returns_401_and_no_project_side_effect(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.post("/api/v1/projects", json={"name": "Demo"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "UNAUTHORIZED")
        self.assertEqual(app.state.store.project_write_count, 0)

    def test_invalid_project_payload_returns_401_and_no_project_side_effect(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test:user-1:editor"},
            json={},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "UNAUTHORIZED")
        self.assertEqual(app.state.store.project_write_count, 0)

    def test_invalid_bearer_token_returns_401_and_no_job_side_effect(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/api/v1/projects/project-1/jobs",
            headers={"Authorization": "Bearer not-a-valid-token"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "UNAUTHORIZED")
        self.assertEqual(app.state.store.job_write_count, 0)

    def test_valid_bearer_token_resolves_user_id_for_downstream_handler(self) -> None:
        app = create_app()
        client = TestClient(app)

        capturing_service = _CapturingProjectService()
        app.dependency_overrides[get_project_service] = lambda: capturing_service

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test:user-123:editor"},
            json={"name": "Owned Project"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(capturing_service.calls), 1)
        self.assertEqual(capturing_service.calls[0][0], "user-123")
        self.assertEqual(capturing_service.calls[0][1], "Owned Project")

    def test_auth_principal_is_attached_to_request_state(self) -> None:
        app = create_app()
        client = TestClient(app)

        capturing_service = _CapturingProjectService()
        observed_user_id: dict[str, str] = {}

        def _override_project_service(request: Request) -> _CapturingProjectService:
            observed_user_id["value"] = request.state.auth_principal.user_id
            return capturing_service

        app.dependency_overrides[get_project_service] = _override_project_service

        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": "Bearer test:user-state:editor"},
            json={"name": "State Project"},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(observed_user_id.get("value"), "user-state")

    def test_internal_callback_uses_callback_secret_not_bearer(self) -> None:
        app = create_app()
        client = TestClient(app)

        body = {
            "event_id": "evt-1",
            "status": "CREATED",
            "occurred_at": "2026-02-22T00:00:00Z",
            "correlation_id": "corr-1",
        }

        unauthorized = client.post("/api/v1/internal/jobs/job-1/status", json=body)
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(unauthorized.json()["code"], "UNAUTHORIZED")

        authorized = client.post(
            "/api/v1/internal/jobs/job-1/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json=body,
        )
        self.assertEqual(authorized.status_code, 204)

    def test_invalid_callback_payload_returns_401(self) -> None:
        app = create_app()
        client = TestClient(app)

        response = client.post(
            "/api/v1/internal/jobs/job-1/status",
            headers={"X-Callback-Secret": "test-callback-secret"},
            json={"event_id": "evt-1"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "UNAUTHORIZED")


class AuthAdapterUnitTests(unittest.TestCase):
    def test_mock_token_verifier_normalizes_principal(self) -> None:
        verifier = MockTokenVerifier()

        principal = verifier.verify_token("test:user-999:editor")

        self.assertEqual(principal.user_id, "user-999")
        self.assertEqual(principal.role, "editor")

    def test_mock_token_verifier_rejects_invalid_token(self) -> None:
        verifier = MockTokenVerifier()

        with self.assertRaises(AuthVerificationError):
            verifier.verify_token("invalid")

    def test_dependency_selects_firebase_verifier(self) -> None:
        settings = Settings(
            auth_provider="firebase",
            callback_secret="secret",
            firebase_project_id="project-a",
            firebase_audience="aud-a",
        )

        verifier = get_token_verifier(settings)

        self.assertIsInstance(verifier, FirebaseTokenVerifier)


class FirebaseVerifierUnitTests(unittest.TestCase):
    @staticmethod
    def _fake_firebase_modules(decoded_token: dict[str, str]) -> dict[str, types.ModuleType]:
        fake_admin = types.ModuleType("firebase_admin")
        fake_auth = types.ModuleType("firebase_admin.auth")

        fake_admin._apps = []

        def initialize_app() -> object:
            app_handle = object()
            fake_admin._apps.append(app_handle)
            return app_handle

        def verify_id_token(token: str, check_revoked: bool = True) -> dict[str, str]:
            if token != "valid-jwt":
                raise ValueError("invalid token")
            if not check_revoked:
                raise ValueError("must validate revoked tokens")
            return decoded_token

        fake_admin.initialize_app = initialize_app
        fake_admin.auth = fake_auth
        fake_auth.verify_id_token = verify_id_token

        return {
            "firebase_admin": fake_admin,
            "firebase_admin.auth": fake_auth,
        }

    def test_firebase_verifier_normalizes_principal(self) -> None:
        fake_modules = self._fake_firebase_modules(
            {
                "uid": "firebase-user-1",
                "aud": "aud-a",
                "iss": "https://securetoken.google.com/project-a",
                "role": "editor",
            }
        )

        with patch.dict(sys.modules, fake_modules):
            verifier = FirebaseTokenVerifier(project_id="project-a", audience="aud-a")
            principal = verifier.verify_token("valid-jwt")

        self.assertEqual(principal.user_id, "firebase-user-1")
        self.assertEqual(principal.role, "editor")

    def test_firebase_verifier_rejects_invalid_audience(self) -> None:
        fake_modules = self._fake_firebase_modules(
            {
                "uid": "firebase-user-1",
                "aud": "unexpected-aud",
                "iss": "https://securetoken.google.com/project-a",
            }
        )

        with patch.dict(sys.modules, fake_modules):
            verifier = FirebaseTokenVerifier(project_id="project-a", audience="aud-a")
            with self.assertRaises(AuthVerificationError):
                verifier.verify_token("valid-jwt")


if __name__ == "__main__":
    unittest.main()
