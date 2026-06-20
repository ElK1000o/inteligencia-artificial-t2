"""Integration tests: Role-Based Access Control on API endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def _auth(roles: list) -> dict:
    return {"sub": "00000000-0000-0000-0000-000000000001", "roles": roles}


class TestRBACModelTraining:
    def test_viewer_cannot_train_model(self, client):
        with patch("app.api.v1.model_routes.get_current_user_payload") as mock_auth:
            mock_auth.return_value = _auth(["viewer"])
            resp = client.post(
                "/api/v1/models/train",
                json={
                    "model_type": "random_forest_regressor",
                    "task_type": "regression",
                    "target_property": "energy_above_hull",
                    "dataset_id": "00000000-0000-0000-0000-000000000001",
                    "descriptor_set_id": "00000000-0000-0000-0000-000000000002",
                },
                headers={"Authorization": "Bearer fake"},
            )
        # Viewer should be rejected with 403
        assert resp.status_code == 403

    def test_unauthenticated_cannot_access_any_endpoint(self, client):
        sensitive_endpoints = [
            ("GET", "/api/v1/datasets"),
            ("GET", "/api/v1/materials"),
            ("GET", "/api/v1/models"),
            ("GET", "/api/v1/rankings"),
            ("GET", "/api/v1/dashboard/stats"),
        ]
        for method, path in sensitive_endpoints:
            resp = client.request(method, path)
            assert resp.status_code == 401, f"{method} {path} should return 401"


class TestRBACUserManagement:
    def test_viewer_cannot_list_users(self, client):
        with patch("app.api.v1.user_routes.get_current_user_payload") as mock_auth:
            mock_auth.return_value = _auth(["viewer"])
            resp = client.get(
                "/api/v1/users",
                headers={"Authorization": "Bearer fake"},
            )
        assert resp.status_code == 403

    def test_researcher_cannot_list_users(self, client):
        with patch("app.api.v1.user_routes.get_current_user_payload") as mock_auth:
            mock_auth.return_value = _auth(["researcher"])
            resp = client.get(
                "/api/v1/users",
                headers={"Authorization": "Bearer fake"},
            )
        assert resp.status_code == 403


class TestRBACAdminEndpoints:
    def test_admin_can_access_user_list(self, client):
        with patch("app.api.v1.user_routes.get_current_user_payload") as mock_auth:
            with patch("app.api.v1.user_routes.get_db") as mock_db:
                from unittest.mock import MagicMock
                mock_auth.return_value = _auth(["admin"])
                mock_session = MagicMock()
                mock_session.execute.return_value.scalars.return_value.all.return_value = []
                mock_db.return_value = iter([mock_session])
                resp = client.get(
                    "/api/v1/users",
                    headers={"Authorization": "Bearer fake"},
                )
        assert resp.status_code != 403


class TestTokenValidation:
    def test_no_authorization_header_returns_401(self, client):
        resp = client.get("/api/v1/materials")
        assert resp.status_code == 401

    def test_empty_bearer_token_returns_401(self, client):
        resp = client.get(
            "/api/v1/materials",
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code == 401

    def test_wrong_scheme_returns_401(self, client):
        resp = client.get(
            "/api/v1/materials",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert resp.status_code == 401
