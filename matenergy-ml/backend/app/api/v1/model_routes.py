"""
ML model routes for MatEnergy-ML.

Endpoints:
  POST  /models/train                     — submit a training job
  GET   /models                           — list model versions
  GET   /models/compare                   — compare multiple models by their metrics
  GET   /models/{model_id}                — model version detail
  GET   /models/{model_id}/metrics        — training metrics
  GET   /models/{model_id}/feature-importance — feature importance list
  POST  /models/{model_id}/activate       — set model as active for its target property

Training is handled synchronously in this stub implementation; in production
an async task queue (e.g. Celery) would be used.
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.logging_config import get_logger
from app.core.security import get_current_user_payload, require_roles
from app.infrastructure.database.models.model_models import ModelVersion, ModelTrainingRun
from app.infrastructure.database.repositories.model_repository import (
    ModelMetricRepository,
    ModelTrainingRunRepository,
    ModelVersionRepository,
)
from app.infrastructure.database.session import get_db
from app.schemas.common import MessageResponse
from app.schemas.model_schemas import (
    ModelMetricResponse,
    ModelTrainingRunResponse,
    ModelVersionResponse,
    TrainModelRequest,
)

router = APIRouter(prefix="/models", tags=["models"])
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Routes — note: /compare and /train must come BEFORE /{model_id} to avoid
# FastAPI treating "compare" or "train" as a UUID path parameter.
# ---------------------------------------------------------------------------


@router.post(
    "/train",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.RESEARCHER))],
)
async def train_model(
    body: TrainModelRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Submit a model training job.

    Creates a ModelVersion and a ModelTrainingRun record with status='running'.
    In production this would dispatch to a task queue; here the records are
    created immediately and the caller polls /models/{model_id} for updates.
    """
    user_id = uuid.UUID(payload["sub"])

    name = body.name or f"{body.model_type}_{body.target_property}"

    mv = ModelVersion(
        id=uuid.uuid4(),
        name=name,
        model_type=body.model_type,
        task_type=body.task_type,
        target_property=body.target_property,
        dataset_id=body.dataset_id,
        descriptor_set_id=body.descriptor_set_id,
        description=body.description,
        is_active=False,
        created_by=user_id,
    )
    db.add(mv)
    db.flush()

    run = ModelTrainingRun(
        id=uuid.uuid4(),
        model_version_id=mv.id,
        dataset_id=body.dataset_id,
        descriptor_set_id=body.descriptor_set_id,
        status="running",
        hyperparameters=body.hyperparameters or {},
        triggered_by=user_id,
    )
    db.add(run)
    db.commit()

    logger.info(
        "training_job_submitted",
        model_version_id=str(mv.id),
        run_id=str(run.id),
        user_id=str(user_id),
    )
    return {"job_id": str(run.id), "model_version_id": str(mv.id), "status": "running"}


