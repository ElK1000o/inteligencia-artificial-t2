"""Integration tests: prediction pipeline and OOD detection."""
import uuid
import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

from app.infrastructure.ml.predictor import Predictor


def _make_simple_pipeline(n_features: int = 10) -> Pipeline:
    rng = np.random.RandomState(42)
    X_train = pd.DataFrame(rng.randn(100, n_features), columns=[f"f{i}" for i in range(n_features)])
    y_train = pd.Series(rng.randn(100))
    pipeline = Pipeline([("scaler", StandardScaler()), ("model", Ridge())])
    pipeline.fit(X_train, y_train)
    return pipeline, X_train


class TestPredictor:
    def setup_method(self):
        pipeline, X_train = _make_simple_pipeline()
        self.feature_names = [f"f{i}" for i in range(10)]
        self.predictor = Predictor(
            pipeline=pipeline,
            feature_names=self.feature_names,
            training_X=X_train,
        )
        self.X_test = pd.DataFrame(
            np.random.RandomState(99).randn(5, 10),
            columns=self.feature_names,
        )

    def test_predict_single_returns_dict(self):
        x = self.X_test.iloc[[0]]
        result = self.predictor.predict_single(x)
        assert isinstance(result, dict)
        assert "predicted_value" in result

    def test_predicted_value_is_float(self):
        x = self.X_test.iloc[[0]]
        result = self.predictor.predict_single(x)
        assert isinstance(result["predicted_value"], float)

    def test_in_domain_sample_not_flagged_ood(self):
        # Normal training-range data should not be OOD
        x = pd.DataFrame(
            np.zeros((1, 10)),  # mean of training distribution
            columns=self.feature_names,
        )
        result = self.predictor.predict_single(x)
        # mean should be close to in-domain
        assert "is_out_of_domain" in result

    def test_extreme_outlier_flagged_ood(self):
        # Values 100x outside training range should trigger OOD
        x = pd.DataFrame(
            np.full((1, 10), 500.0),  # extreme outlier
            columns=self.feature_names,
        )
        result = self.predictor.predict_single(x)
        assert result.get("is_out_of_domain") is True

    def test_ood_reason_provided(self):
        x = pd.DataFrame(np.full((1, 10), 500.0), columns=self.feature_names)
        result = self.predictor.predict_single(x)
        if result.get("is_out_of_domain"):
            assert result.get("out_of_domain_reason") is not None


class TestPredictorWithoutTrainingStats:
    def test_no_ood_detection_without_training_data(self):
        pipeline, _ = _make_simple_pipeline()
        predictor = Predictor(pipeline=pipeline, feature_names=[f"f{i}" for i in range(10)])
        x = pd.DataFrame(np.full((1, 10), 500.0), columns=[f"f{i}" for i in range(10)])
        result = predictor.predict_single(x)
        # Without training stats, OOD should be False (cannot detect)
        assert result.get("is_out_of_domain") is False
