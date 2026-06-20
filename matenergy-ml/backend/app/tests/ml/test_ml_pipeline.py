"""Tests for ML training and evaluation pipeline."""
import pytest
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from app.infrastructure.ml.trainers import ModelTrainer
from app.infrastructure.ml.evaluators import RegressionEvaluator, ClassificationEvaluator
from app.core.constants import ModelType, TaskType, FIXED_RANDOM_SEED
import tempfile

def make_regression_data(n=100, n_features=20):
    rng = np.random.RandomState(42)
    X = pd.DataFrame(rng.randn(n, n_features), columns=[f"f{i}" for i in range(n_features)])
    y = pd.Series(rng.randn(n), name="target")
    return X, y

def make_classification_data(n=100, n_features=20):
    rng = np.random.RandomState(42)
    X = pd.DataFrame(rng.randn(n, n_features), columns=[f"f{i}" for i in range(n_features)])
    y = pd.Series(rng.randint(0, 2, n), name="target")
    return X, y

class TestModelTraining:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.trainer = ModelTrainer(self.tmpdir)

    def _split(self, X, y, n_test=20):
        return X[:-n_test], X[-n_test:], y[:-n_test], y[-n_test:]

    def test_ridge_regression_trains(self):
        X, y = make_regression_data()
        X_tr, X_te, y_tr, y_te = self._split(X, y)
        pipeline, info = self.trainer.train(ModelType.RIDGE_REGRESSION, TaskType.REGRESSION, X_tr, y_tr)
        assert isinstance(pipeline, Pipeline)

    def test_random_forest_regressor_trains(self):
        X, y = make_regression_data()
        X_tr, X_te, y_tr, y_te = self._split(X, y)
        pipeline, _ = self.trainer.train(ModelType.RANDOM_FOREST_REGRESSOR, TaskType.REGRESSION, X_tr, y_tr)
        assert isinstance(pipeline, Pipeline)

    def test_random_forest_classifier_trains(self):
        X, y = make_classification_data()
        X_tr, X_te, y_tr, y_te = self._split(X, y)
        pipeline, _ = self.trainer.train(ModelType.RANDOM_FOREST_CLASSIFIER, TaskType.CLASSIFICATION, X_tr, y_tr)
        assert isinstance(pipeline, Pipeline)

    def test_training_is_reproducible(self):
        X, y = make_regression_data()
        X_tr, X_te, y_tr, y_te = self._split(X, y)
        p1, _ = self.trainer.train(ModelType.RIDGE_REGRESSION, TaskType.REGRESSION, X_tr, y_tr)
        p2, _ = self.trainer.train(ModelType.RIDGE_REGRESSION, TaskType.REGRESSION, X_tr, y_tr)
        pred1 = p1.predict(X_te)
        pred2 = p2.predict(X_te)
        np.testing.assert_array_almost_equal(pred1, pred2)

class TestMetricComputation:
    def test_regression_metrics_computed(self):
        X, y = make_regression_data()
        X_tr, X_te, y_tr, y_te = X[:80], X[80:], y[:80], y[80:]
        trainer = ModelTrainer(tempfile.mkdtemp())
        pipeline, _ = trainer.train(ModelType.RIDGE_REGRESSION, TaskType.REGRESSION, X_tr, y_tr)
        evaluator = RegressionEvaluator()
        result = evaluator.evaluate(pipeline, X_tr, X_te, y_tr, y_te)
        metric_names = [m["metric_name"] for m in result["metrics"]]
        assert "mae" in metric_names
        assert "rmse" in metric_names
        assert "r2" in metric_names

    def test_classification_metrics_computed(self):
        X, y = make_classification_data()
        X_tr, X_te, y_tr, y_te = X[:80], X[80:], y[:80], y[80:]
        trainer = ModelTrainer(tempfile.mkdtemp())
        pipeline, _ = trainer.train(ModelType.RANDOM_FOREST_CLASSIFIER, TaskType.CLASSIFICATION, X_tr, y_tr)
        evaluator = ClassificationEvaluator()
        result = evaluator.evaluate(pipeline, X_tr, X_te, y_tr, y_te)
        metric_names = [m["metric_name"] for m in result["metrics"]]
        assert "accuracy" in metric_names
        assert "f1_macro" in metric_names
