"""
Prediction service for MatEnergy-ML.
Handles single and batch predictions with out-of-domain detection.
"""
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from typing import Optional

from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Threshold for out-of-domain detection (normalized Mahalanobis-inspired heuristic)
OOD_PERCENTILE_THRESHOLD = 0.95


class Predictor:
    def __init__(
        self,
        pipeline: Pipeline,
        feature_names: list[str],
        training_X: Optional[pd.DataFrame] = None,
    ):
        self.pipeline = pipeline
        self.feature_names = feature_names
        self._training_stats: Optional[dict] = None
        if training_X is not None:
            self._fit_domain_stats(training_X)

    def _fit_domain_stats(self, X_train: pd.DataFrame) -> None:
        """Compute training domain statistics for OOD detection."""
        self._training_stats = {
            "mean": X_train.mean().to_dict(),
            "std": X_train.std().to_dict(),
            "min": X_train.min().to_dict(),
            "max": X_train.max().to_dict(),
        }

    def _is_out_of_domain(self, x: pd.Series) -> tuple[bool, str]:
        """Simple range-based OOD check against training distribution."""
        if self._training_stats is None:
            return False, ""

        violations = []
        for feat in self.feature_names:
            if feat not in self._training_stats["mean"]:
                continue
            val = x.get(feat, 0.0)
            mean = self._training_stats["mean"][feat]
            std = self._training_stats["std"].get(feat, 0.0)
            if std > 0 and abs(val - mean) > 3 * std:
                violations.append(feat)

        if len(violations) > max(1, len(self.feature_names) * 0.1):
            return True, f"Features outside training distribution: {violations[:5]}"
        return False, ""

    def predict(self, X: pd.DataFrame) -> list[dict]:
        """Predict for a batch. Returns list of prediction dicts."""
        results: list[dict] = []
        for idx, row in X.iterrows():
            row_df = pd.DataFrame([row])
            try:
                pred = self.pipeline.predict(row_df)[0]
            except Exception as e:
                results.append({"index": idx, "error": str(e)})
                continue

            ood, ood_reason = self._is_out_of_domain(row)

            result: dict = {
                "index": idx,
                "predicted_value": float(pred) if np.isscalar(pred) else None,
                "is_out_of_domain": ood,
                "out_of_domain_reason": ood_reason if ood else None,
                "is_calibrated": False,
            }

            # Uncertainty via std of tree estimators if available
            model = self.pipeline.named_steps.get("model")
            if hasattr(model, "estimators_"):
                try:
                    preprocessor = self.pipeline.named_steps["preprocessor"]
                    transformed = preprocessor.transform(row_df)
                    preds = np.array([
                        est.predict(transformed)[0] for est in model.estimators_
                    ])
                    result["uncertainty"] = float(preds.std())
                except Exception:
                    pass

            results.append(result)
        return results

    def predict_single(self, x_df: pd.DataFrame) -> dict:
        """Predict for a single-row DataFrame. Returns one result dict."""
        results = self.predict(x_df)
        return results[0] if results else {"error": "no_prediction"}

    def predict_proba(self, X: pd.DataFrame) -> list[dict]:
        """Classification probability predictions."""
        results: list[dict] = []
        for idx, row in X.iterrows():
            row_df = pd.DataFrame([row])
            try:
                if hasattr(self.pipeline, "predict_proba"):
                    proba = self.pipeline.predict_proba(row_df)[0]
                    cls = self.pipeline.predict(row_df)[0]
                    ood, ood_reason = self._is_out_of_domain(row)
                    results.append({
                        "index": idx,
                        "predicted_class": str(cls),
                        "confidence_score": float(max(proba)),
                        "is_out_of_domain": ood,
                        "out_of_domain_reason": ood_reason if ood else None,
                        "is_calibrated": False,
                    })
            except Exception as e:
                results.append({"index": idx, "error": str(e)})
        return results
