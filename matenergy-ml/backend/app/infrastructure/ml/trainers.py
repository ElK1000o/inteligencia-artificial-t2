"""
ML model trainers for MatEnergy-ML.
Implements Ridge, RF, GBM, MLP for regression and classification.
"""
import numpy as np
import pandas as pd
import joblib
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.ensemble import (
    RandomForestRegressor, RandomForestClassifier,
    GradientBoostingRegressor, GradientBoostingClassifier
)
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.svm import SVR, SVC
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.pipeline import Pipeline

from app.core.constants import ModelType, TaskType, FIXED_RANDOM_SEED
from app.core.exceptions import (
    ModelTrainingError, UnsupportedModelTypeError, ModelPersistenceError,
    ArtifactIntegrityError, FeatureMatrixError
)
from app.infrastructure.ml.preprocessing import build_sklearn_pipeline, prepare_train_test
from app.core.logging_config import get_logger

logger = get_logger(__name__)

REGRESSOR_DEFAULTS: dict[ModelType, dict] = {
    ModelType.RIDGE_REGRESSION: {
        "alpha": 1.0, "random_state": FIXED_RANDOM_SEED
    },
    ModelType.RANDOM_FOREST_REGRESSOR: {
        "n_estimators": 200, "max_depth": None, "min_samples_leaf": 2,
        "n_jobs": -1, "random_state": FIXED_RANDOM_SEED
    },
    ModelType.GRADIENT_BOOSTING_REGRESSOR: {
        "n_estimators": 200, "learning_rate": 0.05, "max_depth": 4,
        "subsample": 0.8, "random_state": FIXED_RANDOM_SEED
    },
    ModelType.MLP_REGRESSOR: {
        "hidden_layer_sizes": (128, 64, 32), "activation": "relu",
        "max_iter": 500, "random_state": FIXED_RANDOM_SEED, "early_stopping": True
    },
    ModelType.SVR: {
        "kernel": "rbf", "C": 10.0, "epsilon": 0.1
    },
    ModelType.GAUSSIAN_PROCESS_REGRESSOR: {
        "n_restarts_optimizer": 3, "random_state": FIXED_RANDOM_SEED
    },
}

CLASSIFIER_DEFAULTS: dict[ModelType, dict] = {
    ModelType.LOGISTIC_REGRESSION: {
        "max_iter": 1000, "random_state": FIXED_RANDOM_SEED, "class_weight": "balanced"
    },
    ModelType.RANDOM_FOREST_CLASSIFIER: {
        "n_estimators": 200, "max_depth": None, "min_samples_leaf": 2,
        "n_jobs": -1, "random_state": FIXED_RANDOM_SEED, "class_weight": "balanced"
    },
    ModelType.GRADIENT_BOOSTING_CLASSIFIER: {
        "n_estimators": 200, "learning_rate": 0.05, "max_depth": 4,
        "subsample": 0.8, "random_state": FIXED_RANDOM_SEED
    },
    ModelType.MLP_CLASSIFIER: {
        "hidden_layer_sizes": (128, 64, 32), "activation": "relu",
        "max_iter": 500, "random_state": FIXED_RANDOM_SEED, "early_stopping": True
    },
}


def _build_estimator(model_type: ModelType, task_type: TaskType, hyperparams: dict) -> Any:
    if task_type == TaskType.REGRESSION:
        cls_map = {
            ModelType.RIDGE_REGRESSION: Ridge,
            ModelType.RANDOM_FOREST_REGRESSOR: RandomForestRegressor,
            ModelType.GRADIENT_BOOSTING_REGRESSOR: GradientBoostingRegressor,
            ModelType.MLP_REGRESSOR: MLPRegressor,
            ModelType.SVR: SVR,
            ModelType.GAUSSIAN_PROCESS_REGRESSOR: GaussianProcessRegressor,
        }
    else:
        cls_map = {
            ModelType.LOGISTIC_REGRESSION: LogisticRegression,
            ModelType.RANDOM_FOREST_CLASSIFIER: RandomForestClassifier,
            ModelType.GRADIENT_BOOSTING_CLASSIFIER: GradientBoostingClassifier,
            ModelType.MLP_CLASSIFIER: MLPClassifier,
        }
    if model_type not in cls_map:
        raise UnsupportedModelTypeError(
            code="UNSUPPORTED_MODEL",
            message=f"Model type {model_type} is not supported for {task_type}",
            detail=f"Available: {list(cls_map.keys())}",
            recommended_action="Choose a supported model type"
        )
    return cls_map[model_type](**hyperparams)


