"""
ML preprocessing pipeline for MatEnergy-ML.
Handles: imputation, scaling, constant feature removal, leakage detection, train/test split.
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import VarianceThreshold
from typing import Optional

from app.core.constants import FIXED_RANDOM_SEED, MIN_TRAINING_SAMPLES
from app.core.exceptions import (
    InsufficientDataError, TargetLeakageError, FeatureMatrixError
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def remove_constant_features(X: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Remove features with zero variance."""
    selector = VarianceThreshold(threshold=0.0)
    selector.fit(X)
    kept = X.columns[selector.get_support()].tolist()
    removed = [c for c in X.columns if c not in kept]
    if removed:
        logger.info("removed_constant_features", count=len(removed), features=removed[:10])
    return X[kept], removed


def check_for_leakage(feature_names: list[str], target: str) -> None:
    """Detect obvious target leakage (target column in features)."""
    suspicious = [f for f in feature_names if target.lower() in f.lower() and f != target]
    if suspicious:
        raise TargetLeakageError(
            code="TARGET_LEAKAGE",
            message=f"Potential target leakage detected in features",
            detail=f"Feature names containing target '{target}': {suspicious}",
            recommended_action="Remove features derived from the target variable before training"
        )


def check_for_duplicates_before_split(X: pd.DataFrame, y: pd.Series) -> int:
    """Return count of duplicate rows."""
    combined = pd.concat([X, y.rename("_target_")], axis=1)
    dups = combined.duplicated().sum()
    if dups > 0:
        logger.warning("duplicate_samples_detected", count=int(dups))
    return int(dups)


def validate_dataset_for_training(X: pd.DataFrame, y: pd.Series, min_samples: int = MIN_TRAINING_SAMPLES) -> None:
    if len(X) < min_samples:
        raise InsufficientDataError(
            code="INSUFFICIENT_DATA",
            message=f"Dataset has only {len(X)} samples, minimum required is {min_samples}",
            detail=f"n_samples={len(X)}, min_required={min_samples}",
            recommended_action="Provide a dataset with more materials"
        )
    null_frac = y.isnull().mean()
    if null_frac > 0.3:
        raise FeatureMatrixError(
            code="HIGH_TARGET_NULL_FRACTION",
            message=f"Target variable has {null_frac:.1%} missing values",
            detail=f"null_fraction={null_frac}",
            recommended_action="Clean the dataset or choose a different target property"
        )
    if X.shape[1] == 0:
        raise FeatureMatrixError(
            code="EMPTY_FEATURE_MATRIX",
            message="Feature matrix has no columns",
            detail="X.shape[1] == 0",
            recommended_action="Generate descriptors before training"
        )


def build_sklearn_pipeline(task_type: str, scale: bool = True) -> Pipeline:
    """Build a reproducible sklearn preprocessing pipeline."""
    steps = [
        ("imputer", SimpleImputer(strategy="median")),
    ]
    if scale:
        steps.append(("scaler", RobustScaler()))
    return Pipeline(steps)


def prepare_train_test(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.2,
    random_seed: int = FIXED_RANDOM_SEED,
    stratify: Optional[pd.Series] = None,
) -> tuple:
    """Split data into train/test with fixed seed."""
    check_for_duplicates_before_split(X, y)
    validate_dataset_for_training(X, y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=test_size,
        random_state=random_seed,
        stratify=stratify,
    )
    return X_train, X_test, y_train, y_test
