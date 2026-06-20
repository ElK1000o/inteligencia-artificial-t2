"""
EvaluateModelUseCase
====================
Loads a verified model artifact and re-evaluates it against a test split
derived from the same descriptor vectors used during training.

Use this to:
  - Compute fresh metrics after model activation.
  - Validate a model on a new dataset (transfer evaluation).
  - Regenerate metrics if the original training run record was lost.

Steps
-----
1.  Verify artifact integrity (SHA-256 check).
2.  Load the sklearn Pipeline via joblib.
3.  Reconstruct X / y from DescriptorVectors + MaterialProperties.
4.  Run the appropriate evaluator (regression / classification).
5.  Persist new ModelMetric rows tagged with split='eval_holdout'.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import FIXED_RANDOM_SEED, TaskType
from app.core.exceptions import (
    ArtifactIntegrityError,
    ModelEvaluationError,
    NotFoundError,
)
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
    ModelVersionRepository,
)
from app.infrastructure.database.repositories.material_repository import (
    MaterialPropertyRepository,
)
from app.infrastructure.ml.evaluators import ClassificationEvaluator, RegressionEvaluator
from app.infrastructure.ml.preprocessing import prepare_train_test
from app.application.use_cases.verify_model_artifact_use_case import (
    VerifyModelArtifactUseCase,
)

logger = get_logger(__name__)


class EvaluateModelUseCase:
    """
    Re-evaluates a trained model and persists new metrics.

    Args:
        db: Active SQLAlchemy Session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(
        self,
        model_version_id: uuid.UUID,
        dataset_id: Optional[uuid.UUID] = None,
        test_size: float = 0.2,
    ) -> dict:
        """
        Evaluate *model_version_id*.

        Args:
            model_version_id: Model to evaluate.
            dataset_id:       Override dataset (uses model's training dataset if None).
            test_size:        Test fraction for the re-split.

        Returns
        -------
        {
            "model_version_id": str,
            "task_type"       : str,
            "target_property" : str,
            "n_samples"       : int,
            "metrics"         : list[dict],
        }
        """
        # ---- Resolve model version ----------------------------------------
        mv_repo = ModelVersionRepository(self.db)
        mv: ModelVersion | None = mv_repo.get_by_id(model_version_id)
        if mv is None:
            raise NotFoundError(
                code="MODEL_VERSION_NOT_FOUND",
                message=f"No se encontró la versión de modelo {model_version_id}",
                recommended_action="Verifique el model_version_id",
            )

        effective_dataset_id = dataset_id or mv.dataset_id
        if effective_dataset_id is None:
            raise ModelEvaluationError(
                code="NO_DATASET",
                message="No hay un dataset asociado a esta versión de modelo",
                recommended_action="Proporcione un dataset_id explícitamente",
            )

        # ---- Verify and load artifact -------------------------------------
        verifier = VerifyModelArtifactUseCase(self.db)
        verifier.execute(model_version_id)  # raises ArtifactIntegrityError on failure

        artifact_stmt = (
            select(ModelArtifact)
            .where(ModelArtifact.model_version_id == model_version_id)
            .order_by(ModelArtifact.created_at.desc())
            .limit(1)
        )
        artifact: ModelArtifact | None = self.db.execute(artifact_stmt).scalar_one_or_none()
        pipeline = joblib.load(artifact.file_path)

        # ---- Rebuild feature matrix --------------------------------------
        vec_repo = DescriptorVectorRepository(self.db)
        prop_repo = MaterialPropertyRepository(self.db)
        ds_repo = DescriptorSetRepository(self.db)

        vectors = vec_repo.get_all_for_dataset(effective_dataset_id, mv.descriptor_set_id)
        if not vectors:
            raise ModelEvaluationError(
                code="NO_DESCRIPTOR_VECTORS",
                message="No se encontraron vectores de descriptores para este dataset",
                recommended_action="Ejecute primero GenerateDescriptorsUseCase",
            )

        desc_set = ds_repo.get_by_id(mv.descriptor_set_id)
        feature_names: list[str] = (
            desc_set.feature_names if desc_set and desc_set.feature_names else []
        )

        task_type = TaskType(mv.task_type) if mv.task_type else TaskType.REGRESSION
        target_property = mv.target_property

        X_rows, y_values = [], []
        for vec in vectors:
            prop = prop_repo.get_by_material_and_property(vec.material_id, target_property)
            if prop is None:
                continue
            if task_type == TaskType.REGRESSION:
                if prop.value_float is None:
                    continue
                y_val = prop.value_float
            else:
                if prop.value_bool is not None:
                    y_val = 1.0 if prop.value_bool else 0.0
                elif prop.value_float is not None:
                    y_val = float(int(round(prop.value_float)))
                else:
                    continue
            raw = vec.vector
            if isinstance(raw, dict):
                raw = list(raw.values())
            X_rows.append(raw)
            y_values.append(y_val)

        if not X_rows:
            raise ModelEvaluationError(
                code="NO_MATCHING_SAMPLES",
                message=f"No se encontraron muestras con el objetivo '{target_property}'",
                recommended_action="Asegúrese de que el dataset contenga la propiedad objetivo",
            )

        n = len(X_rows)
        cols = feature_names[:len(X_rows[0])] if feature_names else [
            f"feat_{i}" for i in range(len(X_rows[0]))
        ]
        X = pd.DataFrame(X_rows, columns=cols)
        y = pd.Series(y_values, name=target_property)

        stratify = y if task_type == TaskType.CLASSIFICATION else None
        X_train, X_test, y_train, y_test = prepare_train_test(
            X, y, test_size=test_size, stratify=stratify
        )

        if task_type == TaskType.REGRESSION:
            evaluator = RegressionEvaluator()
        else:
            evaluator = ClassificationEvaluator()

        eval_result = evaluator.evaluate(pipeline, X_train, X_test, y_train, y_test)

        # Create an evaluation training run to anchor the metrics
        from datetime import datetime, timezone
        eval_run = ModelTrainingRun(
            id=uuid.uuid4(),
            model_version_id=model_version_id,
            dataset_id=effective_dataset_id,
            descriptor_set_id=mv.descriptor_set_id,
            status="completed",
            n_train_samples=len(X_train),
            n_test_samples=len(X_test),
            n_features=X.shape[1],
            completed_at=datetime.now(tz=timezone.utc),
        )
        self.db.add(eval_run)
        self.db.flush()

        # Persist metrics tagged with the evaluation split
        for m in eval_result["metrics"]:
            self.db.add(
                ModelMetric(
                    id=uuid.uuid4(),
                    training_run_id=eval_run.id,
                    split=f"eval_{m['split']}",
                    metric_name=m["metric_name"],
                    metric_value=float(m["metric_value"]),
                )
            )
        self.db.commit()

        logger.info(
            "model_evaluated",
            model_version_id=str(model_version_id),
            n_samples=n,
            target=target_property,
        )

        return {
            "model_version_id": str(model_version_id),
            "task_type": task_type.value,
            "target_property": target_property,
            "n_samples": n,
            "metrics": eval_result["metrics"],
        }
