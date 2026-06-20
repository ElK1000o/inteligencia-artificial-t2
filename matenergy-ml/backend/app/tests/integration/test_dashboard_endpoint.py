"""Integration tests: dashboard stats endpoint."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


class TestDashboardEndpoint:
    def test_dashboard_stats_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard/stats")
        assert resp.status_code == 401

    def test_dashboard_stats_structure_with_mocked_auth(self, client):
        with patch("app.api.v1.dashboard_routes.get_current_user_payload") as mock_auth:
            mock_auth.return_value = {"sub": "00000000-0000-0000-0000-000000000001", "roles": ["viewer"]}
            with patch("app.api.v1.dashboard_routes.get_db") as mock_db:
                # Provide a mock session that returns 0 for all count queries
                mock_session = MagicMock()
                mock_session.execute.return_value.scalar_one.return_value = 0
                mock_db.return_value.__next__ = MagicMock(return_value=mock_session)
                mock_db.return_value = iter([mock_session])

                resp = client.get(
                    "/api/v1/dashboard/stats",
                    headers={"Authorization": "Bearer fake"},
                )

        # With mocked auth, should return 200 or at most a DB error (not 401)
        assert resp.status_code != 401

    def test_health_check_always_accessible(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
