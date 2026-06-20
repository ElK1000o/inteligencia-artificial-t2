"""
Dashboard routes for MatEnergy-ML.

Endpoints:
  GET /dashboard/stats — aggregated platform statistics for the dashboard UI
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.security import get_current_user_payload
from app.infrastructure.database.models.dataset_models import Dataset, RejectedDatasetRow
from app.infrastructure.database.models.material_models import Material, MaterialProperty
from app.infrastructure.database.models.model_models import ModelMetric, ModelTrainingRun, ModelVersion
from app.infrastructure.database.models.ranking_models import CandidateRankingItem
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
logger = get_logger(__name__)


@router.get("/stats")
async def dashboard_stats(
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Return aggregated platform statistics:

    - total_materials: all materials in the database
    - valid_materials: materials belonging to datasets with status='valid'
    - rejected_rows: total rejected rows across all datasets
    - active_datasets: datasets with status in (valid, partial)
    - active_models: model versions with is_active=True
    - best_mae: lowest test MAE across all completed runs (None if none exist)
    - best_f1: highest test F1 across all completed runs (None if none exist)
    - stable_candidates: ranking items labelled high_priority
    - last_training: ISO timestamp of the most recent completed training run
    - security_events_count: placeholder (audit log integration pending)
    """
    # Total materials
    total_materials: int = db.execute(
        select(func.count()).select_from(Material)
    ).scalar_one()

    # Valid materials (in valid/partial datasets)
    valid_dataset_ids_stmt = select(Dataset.id).where(
        Dataset.status.in_(["valid", "partial"])
    )
    valid_dataset_ids = [r for (r,) in db.execute(valid_dataset_ids_stmt).all()]
    if valid_dataset_ids:
        valid_materials: int = db.execute(
            select(func.count())
            .select_from(Material)
            .where(Material.dataset_id.in_(valid_dataset_ids))
        ).scalar_one()
    else:
        valid_materials = 0

    # Rejected rows
    rejected_rows: int = db.execute(
        select(func.count()).select_from(RejectedDatasetRow)
    ).scalar_one()

    # Active datasets
    active_datasets: int = db.execute(
        select(func.count())
        .select_from(Dataset)
        .where(Dataset.status.in_(["valid", "partial", "pending"]))
    ).scalar_one()

    # Active models
    active_models: int = db.execute(
        select(func.count())
        .select_from(ModelVersion)
        .where(ModelVersion.is_active.is_(True))
    ).scalar_one()

    # Best MAE (test split, minimum value)
    best_mae_row = db.execute(
        select(func.min(ModelMetric.metric_value))
        .where(
            ModelMetric.split == "test",
            ModelMetric.metric_name == "mae",
        )
    ).scalar_one_or_none()
    best_mae = float(best_mae_row) if best_mae_row is not None else None

    # Best F1-macro (test split, maximum value)
    best_f1_row = db.execute(
        select(func.max(ModelMetric.metric_value))
        .where(
            ModelMetric.split == "test",
            ModelMetric.metric_name == "f1_macro",
        )
    ).scalar_one_or_none()
    best_f1 = float(best_f1_row) if best_f1_row is not None else None

    # DFT-confirmed stable materials: energy_above_hull <= 0.05 eV/atom.
    # Uses ground-truth property values, which is more rigorous for a thesis than ML predictions.
    stable_candidates: int = db.execute(
        select(func.count())
        .select_from(MaterialProperty)
        .where(
            MaterialProperty.property_name == "energy_above_hull",
            MaterialProperty.value_float.isnot(None),
            MaterialProperty.value_float <= 0.05,
        )
    ).scalar_one()

    # Last training run completion
    last_run = db.execute(
        select(ModelTrainingRun.completed_at)
        .where(ModelTrainingRun.status == "completed")
        .order_by(ModelTrainingRun.completed_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    last_training = last_run.isoformat() if last_run else None

    return {
        "total_materials": total_materials,
        "valid_materials": valid_materials,
        "rejected_rows": rejected_rows,
        "active_datasets": active_datasets,
        "active_models": active_models,
        "best_mae": best_mae,
        "best_f1": best_f1,
        "stable_candidates": stable_candidates,
        "last_training": last_training,
        "security_events_count": 0,  # Placeholder — audit log integration pending
    }
