"""Tests for model artifact hash verification."""
import pytest
import uuid
import tempfile
import os
import joblib
from pathlib import Path
from sklearn.linear_model import Ridge
from app.infrastructure.ml.trainers import ModelTrainer
from app.core.exceptions import ArtifactIntegrityError

class TestArtifactIntegrity:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.trainer = ModelTrainer(artifact_storage_path=self.tmpdir)

    def test_saved_artifact_can_be_loaded(self):
        model = Ridge()
        import pandas as pd, numpy as np
        X = pd.DataFrame(np.random.rand(50, 5))
        y = pd.Series(np.random.rand(50))
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        pipeline = Pipeline([("s", StandardScaler()), ("m", Ridge())])
        pipeline.fit(X, y)

        path, sha = self.trainer.save_artifact(pipeline, "test_model")
        loaded = self.trainer.load_artifact(path, sha)
        assert loaded is not None

    def test_tampered_artifact_raises(self):
        import pandas as pd, numpy as np
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler
        X = pd.DataFrame(np.random.rand(50, 5))
        y = pd.Series(np.random.rand(50))
        pipeline = Pipeline([("s", StandardScaler()), ("m", Ridge())])
        pipeline.fit(X, y)

        path, sha = self.trainer.save_artifact(pipeline, "test_model")

        # Tamper with the file
        with open(path, "ab") as f:
            f.write(b"\x00\x00")

        with pytest.raises(ArtifactIntegrityError) as exc:
            self.trainer.load_artifact(path, sha)
        assert exc.value.code == "ARTIFACT_HASH_MISMATCH"

    def test_missing_artifact_raises(self):
        with pytest.raises(ArtifactIntegrityError) as exc:
            self.trainer.load_artifact("/nonexistent/path/model.joblib", "fakehash")
        assert exc.value.code == "ARTIFACT_NOT_FOUND"
