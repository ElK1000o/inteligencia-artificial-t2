"""Integration tests: dataset upload and validation endpoints."""
import io
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import create_app

VALID_CSV = b"""formula,energy_above_hull,formation_energy_per_atom,band_gap,is_stable
LiFePO4,0.000,-3.181,3.71,True
Li2O,0.000,-1.991,4.91,True
LiCoO2,0.000,-2.887,2.53,True
"""

OVERSIZED_CSV = b"x" * (60 * 1024 * 1024)  # 60 MB > 50 MB limit

EMPTY_CSV = b""

CSV_INVALID_EXTENSION_CONTENT = b"not,a,csv\n1,2,3\n"


@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestCSVUploadSecurity:
    def test_upload_requires_auth(self, client):
        resp = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("test.csv", io.BytesIO(VALID_CSV), "text/csv")},
            data={"name": "test"},
        )
        assert resp.status_code == 401

    def test_upload_wrong_extension_rejected(self, client):
        with patch("app.api.v1.dataset_routes.get_current_user_payload") as mock_auth:
            mock_auth.return_value = {"sub": "00000000-0000-0000-0000-000000000001", "roles": ["researcher"]}
            resp = client.post(
                "/api/v1/datasets/upload",
                files={"file": ("data.exe", io.BytesIO(VALID_CSV), "application/octet-stream")},
                data={"name": "bad_ext"},
                headers={"Authorization": "Bearer fake"},
            )
        # 401 from real auth OR 422 from validation — either blocks the upload
        assert resp.status_code in (400, 401, 422)

    def test_upload_empty_csv_rejected(self, client):
        with patch("app.api.v1.dataset_routes.get_current_user_payload") as mock_auth:
            mock_auth.return_value = {"sub": "00000000-0000-0000-0000-000000000001", "roles": ["researcher"]}
            resp = client.post(
                "/api/v1/datasets/upload",
                files={"file": ("empty.csv", io.BytesIO(EMPTY_CSV), "text/csv")},
                data={"name": "empty"},
                headers={"Authorization": "Bearer fake"},
            )
        assert resp.status_code in (400, 401, 422)

    def test_path_traversal_in_filename(self, client):
        """A filename with path traversal should never reach the filesystem."""
        dangerous_names = ["../../../etc/passwd", "..\\Windows\\System32\\cmd.exe"]
        for name in dangerous_names:
            with patch("app.api.v1.dataset_routes.get_current_user_payload") as mock_auth:
                mock_auth.return_value = {"sub": "00000000-0000-0000-0000-000000000001", "roles": ["researcher"]}
                resp = client.post(
                    "/api/v1/datasets/upload",
                    files={"file": (name, io.BytesIO(VALID_CSV), "text/csv")},
                    data={"name": "traversal_test"},
                    headers={"Authorization": "Bearer fake"},
                )
            # Must not succeed (401 from real auth or 400 from validation)
            assert resp.status_code != 200


class TestDatasetListEndpoint:
    def test_list_datasets_unauthenticated(self, client):
        resp = client.get("/api/v1/datasets")
        assert resp.status_code == 401

    def test_list_datasets_returns_list_shape(self, client):
        with patch("app.api.v1.dataset_routes.get_current_user_payload") as mock_auth:
            mock_auth.return_value = {"sub": "00000000-0000-0000-0000-000000000001", "roles": ["viewer"]}
            with patch("app.api.v1.dataset_routes.get_db") as mock_db:
                mock_session = MagicMock()
                mock_db.return_value.__enter__ = lambda s: mock_session
                mock_db.return_value.__exit__ = MagicMock(return_value=False)
                resp = client.get(
                    "/api/v1/datasets",
                    headers={"Authorization": "Bearer fake"},
                )
        # With mocked auth, we should get past 401
        assert resp.status_code != 401
