"""
PredictMaterialPropertyUseCase
===============================
Loads the active model for a target property, builds feature vectors for
a list of materials, runs prediction with OOD detection, and persists
a PredictionBatch + individual Prediction rows.

Steps
-----
1.  Resolve the active ModelVersion for the requested target_property.
2.  Verify artifact integrity.
3.  Load sklearn Pipeline via joblib.
4.  For each material: fetch DescriptorVector → predict → OOD check.
5.  Persist PredictionBatch and Prediction rows.
6.  Return batch summary with per-material results.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import TaskType
from app.core.exceptions import ModelEvaluationError, NotFoundError
from app.core.logging_config import get_logger
from app.infrastructure.database.models.model_models import ModelArtifact
from app.infrastructure.database.models.prediction_models import Prediction, PredictionBatch
from app.infrastructure.database.repositories import (
    DescriptorSetRepository,
    DescriptorVectorRepository,
    MaterialRepository,
    ModelVersionRepository,
)
from app.infrastructure.ml.predictor import Predictor
from app.application.use_cases.verify_model_artifact_use_case import (
    VerifyModelArtifactUseCase,
)

logger = get_logger(__name__)


class PredictMaterialPropertyUseCase:
    """
    Runs batch predictions for a target property over a set of materials.

    Args:
        db: Active SQLAlchemy Session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(
        self,
        target_property: str,
        material_ids: list[uuid.UUID],
        dataset_id: Optional[uuid.UUID],
        user_id: uuid.UUID,
        model_version_id: Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Run predictions and persist results.

        Args:
            target_property:   Property to predict (e.g. "energy_above_hull").
            material_ids:      List of material UUIDs to predict for.
            dataset_id:        Dataset the materials belong to (for descriptor lookup).
            user_id:           Requesting user.
            model_version_id:  Override; uses active model if None.

        Returns
        -------
        {
            "batch_id"       : str,
            "model_version_id": str,
            "n_predicted"    : int,
            "n_ood"          : int,
            "predictions"    : list[dict],
        }
        """
        # ---- Resolve model -----------------------------------------------
        mv_repo = ModelVersionRepository(self.db)
        if model_version_id:
            mv = mv_repo.get_by_id(model_version_id)
        else:
            mv = mv_repo.get_active_for_target(target_property)

        if mv is None:
            raise NotFoundError(
                code="NO_ACTIVE_MODEL",
                message=f"No se encontró un modelo activo para el objetivo '{target_property}'",
                recommended_action="Entrene y active primero un modelo para esta propiedad",
            )

        task_type = TaskType(mv.task_type) if mv.task_type else TaskType.REGRESSION

        # ---- Verify + load artifact --------------------------------------
        verifier = VerifyModelArtifactUseCase(self.db)
        verifier.execute(mv.id)

        artifact_stmt = (
            select(ModelArtifact)
            .where(ModelArtifact.model_version_id == mv.id)
            .order_by(ModelArtifact.created_at.desc())
            .limit(1)
        )
        artifact = self.db.execute(artifact_stmt).scalar_one_or_none()
        pipeline = joblib.load(artifact.file_path)

        # ---- Feature names -----------------------------------------------
        ds_repo = DescriptorSetRepository(self.db)
        desc_set = ds_repo.get_by_id(mv.descriptor_set_id) if mv.descriptor_set_id else None
        feature_names: list[str] = (
            desc_set.feature_names if desc_set and desc_set.feature_names else []
        )

        # ---- Create PredictionBatch --------------------------------------
        batch = PredictionBatch(
            id=uuid.uuid4(),
            model_version_id=mv.id,
            dataset_id=dataset_id,
            status="running",
            n_materials=len(material_ids),
            created_by=user_id,
        )
        self.db.add(batch)
        self.db.flush()

        # ---- Predict per material ----------------------------------------
        vec_repo = DescriptorVectorRepository(self.db)
        predictor = Predictor(pipeline=pipeline, feature_names=feature_names)
        results = []
        n_ood = 0

        for mat_id in material_ids:
            vec = vec_repo.get_for_material(mat_id, mv.descriptor_set_id) if mv.descriptor_set_id else None
            if vec is None:
                results.append({
                    "material_id": str(mat_id),
                    "error": "no_descriptor_vector",
                })
                continue

            raw = vec.vector
            if isinstance(raw, dict):
                raw = list(raw.values())

            n_feats = len(feature_names) if feature_names else len(raw)
            cols = feature_names[:n_feats] if feature_names else [f"feat_{i}" for i in range(n_feats)]
            x = pd.Series(raw[:n_feats], index=cols)
            x_df = x.to_frame().T

            pred_result = predictor.predict_single(x_df)

            # If predictor returned an error dict, skip DB row (avoids CHECK constraint violation)
            if pred_result.get("error"):
                results.append({
                    "material_id": str(mat_id),
                    "error": pred_result["error"],
                })
                continue

            is_ood = pred_result.get("is_out_of_domain", False)
            if is_ood:
                n_ood += 1

            pred_value: Optional[float] = None
            pred_class: Optional[str] = None

            if task_type == TaskType.REGRESSION:
                raw_pred = pred_result.get("predicted_value")
                pred_value = float(raw_pred) if raw_pred is not None else None
            else:
                raw_pred = pred_result.get("predicted_value")
                if raw_pred is not None:
                    pred_class = str(int(round(float(raw_pred))))

            # Guard: DB CHECK requires at least one of predicted_value / predicted_class
            if pred_value is None and pred_class is None:
                results.append({
                    "material_id": str(mat_id),
                    "error": "pipeline_returned_null_prediction",
                })
                continue

            prediction = Prediction(
                id=uuid.uuid4(),
                batch_id=batch.id,
                material_id=mat_id,
                predicted_value=pred_value,
                predicted_class=pred_class,
                confidence_score=pred_result.get("confidence_score"),
                is_out_of_domain=is_ood,
                out_of_domain_reason=pred_result.get("out_of_domain_reason"),
                is_calibrated=False,
            )
            self.db.add(prediction)

            results.append({
                "material_id": str(mat_id),
                "predicted_value": pred_value,
                "predicted_class": pred_class,
                "confidence_score": pred_result.get("confidence_score"),
                "is_out_of_domain": is_ood,
                "out_of_domain_reason": pred_result.get("out_of_domain_reason"),
            })

        batch.status = "completed"
        batch.completed_at = datetime.now(tz=timezone.utc)
        self.db.commit()

        logger.info(
            "predictions_complete",
            batch_id=str(batch.id),
            model_version_id=str(mv.id),
            n_predicted=len(results),
            n_ood=n_ood,
        )

        return {
            "batch_id": str(batch.id),
            "model_version_id": str(mv.id),
            "n_predicted": len(results),
            "n_ood": n_ood,
            "predictions": results,
        }
