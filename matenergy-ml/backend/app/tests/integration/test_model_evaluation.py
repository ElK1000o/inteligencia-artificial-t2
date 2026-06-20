"""Integration tests: model evaluation use case."""
import uuid
import tempfile
import pytest
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from unittest.mock import MagicMock, patch
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

from app.application.use_cases.verify_model_artifact_use_case import VerifyModelArtifactUseCase
from app.application.use_cases.register_model_artifact_use_case import RegisterModelArtifactUseCase
from app.core.exceptions import ArtifactIntegrityError, NotFoundError


def _make_and_save_pipeline(tmpdir: str) -> tuple[str, str]:
    """Create a trained pipeline, save it, return (path, sha256)."""
    import hashlib
    X = pd.DataFrame(np.random.randn(50, 5), columns=list("abcde"))
    y = pd.Series(np.random.randn(50))
    p = Pipeline([("scaler", StandardScaler()), ("model", Ridge())])
    p.fit(X, y)
    path = Path(tmpdir) / f"test_artifact_{uuid.uuid4()}.joblib"
    joblib.dump(p, path, compress=3)
    h = hashlib.sha256(path.read_bytes()).hexdigest()
    return str(path), h


class TestVerifyModelArtifactUseCase:
    def test_missing_artifact_record_raises_not_found(self):
        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        uc = VerifyModelArtifactUseCase(mock_db)
        with pytest.raises(NotFoundError):
            uc.execute(uuid.uuid4())

    def test_missing_file_raises_integrity_error(self):
        from app.infrastructure.database.models.model_models import ModelArtifact
        artifact = MagicMock(spec=ModelArtifact)
        artifact.file_path = "/nonexistent/path/model.joblib"
        artifact.sha256_hash = "abc123"
        artifact.id = uuid.uuid4()

        mock_db = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = artifact
        uc = VerifyModelArtifactUseCase(mock_db)
        with pytest.raises(ArtifactIntegrityError) as exc_info:
            uc.execute(uuid.uuid4())
        assert "missing" in exc_info.value.code.lower()

    def test_hash_mismatch_raises_integrity_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path, correct_sha256 = _make_and_save_pipeline(tmpdir)

            from app.infrastructure.database.models.model_models import ModelArtifact
            artifact = MagicMock(spec=ModelArtifact)
            artifact.file_path = path
            artifact.sha256_hash = "deadbeef" * 8  # wrong hash
            artifact.id = uuid.uuid4()

            mock_db = MagicMock()
            mock_db.execute.return_value.scalar_one_or_none.return_value = artifact
            uc = VerifyModelArtifactUseCase(mock_db)
            with pytest.raises(ArtifactIntegrityError) as exc_info:
                uc.execute(uuid.uuid4())
            assert "mismatch" in exc_info.value.code.lower()

    def test_correct_hash_returns_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path, correct_sha256 = _make_and_save_pipeline(tmpdir)

            from app.infrastructure.database.models.model_models import ModelArtifact
            artifact = MagicMock(spec=ModelArtifact)
            artifact.file_path = path
            artifact.sha256_hash = correct_sha256
            artifact.id = uuid.uuid4()
            artifact.created_at = None

            mock_db = MagicMock()
            mock_db.execute.return_value.scalar_one_or_none.return_value = artifact
            uc = VerifyModelArtifactUseCase(mock_db)
            result = uc.execute(uuid.uuid4())
            assert result["integrity_ok"] is True
            assert result["computed_sha256"] == correct_sha256