@router.get("/compare")
async def compare_models(
    model_ids: list[uuid.UUID] = Query(..., description="Model version IDs to compare"),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> list[dict]:
    """
    Compare multiple model versions side-by-side with their test metrics.

    Pass one or more ``model_ids`` query parameters.
    """
    mv_repo = ModelVersionRepository(db)
    run_repo = ModelTrainingRunRepository(db)
    metric_repo = ModelMetricRepository(db)

    result = []
    for mid in model_ids:
        mv = mv_repo.get_by_id(mid)
        if not mv:
            continue
        mv_data = ModelVersionResponse.model_validate(mv).model_dump()

        # Gather metrics from the latest completed training run
        latest_run = run_repo.get_latest_completed(mid)
        metrics: list[dict] = []
        if latest_run:
            raw_metrics = metric_repo.get_by_run(latest_run.id)
            metrics = [ModelMetricResponse.model_validate(m).model_dump() for m in raw_metrics]

        mv_data["metrics"] = metrics
        result.append(mv_data)

    return result


@router.get("", response_model=list[ModelVersionResponse])
async def list_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    dataset_id: Optional[uuid.UUID] = Query(None),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> list[ModelVersionResponse]:
    """List all model versions."""
    repo = ModelVersionRepository(db)
    if dataset_id:
        items = repo.get_by_dataset(dataset_id)
    else:
        items = repo.get_all(skip=skip, limit=limit)
    return [ModelVersionResponse.model_validate(mv) for mv in items]


@router.get("/{model_id}", response_model=ModelVersionResponse)
async def get_model(
    model_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> ModelVersionResponse:
    """Retrieve a model version by ID."""
    repo = ModelVersionRepository(db)
    mv = repo.get_by_id(model_id)
    if not mv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo no encontrado")
    return ModelVersionResponse.model_validate(mv)


@router.get("/{model_id}/metrics", response_model=list[ModelMetricResponse])
async def get_model_metrics(
    model_id: uuid.UUID,
    split: Optional[str] = Query(None, description="Filter by split: train, test, cv"),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> list[ModelMetricResponse]:
    """
    Return all metrics for the latest completed training run of a model version.
    """
    mv_repo = ModelVersionRepository(db)
    mv = mv_repo.get_by_id(model_id)
    if not mv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo no encontrado")

    run_repo = ModelTrainingRunRepository(db)
    latest_run = run_repo.get_latest_completed(model_id)
    if not latest_run:
        return []

    metric_repo = ModelMetricRepository(db)
    if split:
        from sqlalchemy import select
        from app.infrastructure.database.models.model_models import ModelMetric
        stmt = (
            select(ModelMetric)
            .where(
                ModelMetric.training_run_id == latest_run.id,
                ModelMetric.split == split,
            )
        )
        metrics = list(db.execute(stmt).scalars().all())
    else:
        metrics = metric_repo.get_by_run(latest_run.id)

    return [ModelMetricResponse.model_validate(m) for m in metrics]


@router.get("/{model_id}/feature-importance")
async def get_feature_importance(
    model_id: uuid.UUID,
    top_n: int = Query(20, ge=1, le=200, description="Number of top features to return"),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> list[dict]:
    """
    Return feature importance values for a model version.

    Feature importances are stored in the ModelParameter table under the key
    'feature_importances'. Returns an empty list if not yet computed.
    """
    mv_repo = ModelVersionRepository(db)
    mv = mv_repo.get_by_id(model_id)
    if not mv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo no encontrado")

    # Look for feature_importances in model parameters
    from app.infrastructure.database.repositories.model_repository import ModelParameterRepository
    param_repo = ModelParameterRepository(db)
    param = param_repo.get_by_name(model_id, "feature_importances")
    if not param or not param.parameter_value:
        return []

    # parameter_value is expected to be a list of {"feature": ..., "importance": ...} dicts
    importances = param.parameter_value
    if isinstance(importances, list):
        sorted_importances = sorted(
            importances, key=lambda x: x.get("importance", 0), reverse=True
        )
        return sorted_importances[:top_n]
    return []


@router.get("/{model_id}/parity-data")
async def get_parity_data(
    model_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Return y_test vs y_pred arrays for parity-plot visualization.
    Only available for regression models trained after parity persistence was added.
    """
    mv_repo = ModelVersionRepository(db)
    mv = mv_repo.get_by_id(model_id)
    if not mv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo no encontrado")

    from app.infrastructure.database.repositories.model_repository import ModelParameterRepository
    param_repo = ModelParameterRepository(db)
    param = param_repo.get_by_name(model_id, "parity_data")
    if not param or not param.parameter_value:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Datos de parity no disponibles. Reentrene el modelo para generarlos.",
        )

    data = param.parameter_value
    y_test = data.get("y_test", [])
    y_pred = data.get("y_pred", [])

    if not y_test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Los datos de parity están vacíos")

    import numpy as np
    y_test_arr = np.array(y_test, dtype=float)
    y_pred_arr = np.array(y_pred, dtype=float)
    mae = float(np.mean(np.abs(y_test_arr - y_pred_arr)))
    ss_res = np.sum((y_test_arr - y_pred_arr) ** 2)
    ss_tot = np.sum((y_test_arr - np.mean(y_test_arr)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0

    return {
        "y_test": y_test,
        "y_pred": y_pred,
        "mae": round(mae, 6),
        "r2": round(r2, 6),
        "target_property": mv.target_property,
    }


@router.post("/{model_id}/explain")
async def explain_prediction(
    model_id: uuid.UUID,
    body: dict,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Compute SHAP feature contributions for a single material prediction.

    Body: { "material_id": str, "dataset_id": str }
    """
    material_id_str = body.get("material_id")
    dataset_id_str = body.get("dataset_id")
    if not material_id_str or not dataset_id_str:
        raise HTTPException(status_code=400, detail="Se requieren material_id y dataset_id")

    try:
        material_id = uuid.UUID(material_id_str)
        dataset_id = uuid.UUID(dataset_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de UUID inválido")

    mv_repo = ModelVersionRepository(db)
    mv = mv_repo.get_by_id(model_id)
    if not mv:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")

    from app.infrastructure.database.repositories.model_repository import (
        ModelArtifactRepository,
        ModelParameterRepository,
    )
    from app.infrastructure.database.repositories.descriptor_repository import DescriptorVectorRepository
    from app.infrastructure.database.models.material_models import Material
    from app.infrastructure.ml.trainers import ModelTrainer
    from app.core.config import settings

    artifact_repo = ModelArtifactRepository(db)
    artifact = artifact_repo.get_by_model_version(model_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artefacto del modelo no encontrado")

    trainer = ModelTrainer(settings.ARTIFACT_STORAGE_PATH)
    try:
        pipeline = trainer.load_artifact(artifact.file_path, artifact.sha256_hash)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo cargar el modelo: {e}")

    vec_repo = DescriptorVectorRepository(db)
    dv = vec_repo.get_by_material_and_set(material_id, mv.descriptor_set_id)
    if not dv:
        raise HTTPException(status_code=404, detail="No se encontró un vector de descriptores para este material")

    from app.infrastructure.database.repositories.descriptor_repository import DescriptorSetRepository
    ds_repo = DescriptorSetRepository(db)
    desc_set = ds_repo.get_by_id(mv.descriptor_set_id)
    feature_names: list[str] = (
        desc_set.feature_names if desc_set and isinstance(desc_set.feature_names, list) else []
    )

    raw_vector = dv.vector
    if isinstance(raw_vector, dict):
        raw_vector = list(raw_vector.values())

    n_features = len(raw_vector)
    cols = feature_names[:n_features] if len(feature_names) >= n_features else [f"feat_{i}" for i in range(n_features)]

    import pandas as pd
    import numpy as np
    x_df = pd.DataFrame([raw_vector], columns=cols)

    material = db.get(Material, material_id)
    formula = material.formula if material else str(material_id)[:8]

    try:
        import shap

        preprocessor = pipeline.named_steps.get("preprocessor")
        model_step = pipeline.named_steps.get("model")

        if preprocessor is not None:
            X_transformed = preprocessor.transform(x_df)
            if hasattr(X_transformed, "toarray"):
                X_transformed = X_transformed.toarray()
            X_transformed = np.array(X_transformed, dtype=float)
        else:
            X_transformed = x_df.values

        param_repo = ModelParameterRepository(db)
        bg_param = param_repo.get_by_name(model_id, "shap_background_sample")

        if hasattr(model_step, "feature_importances_") or hasattr(model_step, "estimators_"):
            explainer = shap.TreeExplainer(model_step)
            shap_vals = explainer.shap_values(X_transformed)
            if isinstance(shap_vals, list):
                shap_vals = shap_vals[1] if len(shap_vals) > 1 else shap_vals[0]
            shap_array = np.array(shap_vals).flatten()
            base_value = float(explainer.expected_value) if not isinstance(explainer.expected_value, (list, np.ndarray)) else float(explainer.expected_value[0])
        elif hasattr(model_step, "coef_"):
            if bg_param and bg_param.parameter_value:
                bg_data = np.array(bg_param.parameter_value["data"], dtype=float)
                explainer = shap.LinearExplainer(model_step, bg_data)
            else:
                explainer = shap.LinearExplainer(model_step, X_transformed)
            shap_vals = explainer.shap_values(X_transformed)
            shap_array = np.array(shap_vals).flatten()
            base_value = float(explainer.expected_value) if not isinstance(explainer.expected_value, (list, np.ndarray)) else float(explainer.expected_value[0])
        else:
            if bg_param and bg_param.parameter_value:
                bg_data = np.array(bg_param.parameter_value["data"], dtype=float)
                explainer = shap.KernelExplainer(model_step.predict, bg_data[:20])
            else:
                explainer = shap.KernelExplainer(model_step.predict, X_transformed)
            shap_vals = explainer.shap_values(X_transformed)
            shap_array = np.array(shap_vals).flatten()
            base_value = float(explainer.expected_value) if not isinstance(explainer.expected_value, (list, np.ndarray)) else float(explainer.expected_value[0])

        feature_contribs = [
            {
                "feature": cols[i] if i < len(cols) else f"feat_{i}",
                "shap_value": float(shap_array[i]),
                "feature_value": float(x_df.iloc[0, i]) if i < x_df.shape[1] else 0.0,
            }
            for i in range(len(shap_array))
        ]
        feature_contribs.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

        predicted_value = float(pipeline.predict(x_df)[0])

        return {
            "model_id": str(model_id),
            "material_id": str(material_id),
            "formula": formula,
            "base_value": base_value,
            "predicted_value": predicted_value,
            "target_property": mv.target_property,
            "feature_contributions": feature_contribs[:20],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falló el cálculo de SHAP: {e}")


@router.post(
    "/{model_id}/activate",
    response_model=MessageResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.RESEARCHER))],
)
async def activate_model(
    model_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Set a model version as active for its target property.

    Any previously active model for the same target property is deactivated.
    """
    repo = ModelVersionRepository(db)
    mv = repo.get_by_id(model_id)
    if not mv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Modelo no encontrado")

    repo.activate(mv)
    db.commit()

    logger.info(
        "model_activated",
        model_id=str(model_id),
        target_property=mv.target_property,
        activated_by=payload.get("sub"),
    )
    return MessageResponse(message=f"El modelo '{mv.name}' ahora está activo para '{mv.target_property}'")
