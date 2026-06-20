"""
ML model evaluation for MatEnergy-ML.
Computes regression and classification metrics with cross-validation.
"""
import numpy as np
import pandas as pd
from typing import Optional, Any
from sklearn.pipeline import Pipeline
from sklearn.model_selection import cross_val_score, StratifiedKFold, KFold
from sklearn.metrics import (
    mean_absolute_error, mean_squared_error, r2_score,
    median_absolute_error, accuracy_score, precision_score,
    recall_score, f1_score, roc_auc_score, balanced_accuracy_score,
    confusion_matrix, average_precision_score
)
from app.core.constants import TaskType, FIXED_RANDOM_SEED
from app.core.exceptions import ModelEvaluationError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class RegressionEvaluator:
    def evaluate(
        self,
        pipeline: Pipeline,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series,
        n_cv_folds: int = 5,
    ) -> dict:
        try:
            train_pred = pipeline.predict(X_train)
            test_pred = pipeline.predict(X_test)

            train_metrics = self._compute_metrics(y_train.values, train_pred, split="train")
            test_metrics = self._compute_metrics(y_test.values, test_pred, split="test")

            cv_scores = cross_val_score(
                pipeline, pd.concat([X_train, X_test]), pd.concat([y_train, y_test]),
                cv=KFold(n_splits=n_cv_folds, shuffle=True, random_state=FIXED_RANDOM_SEED),
                scoring="neg_mean_absolute_error",
            )
            cv_metrics = {
                "split": "cv",
                "metric_name": "mae_cv_mean",
                "metric_value": float(-cv_scores.mean()),
            }

            all_metrics = train_metrics + test_metrics + [cv_metrics]
            logger.info("regression_evaluation_complete", test_mae=test_metrics[0]["metric_value"])
            return {
                "metrics": all_metrics,
                "predictions": {"y_test": y_test.tolist(), "y_pred": test_pred.tolist()},
            }
        except Exception as e:
            raise ModelEvaluationError(
                code="EVALUATION_FAILED",
                message="Model evaluation failed",
                detail=str(e),
                recommended_action="Check the test data"
            ) from e

    def _compute_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, split: str) -> list[dict]:
        metrics = []

        def add(name: str, val: float) -> None:
            metrics.append({"split": split, "metric_name": name, "metric_value": float(val)})

        add("mae", mean_absolute_error(y_true, y_pred))
        add("rmse", float(np.sqrt(mean_squared_error(y_true, y_pred))))
        add("r2", r2_score(y_true, y_pred))
        add("median_ae", median_absolute_error(y_true, y_pred))
        if np.all(y_true != 0):
            add("mape", float(np.mean(np.abs((y_true - y_pred) / y_true)) * 100))
        return metrics

    def get_feature_importances(self, pipeline: Pipeline, feature_names: list[str]) -> list[dict]:
        model = pipeline.named_steps.get("model")
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            return sorted(
                [{"feature": n, "importance": float(v)} for n, v in zip(feature_names, importances)],
                key=lambda x: x["importance"],
                reverse=True,
            )
        if hasattr(model, "coef_"):
            coefs = np.abs(model.coef_).flatten()[: len(feature_names)]
            return sorted(
                [{"feature": n, "importance": float(v)} for n, v in zip(feature_names, coefs)],
                key=lambda x: x["importance"],
                reverse=True,
            )
        return []


class ClassificationEvaluator:
    def evaluate(
        self,
        pipeline: Pipeline,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        y_train: pd.Series,
        y_test: pd.Series,
        n_cv_folds: int = 5,
    ) -> dict:
        try:
            test_pred = pipeline.predict(X_test)
            train_pred = pipeline.predict(X_train)

            train_metrics = self._compute_metrics(y_train.values, train_pred, split="train")
            test_metrics = self._compute_metrics(y_test.values, test_pred, split="test")

            # Attempt ROC-AUC with probabilities
            extra: list[dict] = []
            if hasattr(pipeline, "predict_proba"):
                try:
                    proba = pipeline.predict_proba(X_test)[:, 1]
                    extra.append({
                        "split": "test",
                        "metric_name": "roc_auc",
                        "metric_value": float(roc_auc_score(y_test, proba)),
                    })
                    extra.append({
                        "split": "test",
                        "metric_name": "pr_auc",
                        "metric_value": float(average_precision_score(y_test, proba)),
                    })
                except Exception:
                    pass

            all_metrics = train_metrics + test_metrics + extra
            return {
                "metrics": all_metrics,
                "confusion_matrix": confusion_matrix(y_test, test_pred).tolist(),
            }
        except Exception as e:
            raise ModelEvaluationError(
                code="CLASSIFICATION_EVAL_FAILED",
                message="Classification evaluation failed",
                detail=str(e),
                recommended_action="Check the test data and class labels"
            ) from e

    def _compute_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, split: str) -> list[dict]:
        metrics: list[dict] = []

        def add(name: str, val: float) -> None:
            metrics.append({"split": split, "metric_name": name, "metric_value": float(val)})

        add("accuracy", accuracy_score(y_true, y_pred))
        add("balanced_accuracy", balanced_accuracy_score(y_true, y_pred))
        add("f1_macro", f1_score(y_true, y_pred, average="macro", zero_division=0))
        add("precision_macro", precision_score(y_true, y_pred, average="macro", zero_division=0))
        add("recall_macro", recall_score(y_true, y_pred, average="macro", zero_division=0))
        return metrics
