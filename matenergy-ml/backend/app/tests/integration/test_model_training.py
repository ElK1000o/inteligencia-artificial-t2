"""Integration tests: ML training pipeline."""
import tempfile
import uuid
import pytest
import numpy as np
import pandas as pd

from app.infrastructure.ml.trainers import ModelTrainer
from app.infrastructure.ml.evaluators import RegressionEvaluator, ClassificationEvaluator
from app.infrastructure.ml.preprocessing import prepare_train_test, remove_constant_features, check_for_leakage
from app.core.constants import ModelType, TaskType
from app.core.exceptions import ModelTrainingError, UnsupportedModelTypeError


def make_regression_data(n: int = 80, n_features: int = 30) -> tuple:
    rng = np.random.RandomState(42)
    X = pd.DataFrame(rng.randn(n, n_features), columns=[f"f{i}" for i in range(n_features)])
    y = pd.Series(rng.randn(n) * 0.5, name="energy_above_hull")
    return X, y


def make_classification_data(n: int = 80, n_features: int = 30) -> tuple:
    rng = np.random.RandomState(42)
    X = pd.DataFrame(rng.randn(n, n_features), columns=[f"f{i}" for i in range(n_features)])
    y = pd.Series((rng.randn(n) > 0).astype(int), name="is_stable")
    return X, y


@pytest.fixture
def trainer():
    tmpdir = tempfile.mkdtemp()
    return ModelTrainer(tmpdir)


class TestModelTrainerIntegration:
    def test_ridge_regression_trains_and_predicts(self, trainer):
        X, y = make_regression_data()
        X_tr, X_te, y_tr, y_te = prepare_train_test(X, y, test_size=0.2)
        pipeline, info = trainer.train(ModelType.RIDGE_REGRESSION, TaskType.REGRESSION, X_tr, y_tr)
        preds = pipeline.predict(X_te)
        assert len(preds) == len(y_te)
        assert "duration_seconds" in info

    def test_random_forest_regressor_trains(self, trainer):
        X, y = make_regression_data()
        X_tr, X_te, y_tr, y_te = prepare_train_test(X, y, test_size=0.2)
        pipeline, _ = trainer.train(ModelType.RANDOM_FOREST_REGRESSOR, TaskType.REGRESSION, X_tr, y_tr)
        assert pipeline is not None

    def test_gradient_boosting_regressor_trains(self, trainer):
        X, y = make_regression_data()
        X_tr, X_te, y_tr, y_te = prepare_train_test(X, y, test_size=0.2)
        pipeline, _ = trainer.train(ModelType.GRADIENT_BOOSTING_REGRESSOR, TaskType.REGRESSION, X_tr, y_tr)
        assert pipeline is not None

    def test_random_forest_classifier_trains(self, trainer):
        X, y = make_classification_data()
        X_tr, X_te, y_tr, y_te = prepare_train_test(X, y, test_size=0.2, stratify=y)
        pipeline, _ = trainer.train(ModelType.RANDOM_FOREST_CLASSIFIER, TaskType.CLASSIFICATION, X_tr, y_tr)
        assert pipeline is not None

    def test_training_is_reproducible(self, trainer):
        X, y = make_regression_data()
        X_tr, X_te, y_tr, y_te = prepare_train_test(X, y, test_size=0.2)
        p1, _ = trainer.train(ModelType.RIDGE_REGRESSION, TaskType.REGRESSION, X_tr, y_tr)
        p2, _ = trainer.train(ModelType.RIDGE_REGRESSION, TaskType.REGRESSION, X_tr, y_tr)
        pred1 = p1.predict(X_te)
        pred2 = p2.predict(X_te)
        np.testing.assert_array_almost_equal(pred1, pred2)

    def test_artifact_saved_and_hash_returned(self, trainer):
        X, y = make_regression_data()
        X_tr, _, y_tr, _ = prepare_train_test(X, y, test_size=0.2)
        pipeline, _ = trainer.train(ModelType.RIDGE_REGRESSION, TaskType.REGRESSION, X_tr, y_tr)
        path, sha256 = trainer.save_artifact(pipeline, "test_model")
        assert len(sha256) == 64  # SHA-256 hex
        from pathlib import Path
        assert Path(path).exists()

    def test_unsupported_model_type_raises(self, trainer):
        X, y = make_regression_data()
        X_tr, _, y_tr, _ = prepare_train_test(X, y, test_size=0.2)
        with pytest.raises((UnsupportedModelTypeError, Exception)):
            trainer.train(ModelType.RANDOM_FOREST_CLASSIFIER, TaskType.REGRESSION, X_tr, y_tr)


class TestEvaluatorsIntegration:
    def test_regression_evaluator_returns_all_metrics(self, trainer):
        X, y = make_regression_data()
        X_tr, X_te, y_tr, y_te = prepare_train_test(X, y, test_size=0.2)
        pipeline, _ = trainer.train(ModelType.RIDGE_REGRESSION, TaskType.REGRESSION, X_tr, y_tr)
        evaluator = RegressionEvaluator()
        result = evaluator.evaluate(pipeline, X_tr, X_te, y_tr, y_te)
        metric_names = {m["metric_name"] for m in result["metrics"]}
        assert "mae" in metric_names
        assert "r2" in metric_names
        assert "rmse" in metric_names

    def test_classification_evaluator_returns_all_metrics(self, trainer):
        X, y = make_classification_data()
        X_tr, X_te, y_tr, y_te = prepare_train_test(X, y, test_size=0.2, stratify=y)
        pipeline, _ = trainer.train(ModelType.RANDOM_FOREST_CLASSIFIER, TaskType.CLASSIFICATION, X_tr, y_tr)
        evaluator = ClassificationEvaluator()
        result = evaluator.evaluate(pipeline, X_tr, X_te, y_tr, y_te)
        metric_names = {m["metric_name"] for m in result["metrics"]}
        assert "accuracy" in metric_names
        assert "f1" in metric_names


class TestPreprocessingIntegration:
    def test_constant_feature_removal(self):
        X, y = make_regression_data()
        X["constant_col"] = 5.0  # constant feature
        X_clean, removed = remove_constant_features(X)
        assert "constant_col" in removed
        assert "constant_col" not in X_clean.columns

    def test_leakage_detection_raises(self):
        from app.core.exceptions import TargetLeakageError
        with pytest.raises((TargetLeakageError, Exception)):
            check_for_leakage(["energy_above_hull", "f1", "f2"], "energy_above_hull")
