"""
TrainModelUseCase
=================
Orchestrates the full ML training pipeline:

    dataset descriptors → feature matrix → preprocessing →
    train → evaluate → register artifact in DB.

Steps
-----
1.  Fetch ``DescriptorVector`` rows for the dataset + descriptor set.
2.  Fetch matching target-property values from ``MaterialProperty``.
3.  Build X (DataFrame) and y (Series).
4.  Run leakage check and constant-feature removal.
5.  Train/test split.
6.  Create ``ModelVersion`` and ``ModelTrainingRun`` DB records.
7.  Train via ``ModelTrainer``.
8.  Evaluate via ``RegressionEvaluator`` or ``ClassificationEvaluator``.
9.  Persist artifact + hash, ``ModelArtifact``, ``ModelMetric`` rows.
10. Mark training run ``completed`` (or ``failed`` on error).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import FIXED_RANDOM_SEED, ModelType, TaskType
from app.core.logging_config import get_logger
from app.infrastructure.database.models.model_models import (
    ModelArtifact,
    ModelMetric,
    ModelTrainingRun,
    ModelVersion,
)
from app.infrastructure.database.repositories import (
    DescriptorSetRepository,
    DescriptorVectorRepository,
    MaterialRepository,
    ModelTrainingRunRepository,
    ModelVersionRepository,
)
from app.infrastructure.database.repositories.material_repository import (
    MaterialPropertyRepository,
)
from app.infrastructure.ml.evaluators import (
    ClassificationEvaluator,
    RegressionEvaluator,
)
from app.infrastructure.ml.preprocessing import (
    check_for_leakage,
    prepare_train_test,
    remove_constant_features,
)
from app.infrastructure.ml.trainers import ModelTrainer

logger = get_logger(__name__)


class TrainModelUseCase:
    """
    Full end-to-end ML training pipeline.

    Args:
        db: Active SQLAlchemy ``Session``.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.trainer = ModelTrainer(settings.ARTIFACT_STORAGE_PATH)

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def execute(
        self,
        model_type: ModelType,
        task_type: TaskType,
        target_property: str,
        dataset_id: uuid.UUID,
        descriptor_set_id: uuid.UUID,
        user_id: uuid.UUID,
        hyperparameters: Optional[dict] = None,
        test_size: float = 0.2,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Train a model and register everything in the database.

        Args:
            model_type:        One of the ``ModelType`` enum values.
            task_type:         ``REGRESSION`` or ``CLASSIFICATION``.
            target_property:   Name of the ``MaterialProperty`` to predict.
            dataset_id:        Source dataset.
            descriptor_set_id: Pre-computed descriptor set to use as features.
            user_id:           Requesting user — stored on created records.
            hyperparameters:   Optional overrides for estimator defaults.
            test_size:         Fraction of data held out for evaluation.
            name:              Human-readable model name (auto-generated if None).
            description:       Optional free-text description.

        Returns:
            {
                "model_version_id"  : str,
                "training_run_id"   : str,
                "status"            : "completed",
                "metrics"           : list[dict],
                "artifact_path"     : str,
                "sha256"            : str,
                "n_train_samples"   : int,
                "n_test_samples"    : int,
                "n_features"        : int,
            }

        Raises:
            ValueError:           No descriptor vectors or no matching target values.
            ModelTrainingError:   Training fails.
            ModelEvaluationError: Evaluation fails.
            ModelPersistenceError: Artifact cannot be saved.
        """
        # ---- Build feature matrix ----------------------------------------
        vec_repo = DescriptorVectorRepository(self.db)
        mat_repo = MaterialRepository(self.db)
        prop_repo = MaterialPropertyRepository(self.db)
        ds_repo = DescriptorSetRepository(self.db)

        vectors = vec_repo.get_all_for_dataset(dataset_id, descriptor_set_id)
        if not vectors:
            raise ValueError(
                "No descriptor vectors found for this dataset / descriptor set. "
                "Run GenerateDescriptorsUseCase first."
            )

        desc_set = ds_repo.get_by_id(descriptor_set_id)
        feature_names: list[str] = (
            desc_set.feature_names if desc_set and desc_set.feature_names else []
        )

        X_rows: list[list[float]] = []
        y_values: list[float] = []
        mat_ids: list[uuid.UUID] = []

        for vec in vectors:
            prop = prop_repo.get_by_material_and_property(
                vec.material_id, target_property
            )
            if prop is None:
                continue  # skip materials without the target property

            if task_type == TaskType.REGRESSION:
                if prop.value_float is None:
                    continue
                target_val: float = prop.value_float
            else:
                # Classification: try bool first, then float rounded to int
                if prop.value_bool is not None:
                    target_val = 1.0 if prop.value_bool else 0.0
                elif prop.value_float is not None:
                    target_val = float(int(round(prop.value_float)))
                else:
                    continue

            raw_vector = vec.vector
            # vector may be stored as a JSON list or dict
            if isinstance(raw_vector, dict):
                raw_vector = list(raw_vector.values())

            X_rows.append(raw_vector)
            y_values.append(target_val)
            mat_ids.append(vec.material_id)

        if not X_rows:
            raise ValueError(
                f"No materials with target property '{target_property}' found "
                "in this dataset. Check that the property was imported."
            )

        # Infer column names — fall back to positional names if not stored
        n_features = len(X_rows[0])
        if feature_names and len(feature_names) >= n_features:
            cols = feature_names[:n_features]
        else:
            cols = [f"feat_{i}" for i in range(n_features)]

        X = pd.DataFrame(X_rows, columns=cols)
        y = pd.Series(y_values, name=target_property)

        # ---- Leakage check + constant features ---------------------------
        check_for_leakage(list(X.columns), target_property)
        X, removed_features = remove_constant_features(X)
        if removed_features:
            logger.info(
                "constant_features_removed",
                count=len(removed_features),
                sample=removed_features[:5],
            )

        # ---- Train/test split --------------------------------------------
        stratify = y if task_type == TaskType.CLASSIFICATION else None
        X_train, X_test, y_train, y_test = prepare_train_test(
            X, y, test_size=test_size, stratify=stratify
        )

        # ---- Create ModelVersion -----------------------------------------
        model_name = name or f"{model_type.value}_{target_property}"
        version_tag = f"v{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}"

        mv = ModelVersion(
            id=uuid.uuid4(),
            name=model_name,
            model_type=model_type.value,
            task_type=task_type.value,
            target_property=target_property,
            descriptor_set_id=descriptor_set_id,
            dataset_id=dataset_id,
            is_active=False,
            created_by=user_id,
            description=description,
            version_tag=version_tag,
        )
        self.db.add(mv)
        self.db.flush()

        # ---- Create ModelTrainingRun (status=running) --------------------
        run = ModelTrainingRun(
            id=uuid.uuid4(),
            model_version_id=mv.id,
            dataset_id=dataset_id,
            descriptor_set_id=descriptor_set_id,
            status="running",
            started_at=datetime.now(tz=timezone.utc),
            n_train_samples=len(X_train),
            n_test_samples=len(X_test),
            n_features=X_train.shape[1],
            random_seed=FIXED_RANDOM_SEED,
            hyperparameters=hyperparameters or {},
            triggered_by=user_id,
        )
        self.db.add(run)
        self.db.flush()

        # ---- Train + evaluate + persist ----------------------------------
        try:
            pipeline, train_info = self.trainer.train(
                model_type=model_type,
                task_type=task_type,
                X_train=X_train,
                y_train=y_train,
                hyperparams=hyperparameters,
            )

            if task_type == TaskType.REGRESSION:
                evaluator = RegressionEvaluator()
            else:
                evaluator = ClassificationEvaluator()

            eval_result = evaluator.evaluate(
                pipeline, X_train, X_test, y_train, y_test
            )

            # Persist artifact
            artifact_path, sha256 = self.trainer.save_artifact(pipeline, model_name)
            artifact_file_size = Path(artifact_path).stat().st_size

            self.db.add(
                ModelArtifact(
                    id=uuid.uuid4(),
                    model_version_id=mv.id,
                    file_path=artifact_path,
                    sha256_hash=sha256,
                    file_size_bytes=artifact_file_size,
                    artifact_type="sklearn_joblib",
                    serialization_format="joblib",
                    python_version="3.12",
                )
            )

            # Persist metrics
            for m in eval_result["metrics"]:
                self.db.add(
                    ModelMetric(
                        id=uuid.uuid4(),
                        training_run_id=run.id,
                        split=m["split"],
                        metric_name=m["metric_name"],
                        metric_value=float(m["metric_value"]),
                    )
                )

            # Persist feature importances
            from app.infrastructure.database.models.model_models import ModelParameter
            if task_type == TaskType.REGRESSION:
                _evaluator_for_fi = RegressionEvaluator()
            else:
                _evaluator_for_fi = ClassificationEvaluator()  # type: ignore[assignment]
            if hasattr(_evaluator_for_fi, "get_feature_importances"):
                fi = _evaluator_for_fi.get_feature_importances(pipeline, list(X_train.columns))
                if fi:
                    self.db.add(ModelParameter(
                        id=uuid.uuid4(),
                        model_version_id=mv.id,
                        parameter_name="feature_importances",
                        parameter_value=fi,
                    ))

            # Persist parity data (y_test vs y_pred) for regression
            parity = eval_result.get("predictions")
            if parity and isinstance(parity.get("y_test"), list):
                self.db.add(ModelParameter(
                    id=uuid.uuid4(),
                    model_version_id=mv.id,
                    parameter_name="parity_data",
                    parameter_value=parity,
                ))

            # Persist SHAP background sample (50 rows of X_train, scaled)
            try:
                import numpy as _np
                preprocessor_step = pipeline.named_steps.get("preprocessor")
                if preprocessor_step is not None:
                    sample_idx = _np.random.default_rng(42).choice(
                        len(X_train), size=min(50, len(X_train)), replace=False
                    )
                    X_sample = X_train.iloc[sample_idx]
                    X_scaled = preprocessor_step.transform(X_sample)
                    self.db.add(ModelParameter(
                        id=uuid.uuid4(),
                        model_version_id=mv.id,
                        parameter_name="shap_background_sample",
                        parameter_value={
                            "data": X_scaled.tolist() if hasattr(X_scaled, "tolist") else X_scaled,
                            "feature_names": list(X_train.columns),
                        },
                    ))
            except Exception:
                pass  # SHAP background is best-effort

            # Complete run
            run.status = "completed"
            run.completed_at = datetime.now(tz=timezone.utc)
            run.duration_seconds = train_info["duration_seconds"]
            self.db.commit()

            logger.info(
                "train_model_completed",
                model_version_id=str(mv.id),
                training_run_id=str(run.id),
                model_type=model_type.value,
                target_property=target_property,
                n_train=len(X_train),
                n_test=len(X_test),
                duration_s=train_info["duration_seconds"],
            )

            return {
                "model_version_id": str(mv.id),
                "training_run_id": str(run.id),
                "status": "completed",
                "metrics": eval_result["metrics"],
                "artifact_path": artifact_path,
                "sha256": sha256,
                "n_train_samples": len(X_train),
                "n_test_samples": len(X_test),
                "n_features": X_train.shape[1],
            }

        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc)
            self.db.commit()
            logger.error(
                "train_model_failed",
                model_version_id=str(mv.id),
                error=str(exc),
            )
            raise
