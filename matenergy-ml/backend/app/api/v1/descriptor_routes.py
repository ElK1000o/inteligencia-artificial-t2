"""
Descriptor routes for MatEnergy-ML.

Endpoints:
  POST  /descriptors/generate         — generate compositional (+ optional structural) descriptors
  GET   /descriptors/sets             — list descriptor sets
  GET   /descriptors/sets/{set_id}    — descriptor set detail with feature names
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.logging_config import get_logger
from app.core.security import get_current_user_payload, require_roles
from app.infrastructure.database.models.descriptor_models import DescriptorSet
from app.infrastructure.database.models.dataset_models import Dataset
from app.infrastructure.database.session import get_db
from app.schemas.descriptor_schemas import (
    DescriptorGenerationResult,
    DescriptorSetResponse,
    GenerateDescriptorsRequest,
)

router = APIRouter(prefix="/descriptors", tags=["descriptors"])
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/generate",
    response_model=DescriptorGenerationResult,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.RESEARCHER))],
)
async def generate_descriptors(
    body: GenerateDescriptorsRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> DescriptorGenerationResult:
    """
    Trigger descriptor generation for a dataset.

    Creates a DescriptorSet record and returns its ID. In production, a
    background worker computes the feature vectors for each material.
    This endpoint validates the dataset exists and registers the set.
    """
    user_id = uuid.UUID(payload["sub"])

    # Validate dataset exists
    dataset = db.get(Dataset, body.dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dataset no encontrado"
        )

    descriptor_type = "combined" if body.include_structural else "compositional"
    version = "1.0"
    set_name = body.name or f"{descriptor_type}_{body.dataset_id}"

    ds = DescriptorSet(
        id=uuid.uuid4(),
        name=set_name,
        version=version,
        descriptor_type=descriptor_type,
        n_features=None,  # populated after generation
        feature_names=None,
        created_by=user_id,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

    logger.info(
        "descriptor_generation_requested",
        descriptor_set_id=str(ds.id),
        dataset_id=str(body.dataset_id),
        descriptor_type=descriptor_type,
        user_id=str(user_id),
    )

    return DescriptorGenerationResult(
        descriptor_set_id=ds.id,
        n_success=0,
        n_error=0,
        errors=[],
        feature_names=[],
    )


@router.get("/sets", response_model=list[DescriptorSetResponse])
async def list_descriptor_sets(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> list[DescriptorSetResponse]:
    """List all descriptor sets."""
    stmt = (
        select(DescriptorSet)
        .order_by(DescriptorSet.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    sets = list(db.execute(stmt).scalars().all())
    return [DescriptorSetResponse.model_validate(s) for s in sets]


_TSNE_CACHE: dict = {}


@router.get("/sets/{set_id}/space-map")
async def descriptor_space_map(
    set_id: uuid.UUID,
    n_components: int = Query(2, ge=2, le=3),
    perplexity: float = Query(30.0, ge=5.0, le=80.0),
    color_property: str = Query("formation_energy_per_atom"),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Project descriptor vectors into 2-D (or 3-D) using t-SNE for the chemical
    space map visualization.  Results are cached per (set_id, n_components, perplexity).
    """
    cache_key = (str(set_id), n_components, perplexity)
    if cache_key in _TSNE_CACHE:
        cached = _TSNE_CACHE[cache_key]
        coords = cached["coords"]
        mat_ids = cached["mat_ids"]
    else:
        from app.infrastructure.database.repositories.descriptor_repository import DescriptorVectorRepository
        vec_repo = DescriptorVectorRepository(db)
        vectors = vec_repo.get_all_for_set(set_id)
        if not vectors:
            raise HTTPException(status_code=404, detail="No se encontraron vectores de descriptores para este conjunto")

        import numpy as np
        from sklearn.preprocessing import StandardScaler
        from sklearn.manifold import TSNE

        mat_ids = [str(v.material_id) for v in vectors]
        raw = []
        for v in vectors:
            vec = v.vector
            if isinstance(vec, dict):
                vec = list(vec.values())
            raw.append(vec)

        X = np.array(raw, dtype=float)
        X = np.nan_to_num(X, nan=0.0)
        X_scaled = StandardScaler().fit_transform(X)

        import sklearn
        _sklearn_version = tuple(int(x) for x in sklearn.__version__.split(".")[:2])
        _tsne_kwargs: dict = dict(
            n_components=n_components,
            perplexity=min(perplexity, len(mat_ids) - 1),
            random_state=42,
        )
        # n_iter was renamed to max_iter in sklearn 1.5
        if _sklearn_version >= (1, 5):
            _tsne_kwargs["max_iter"] = 500
        else:
            _tsne_kwargs["n_iter"] = 500
        tsne = TSNE(**_tsne_kwargs)
        coords = tsne.fit_transform(X_scaled)
        _TSNE_CACHE[cache_key] = {"coords": coords, "mat_ids": mat_ids}

    from sqlalchemy import select
    from app.infrastructure.database.models.material_models import Material, MaterialProperty

    stmt = (
        select(Material.id, Material.formula, MaterialProperty.value_float)
        .join(
            MaterialProperty,
            (MaterialProperty.material_id == Material.id)
            & (MaterialProperty.property_name == color_property),
            isouter=True,
        )
        .where(Material.id.in_([mid for mid in mat_ids]))
    )
    prop_map: dict[str, tuple[str, float | None]] = {}
    for row in db.execute(stmt).all():
        prop_map[str(row.id)] = (row.formula, row.value_float)

    import numpy as np
    color_values = [prop_map.get(mid, ("?", None))[1] for mid in mat_ids]
    valid_colors = [c for c in color_values if c is not None]
    color_min = float(np.min(valid_colors)) if valid_colors else 0.0
    color_max = float(np.max(valid_colors)) if valid_colors else 1.0

    points = []
    for i, mid in enumerate(mat_ids):
        formula, cval = prop_map.get(mid, ("?", None))
        entry = {
            "material_id": mid,
            "formula": formula,
            "x": float(coords[i, 0]),
            "y": float(coords[i, 1]),
            "z": float(coords[i, 2]) if n_components == 3 else None,
            "color_value": cval,
            "color_property": color_property,
        }
        points.append(entry)

    return {
        "points": points,
        "color_min": color_min,
        "color_max": color_max,
        "color_property": color_property,
    }


@router.get("/sets/{set_id}")
async def get_descriptor_set(
    set_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Retrieve a descriptor set including its feature names (if already computed).
    """
    ds = db.get(DescriptorSet, set_id)
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conjunto de descriptores no encontrado"
        )

    base = DescriptorSetResponse.model_validate(ds).model_dump()
    # feature_names is stored as a JSONB column (dict or list)
    raw_names = ds.feature_names
    if isinstance(raw_names, list):
        feature_names = raw_names
    elif isinstance(raw_names, dict):
        # Support {"names": [...]} envelope stored by some tooling
        feature_names = raw_names.get("names", list(raw_names.values()))
    else:
        feature_names = []

    base["feature_names"] = feature_names
    return base
