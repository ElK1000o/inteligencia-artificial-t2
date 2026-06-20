"""
Prediction routes for MatEnergy-ML.

Endpoints:
  POST  /predictions                          — create a prediction batch
  GET   /predictions/batches                  — list all prediction batches
  GET   /predictions/batches/{batch_id}       — list individual predictions for a batch
  GET   /predictions/material/{material_id}   — list predictions for a specific material
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.security import get_current_user_payload
from app.infrastructure.database.models.prediction_models import Prediction, PredictionBatch
from app.infrastructure.database.repositories.model_repository import ModelVersionRepository
from app.infrastructure.database.session import get_db
from app.application.use_cases.predict_material_property_use_case import (
    PredictMaterialPropertyUseCase,
)
from app.schemas.common import MessageResponse
from app.schemas.prediction_schemas import (
    BatchPredictionRequest,
    PredictionBatchResponse,
    PredictionRequest,
    PredictionResponse,
)

router = APIRouter(prefix="/predictions", tags=["predictions"])
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_batch_or_404(db: Session, batch_id: uuid.UUID) -> PredictionBatch:
    stmt = select(PredictionBatch).where(PredictionBatch.id == batch_id)
    batch = db.execute(stmt).scalar_one_or_none()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lote de predicciones no encontrado"
        )
    return batch


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/batch",
    status_code=status.HTTP_200_OK,
    summary="Run batch predictions synchronously",
)
async def run_batch_predictions(
    body: BatchPredictionRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Run predictions for a list of materials using the specified (or active) model.

    Calls PredictMaterialPropertyUseCase synchronously and returns the full
    prediction results, including per-material OOD indicators.
    """
    user_id = uuid.UUID(payload["sub"])
    use_case = PredictMaterialPropertyUseCase(db)
    try:
        result = use_case.execute(
            target_property=body.target_property,
            material_ids=list(body.material_ids),
            dataset_id=body.dataset_id,
            user_id=user_id,
            model_version_id=body.model_version_id,
        )
    except Exception as exc:
        logger.error("prediction_batch_failed", error=str(exc), user_id=str(user_id))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return result


@router.post("", response_model=PredictionBatchResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_prediction_batch(
    body: PredictionRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> PredictionBatchResponse:
    """
    Submit a prediction batch for the given model + dataset.

    Optionally pass ``material_ids`` to predict only a subset; omit for all
    materials in the dataset.

    This endpoint creates the batch record with status='pending'. In production
    a background worker would pick it up and populate individual Prediction rows.
    """
    user_id = uuid.UUID(payload["sub"])

    # Validate model exists
    mv_repo = ModelVersionRepository(db)
    mv = mv_repo.get_by_id(body.model_version_id)
    if not mv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Versión de modelo no encontrada"
        )

    # Determine material count
    n_materials: Optional[int] = None
    if body.material_ids is not None:
        n_materials = len(body.material_ids)

    batch = PredictionBatch(
        id=uuid.uuid4(),
        model_version_id=body.model_version_id,
        dataset_id=body.dataset_id,
        status="pending",
        n_materials=n_materials,
        created_by=user_id,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    logger.info(
        "prediction_batch_created",
        batch_id=str(batch.id),
        model_version_id=str(body.model_version_id),
        user_id=str(user_id),
    )
    return PredictionBatchResponse.model_validate(batch)


@router.get("/batches", response_model=list[PredictionBatchResponse])
async def list_prediction_batches(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> list[PredictionBatchResponse]:
    """List all prediction batches, newest first."""
    stmt = (
        select(PredictionBatch)
        .order_by(PredictionBatch.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    batches = list(db.execute(stmt).scalars().all())
    return [PredictionBatchResponse.model_validate(b) for b in batches]


@router.get("/batches/{batch_id}", response_model=list[PredictionResponse])
async def get_batch_predictions(
    batch_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> list[PredictionResponse]:
    """List individual prediction results for a batch."""
    _get_batch_or_404(db, batch_id)

    stmt = (
        select(Prediction)
        .where(Prediction.batch_id == batch_id)
        .offset(skip)
        .limit(limit)
    )
    preds = list(db.execute(stmt).scalars().all())
    return [PredictionResponse.model_validate(p) for p in preds]


@router.get("/material/{material_id}", response_model=list[PredictionResponse])
async def get_material_predictions(
    material_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> list[PredictionResponse]:
    """List all predictions made for a specific material across all batches."""
    stmt = (
        select(Prediction)
        .where(Prediction.material_id == material_id)
        .order_by(Prediction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    preds = list(db.execute(stmt).scalars().all())
    return [PredictionResponse.model_validate(p) for p in preds]
