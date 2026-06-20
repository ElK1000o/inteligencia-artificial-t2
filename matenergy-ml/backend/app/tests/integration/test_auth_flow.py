"""Integration tests: authentication flow (login, refresh, logout, register)."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestLoginEndpoint:
    def test_login_wrong_credentials_returns_401(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401
        # Must not reveal whether the user exists or not
        assert "invalid" in resp.json().get("detail", "").lower()

    def test_login_missing_body_returns_422(self, client):
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422

    def test_login_error_is_generic(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "admin@matenergy.local",
            "password": "incorrectpassword",
        })
        detail = resp.json().get("detail", "")
        # Must not expose whether the email exists
        assert "email" not in detail.lower() or "invalid" in detail.lower()
        assert "password" not in detail.lower() or "invalid" in detail.lower()


class TestProtectedEndpoints:
    def test_unauthenticated_request_returns_401(self, client):
        resp = client.get("/api/v1/materials")
        assert resp.status_code == 401

    def test_invalid_bearer_token_returns_401(self, client):
        resp = client.get(
            "/api/v1/materials",
            headers={"Authorization": "Bearer this.is.not.a.valid.jwt"},
        )
        assert resp.status_code == 401

    def test_expired_token_returns_401(self, client):
        # An obviously expired token (exp=0)
        expired_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            ".eyJzdWIiOiJ0ZXN0IiwiZXhwIjoxfQ"
            ".fake_signature"
        )
        resp = client.get(
            "/api/v1/materials",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    def test_malformed_authorization_header(self, client):
        resp = client.get(
            "/api/v1/materials",
            headers={"Authorization": "NotBearer token"},
        )
        assert resp.status_code == 401


class TestHealthEndpoints:
    def test_health_liveness(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_api_v1_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["api_version"] == "v1"