class ModelTrainer:
    """Trains a sklearn model and wraps it in a preprocessing pipeline."""

    def __init__(self, artifact_storage_path: str):
        self.artifact_storage_path = Path(artifact_storage_path)
        self.artifact_storage_path.mkdir(parents=True, exist_ok=True)

    def train(
        self,
        model_type: ModelType,
        task_type: TaskType,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        hyperparams: Optional[dict] = None,
        scale: bool = True,
    ) -> tuple[Pipeline, dict]:
        """
        Train a full sklearn Pipeline (preprocessor + estimator).
        Returns (fitted_pipeline, training_info_dict).
        """
        defaults = (
            REGRESSOR_DEFAULTS if task_type == TaskType.REGRESSION else CLASSIFIER_DEFAULTS
        ).get(model_type, {})
        params = {**defaults, **(hyperparams or {})}

        try:
            estimator = _build_estimator(model_type, task_type, params)
            preprocessor = build_sklearn_pipeline(task_type.value, scale=scale)

            full_pipeline = Pipeline([
                ("preprocessor", preprocessor),
                ("model", estimator),
            ])

            t0 = datetime.now(tz=timezone.utc)
            full_pipeline.fit(X_train, y_train)
            t1 = datetime.now(tz=timezone.utc)
            duration = (t1 - t0).total_seconds()

            logger.info(
                "model_trained",
                model_type=model_type.value,
                n_samples=len(X_train),
                duration_s=duration,
            )

            return full_pipeline, {
                "model_type": model_type.value,
                "task_type": task_type.value,
                "n_train_samples": len(X_train),
                "n_features": X_train.shape[1],
                "hyperparameters": params,
                "duration_seconds": duration,
                "random_seed": FIXED_RANDOM_SEED,
            }

        except (UnsupportedModelTypeError, FeatureMatrixError):
            raise
        except Exception as e:
            raise ModelTrainingError(
                code="TRAINING_FAILED",
                message="Model training failed",
                detail=str(e),
                recommended_action="Check the training data and hyperparameters"
            ) from e

    def save_artifact(self, pipeline: Pipeline, model_name: str) -> tuple[str, str]:
        """
        Save model artifact to disk. Returns (file_path, sha256_hash).
        NEVER overwrite existing artifacts — use UUID-based filenames.
        """
        artifact_id = str(uuid4())
        filename = f"{model_name}_{artifact_id}.joblib"
        filepath = self.artifact_storage_path / "models" / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        try:
            joblib.dump(pipeline, filepath, compress=3)
        except Exception as e:
            raise ModelPersistenceError(
                code="ARTIFACT_SAVE_FAILED",
                message="Failed to save model artifact",
                detail=str(e),
                recommended_action="Check disk space and permissions"
            ) from e

        sha256 = self._hash_file(filepath)
        logger.info("artifact_saved", path=str(filepath), sha256=sha256[:12])
        return str(filepath), sha256

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def load_artifact(self, file_path: str, expected_hash: str) -> Pipeline:
        """
        Load model artifact after verifying SHA-256 integrity.
        NEVER load if hash doesn't match — security control against tampering.
        """
        path = Path(file_path)
        if not path.exists():
            raise ArtifactIntegrityError(
                code="ARTIFACT_NOT_FOUND",
                message="Model artifact file not found",
                detail=f"path={file_path}",
                recommended_action="Retrain the model or restore from backup"
            )
        actual_hash = self._hash_file(path)
        if actual_hash != expected_hash:
            raise ArtifactIntegrityError(
                code="ARTIFACT_HASH_MISMATCH",
                message="Model artifact integrity check failed",
                detail=f"expected={expected_hash[:12]}..., got={actual_hash[:12]}...",
                recommended_action="The artifact may have been tampered with. Retrain the model."
            )
        try:
            pipeline = joblib.load(path)
        except Exception as e:
            raise ModelPersistenceError(
                code="ARTIFACT_LOAD_FAILED",
                message="Failed to load model artifact",
                detail=str(e),
                recommended_action="The artifact may be corrupted. Retrain the model."
            ) from e
        return pipeline
