"""
Composition Explorer routes for MatEnergy-ML.

Endpoints:
  POST /explore/predict   — predict properties for an arbitrary chemical formula
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.security import get_current_user_payload
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/explore", tags=["explore"])
logger = get_logger(__name__)


@router.post("/predict")
async def explore_predict(
    body: dict,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Predict material properties for an arbitrary chemical formula.

    Body:
        formula: str                    — e.g. "LiCoO2"
        descriptor_set_id: str          — UUID of descriptor set for feature names
        target_properties: list[str]    — properties to predict, e.g. ["energy_above_hull"]

    Returns predictions for each requested property using the currently active model.
    """
    formula: str = body.get("formula", "").strip()
    descriptor_set_id_str: str = body.get("descriptor_set_id", "")
    target_properties: list[str] = body.get("target_properties", ["energy_above_hull"])

    if not formula:
        raise HTTPException(status_code=400, detail="Se requiere formula")
    if not descriptor_set_id_str:
        raise HTTPException(status_code=400, detail="Se requiere descriptor_set_id")

    try:
        descriptor_set_id = uuid.UUID(descriptor_set_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="UUID de descriptor_set_id inválido")

    # Compute descriptors for the formula
    from app.infrastructure.descriptors.descriptor_pipeline import DescriptorPipelineOrchestrator
    try:
        orchestrator = DescriptorPipelineOrchestrator(include_structural=False, impute_nan=True)
        feat_dict, _ = orchestrator.compute_for_material(formula)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"No se pudieron calcular los descriptores: {e}")

    # Load descriptor set feature names
    from app.infrastructure.database.repositories.descriptor_repository import DescriptorSetRepository
    ds_repo = DescriptorSetRepository(db)
    desc_set = ds_repo.get_by_id(descriptor_set_id)
    if not desc_set:
        raise HTTPException(status_code=404, detail="Conjunto de descriptores no encontrado")

    feature_names: list[str] = (
        desc_set.feature_names if isinstance(desc_set.feature_names, list) else []
    )

    import pandas as pd
    import numpy as np
    vector = [feat_dict.get(name, 0.0) for name in feature_names]
    x_df = pd.DataFrame([vector], columns=feature_names) if feature_names else pd.DataFrame([list(feat_dict.values())])

    # Load active models for each requested property and predict
    from app.infrastructure.database.repositories.model_repository import (
        ModelVersionRepository,
        ModelArtifactRepository,
    )
    from app.infrastructure.ml.trainers import ModelTrainer
    from app.core.config import settings
    from app.infrastructure.database.repositories.material_repository import MaterialRepository

    mv_repo = ModelVersionRepository(db)
    artifact_repo = ModelArtifactRepository(db)
    trainer = ModelTrainer(settings.ARTIFACT_STORAGE_PATH)

    predictions: dict[str, float | str | None] = {}
    for prop in target_properties:
        active_mv = mv_repo.get_active_for_target(prop)
        if not active_mv:
            predictions[prop] = None
            continue
        artifact = artifact_repo.get_by_model_version(active_mv.id)
        if not artifact:
            predictions[prop] = None
            continue
        try:
            pipeline = trainer.load_artifact(artifact.file_path, artifact.sha256_hash)
            raw = pipeline.predict(x_df)[0]
            predictions[prop] = float(raw)
        except Exception:
            predictions[prop] = None

    # Stability label based on energy_above_hull prediction
    eah = predictions.get("energy_above_hull")
    if isinstance(eah, float):
        if eah <= 0.05:
            stability_label = "stable"
        elif eah <= 0.10:
            stability_label = "metastable"
        else:
            stability_label = "unstable"
    else:
        stability_label = "unknown"

    # Check if the formula is already in the database
    mat_repo = MaterialRepository(db)
    known = mat_repo.search_by_formula(formula, skip=0, limit=1)
    is_known = len(known) > 0
    known_material_id = str(known[0].id) if is_known else None

    # Descriptor preview (top 10 by magnitude)
    desc_preview = dict(
        sorted(feat_dict.items(), key=lambda kv: abs(kv[1]), reverse=True)[:10]
    )

    return {
        "formula": formula,
        "predictions": predictions,
        "stability_label": stability_label,
        "is_known_material": is_known,
        "material_id": known_material_id,
        "descriptors_preview": {k: round(float(v), 4) for k, v in desc_preview.items()},
    }
