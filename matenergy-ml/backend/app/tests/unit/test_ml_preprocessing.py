"""Tests for ML preprocessing pipeline."""
import numpy as np
import pandas as pd
import pytest
from app.infrastructure.ml.preprocessing import (
    remove_constant_features, check_for_leakage, validate_dataset_for_training,
    prepare_train_test
)
from app.core.exceptions import InsufficientDataError, TargetLeakageError, FeatureMatrixError
from app.core.constants import FIXED_RANDOM_SEED

class TestConstantFeatureRemoval:
    def test_removes_constant_column(self):
        X = pd.DataFrame({"a": [1, 2, 3], "b": [5, 5, 5]})
        X_clean, removed = remove_constant_features(X)
        assert "b" in removed
        assert "a" in X_clean.columns

    def test_keeps_all_varying_columns(self):
        X = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        X_clean, removed = remove_constant_features(X)
        assert removed == []
        assert X_clean.shape[1] == 2

class TestLeakageDetection:
    def test_detects_target_in_feature_name(self):
        with pytest.raises(TargetLeakageError):
            check_for_leakage(["energy_above_hull_derived", "atomic_mass"], "energy_above_hull")

    def test_no_leakage_clean_features(self):
        check_for_leakage(["atomic_mass", "electronegativity", "n_elements"], "energy_above_hull")

class TestDatasetValidation:
    def test_raises_on_insufficient_data(self):
        X = pd.DataFrame({"a": range(5)})
        y = pd.Series(range(5))
        with pytest.raises(InsufficientDataError):
            validate_dataset_for_training(X, y, min_samples=20)

    def test_raises_on_empty_features(self):
        X = pd.DataFrame()
        y = pd.Series(range(30))
        with pytest.raises(FeatureMatrixError):
            validate_dataset_for_training(X, y)

    def test_raises_on_high_null_fraction(self):
        X = pd.DataFrame({"a": range(50)})
        y = pd.Series([None] * 40 + list(range(10)))
        with pytest.raises(FeatureMatrixError):
            validate_dataset_for_training(X, y)

class TestTrainTestSplit:
    def test_split_is_reproducible(self):
        X = pd.DataFrame({"a": range(100), "b": range(100)})
        y = pd.Series(range(100))
        X_tr1, X_te1, y_tr1, y_te1 = prepare_train_test(X, y, random_seed=FIXED_RANDOM_SEED)
        X_tr2, X_te2, y_tr2, y_te2 = prepare_train_test(X, y, random_seed=FIXED_RANDOM_SEED)
        assert list(y_tr1) == list(y_tr2)

    def test_split_sizes_correct(self):
        X = pd.DataFrame({"a": range(100)})
        y = pd.Series(range(100))
        X_tr, X_te, y_tr, y_te = prepare_train_test(X, y, test_size=0.2)
        assert len(X_te) == 20
        assert len(X_tr) == 80
