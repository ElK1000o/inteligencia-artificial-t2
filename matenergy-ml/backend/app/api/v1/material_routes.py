"""
Material routes for MatEnergy-ML.

Endpoints:
  GET /materials                                          — list / filter materials
  GET /materials/{material_id}                           — material detail with properties
  GET /materials/dataset/{dataset_id}/stats              — element distribution + property stats
  GET /materials/dataset/{dataset_id}/properties/{name}/distribution
                                                         — value distribution for a property
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.security import get_current_user_payload
from app.infrastructure.database.models.material_models import Material, MaterialProperty
from app.infrastructure.database.repositories.material_repository import (
    MaterialPropertyRepository,
    MaterialRepository,
)
from app.infrastructure.database.session import get_db
from app.schemas.material_schemas import MaterialDetailResponse, MaterialPropertyResponse, MaterialResponse

router = APIRouter(prefix="/materials", tags=["materials"])
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("", response_model=list[MaterialResponse])
async def list_materials(
    dataset_id: Optional[uuid.UUID] = Query(None),
    formula: Optional[str] = Query(None, description="Partial formula search"),
    chemsys: Optional[str] = Query(None, description="Exact chemical system, e.g. 'Fe-Li-O'"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> list[MaterialResponse]:
    """
    List materials with optional filters.

    Filters can be combined freely. Results are paginated via skip/limit.
    """
    repo = MaterialRepository(db)

    if dataset_id and chemsys:
        # Combined filter: dataset + chemsys
        stmt = (
            select(Material)
            .where(Material.dataset_id == dataset_id, Material.chemsys == chemsys)
            .offset(skip)
            .limit(limit)
        )
        items = list(db.execute(stmt).scalars().all())
    elif dataset_id and formula:
        stmt = (
            select(Material)
            .where(
                Material.dataset_id == dataset_id,
                Material.formula.ilike(f"%{formula}%"),
            )
            .offset(skip)
            .limit(limit)
        )
        items = list(db.execute(stmt).scalars().all())
    elif dataset_id:
        items = repo.get_by_dataset(dataset_id, skip=skip, limit=limit)
    elif formula:
        items = repo.search_by_formula(formula, skip=skip, limit=limit)
    elif chemsys:
        items = repo.get_by_chemsys(chemsys, skip=skip, limit=limit)
    else:
        items = repo.get_all(skip=skip, limit=limit)

    return [MaterialResponse.model_validate(m) for m in items]


@router.get("/dataset/{dataset_id}/stats")
async def dataset_material_stats(
    dataset_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Aggregated statistics for a dataset:
      - element_distribution: count of materials containing each element
      - property_stats: mean/min/max/std/count for each numeric property present
      - total_materials: total material count
    """
    mat_repo = MaterialRepository(db)
    prop_repo = MaterialPropertyRepository(db)

    total = mat_repo.count_by_dataset(dataset_id)
    element_dist = mat_repo.get_element_distribution(dataset_id)

    # Discover all property names for this dataset
    stmt = (
        select(MaterialProperty.property_name)
        .join(Material, Material.id == MaterialProperty.material_id)
        .where(
            Material.dataset_id == dataset_id,
            MaterialProperty.value_float.isnot(None),
        )
        .distinct()
    )
    property_names = list(db.execute(stmt).scalars().all())

    property_stats: dict = {}
    for prop_name in property_names:
        try:
            property_stats[prop_name] = prop_repo.get_property_stats(dataset_id, prop_name)
        except Exception:
            property_stats[prop_name] = {}

    return {
        "total_materials": total,
        "element_distribution": element_dist,
        "property_stats": property_stats,
    }


@router.get("/dataset/{dataset_id}/hull-data")
async def hull_data(
    dataset_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Return per-material formation_energy_per_atom and energy_above_hull for the
    convex-hull scatter plot.  Points with only one property are included (null
    for the missing axis).
    """
    from sqlalchemy.orm import aliased

    Prop1 = aliased(MaterialProperty)
    Prop2 = aliased(MaterialProperty)

    stmt = (
        select(
            Material.id,
            Material.formula,
            Prop1.value_float.label("formation_energy"),
            Prop2.value_float.label("energy_above_hull"),
        )
        .join(
            Prop1,
            (Prop1.material_id == Material.id)
            & (Prop1.property_name == "formation_energy_per_atom"),
        )
        .outerjoin(
            Prop2,
            (Prop2.material_id == Material.id)
            & (Prop2.property_name == "energy_above_hull"),
        )
        .where(Material.dataset_id == dataset_id)
    )
    rows = list(db.execute(stmt).all())

    def _stability(eah: float | None) -> str:
        if eah is None:
            return "unknown"
        if eah <= 0.05:
            return "stable"
        if eah <= 0.10:
            return "metastable"
        return "unstable"

    points = [
        {
            "material_id": str(r.id),
            "formula": r.formula,
            "formation_energy_per_atom": r.formation_energy,
            "energy_above_hull": r.energy_above_hull,
            "stability_label": _stability(r.energy_above_hull),
        }
        for r in rows
    ]
    return {"points": points}


@router.get("/dataset/{dataset_id}/properties/{prop_name}/distribution")
async def property_distribution(
    dataset_id: uuid.UUID,
    prop_name: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=5000),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> list[float]:
    """
    Return the numeric values for *prop_name* across all materials in the dataset.

    Useful for rendering histograms on the front-end.
    Null values are excluded. Results are paginated.
    """
    stmt = (
        select(MaterialProperty.value_float)
        .join(Material, Material.id == MaterialProperty.material_id)
        .where(
            Material.dataset_id == dataset_id,
            MaterialProperty.property_name == prop_name,
            MaterialProperty.value_float.isnot(None),
        )
        .offset(skip)
        .limit(limit)
    )
    values = list(db.execute(stmt).scalars().all())
    return values


@router.get("/{material_id}/decomposition")
async def material_decomposition(
    material_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Compute the thermodynamic decomposition pathway for a material using the
    Materials Project phase diagram.

    For unstable/metastable materials, returns the set of stable competing phases
    that the composition would decompose into, along with their fractional amounts.
    Requires MATERIALS_PROJECT_API_KEY to be set.
    """
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material no encontrado")

    # Resolve chemsys: from DB field or parse from formula
    if material.chemsys:
        chemsys_list = [el.strip() for el in material.chemsys.split("-") if el.strip()]
    else:
        try:
            from pymatgen.core import Composition
            comp = Composition(material.formula)
            chemsys_list = [str(el) for el in comp.elements]
        except Exception:
            raise HTTPException(status_code=400, detail=f"No se pudo determinar el sistema químico para la fórmula '{material.formula}'")

    from app.infrastructure.external.materials_project_client import MaterialsProjectClient
    client = MaterialsProjectClient()

    if not client.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La clave de API de Materials Project no está configurada. Defina la variable de entorno MATERIALS_PROJECT_API_KEY.",
        )

    result = client.fetch_decomposition(material.formula, chemsys_list)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No se pudo calcular la descomposición para '{material.formula}'. No se encontraron entradas en el sistema químico.",
        )

    return result


@router.get("/{material_id}/structure")
async def material_structure(
    material_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Fetch the 3D crystal structure for a material from Materials Project.

    Searches by formula and returns the most stable polymorph found.
    Results are cached per formula for the process lifetime.
    Requires MATERIALS_PROJECT_API_KEY to be set.
    """
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material no encontrado")

    from app.infrastructure.external.materials_project_client import MaterialsProjectClient
    client = MaterialsProjectClient()

    if not client.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La clave de API de Materials Project no está configurada. Defina la variable de entorno MATERIALS_PROJECT_API_KEY.",
        )

    result = client.fetch_structure(material.formula)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró estructura cristalina en Materials Project para la fórmula '{material.formula}'.",
        )

    return result


@router.get("/{material_id}/analysis")
async def material_analysis(
    material_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Composition-level chemical analysis for a material.

    Uses pymatgen to compute element properties, electronegativity mismatch,
    ionic size mismatch, and oxidation state feasibility.  Combines this with
    DFT properties from the database to produce a list of instability factors
    and an overall stability verdict.
    """
    material = db.get(Material, material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material no encontrado")

    from pymatgen.core import Composition, Element
    import numpy as np

    try:
        comp = Composition(material.formula)
    except Exception:
        raise HTTPException(status_code=400, detail=f"No se pudo interpretar la fórmula: {material.formula}")

    # ---- Per-element data ----
    element_data = []
    for el_obj, amount in comp.items():
        el = Element(str(el_obj))
        ar = el.atomic_radius
        element_data.append({
            "symbol": str(el),
            "amount": float(amount),
            "fraction": float(comp.get_atomic_fraction(el_obj)),
            "atomic_radius": float(ar.to("ang")) if ar is not None else None,
            "electronegativity": el.X,
            "common_oxidation_states": list(el.common_oxidation_states),
            "period": el.row,
            "group": el.group,
            "block": el.block,
        })

    xs = [e["electronegativity"] for e in element_data if e["electronegativity"] is not None]
    radii = [e["atomic_radius"] for e in element_data if e["atomic_radius"] is not None]

    x_spread = float(max(xs) - min(xs)) if len(xs) > 1 else 0.0
    x_mean = float(np.mean(xs)) if xs else 0.0
    r_mismatch = float((max(radii) - min(radii)) / np.mean(radii)) if len(radii) > 1 else 0.0

    # ---- Oxidation state feasibility ----
    charge_balanced: bool | None = None
    dominant_oxi: dict = {}
    try:
        oxi_guesses = comp.oxi_state_guesses(max_sites=-1)
        charge_balanced = len(oxi_guesses) > 0
        dominant_oxi = {str(k): float(v) for k, v in oxi_guesses[0].items()} if oxi_guesses else {}
    except Exception:
        charge_balanced = None

    # ---- Fetch DFT properties from DB ----
    prop_rows = db.execute(
        select(MaterialProperty.property_name, MaterialProperty.value_float, MaterialProperty.value_str)
        .where(MaterialProperty.material_id == material_id)
    ).all()
    prop_dict: dict = {p.property_name: {"float": p.value_float, "str": p.value_str} for p in prop_rows}

    eah = prop_dict.get("energy_above_hull", {}).get("float")
    fe = prop_dict.get("formation_energy_per_atom", {}).get("float")
    band_gap = prop_dict.get("band_gap", {}).get("float")

    # ---- Build instability factors ----
    instability_factors: list[dict] = []

    if eah is not None and eah > 0.05:
        instability_factors.append({
            "factor": "Alta energía sobre el casco convexo",
            "severity": "high" if eah > 0.2 else "medium",
            "value": round(float(eah), 4),
            "unit": "eV/atom",
            "explanation": (
                f"El DFT ubica este material {eah:.3f} eV/átomo por encima del casco convexo termodinámico. "
                "Un material tan alejado del casco convexo tiende a descomponerse en fases competidoras más estables."
            ),
            "threshold_note": "≤ 0.05 estable · 0.05–0.10 metaestable · > 0.10 inestable",
        })

    if x_spread > 1.8:
        instability_factors.append({
            "factor": "Mismatch de electronegatividad",
            "severity": "high" if x_spread > 2.4 else "medium",
            "value": round(x_spread, 2),
            "unit": "Pauling",
            "explanation": (
                f"El rango de electronegatividad entre los elementos es de {x_spread:.2f} unidades de Pauling. "
                "Diferencias grandes promueven enlaces iónicos/polares fuertes; si la geometría no puede acomodar "
                "la redistribución de carga resultante, se acumula tensión estructural."
            ),
            "threshold_note": "< 1.0 covalente · 1.0–1.8 covalente polar · > 1.8 iónico",
        })

    if r_mismatch > 0.40:
        instability_factors.append({
            "factor": "Mismatch de tamaño iónico",
            "severity": "high" if r_mismatch > 0.70 else "medium",
            "value": round(r_mismatch * 100, 1),
            "unit": "%",
            "explanation": (
                f"Los radios atómicos abarcan un {r_mismatch*100:.0f}% del radio medio. "
                "Cuando iones de tamaños muy diferentes comparten una red cristalina, la tensión de enlace puede provocar "
                "distorsiones estructurales, transiciones de fase o descomposición."
            ),
            "threshold_note": "< 15% bajo · 15–40% moderado · > 40% alto",
        })

    if charge_balanced is False:
        instability_factors.append({
            "factor": "Desbalance de carga",
            "severity": "high",
            "value": None,
            "unit": None,
            "explanation": (
                "Ninguna asignación válida de estados de oxidación comunes produce una fórmula electroneutra. "
                "La composición probablemente esté electrónicamente frustrada o requiera valencias inusuales."
            ),
            "threshold_note": "Se requiere una asignación válida de estados de oxidación para la estabilidad",
        })

    nelements = len(element_data)
    if nelements > 4:
        instability_factors.append({
            "factor": "Alta complejidad composicional",
            "severity": "low",
            "value": nelements,
            "unit": "elements",
            "explanation": (
                f"Con {nelements} elementos distintos, la entropía configuracional es alta y "
                "las fases competidoras se vuelven más numerosas, dificultando encontrar un estado fundamental estable."
            ),
            "threshold_note": "Los sistemas binarios/ternarios son generalmente más fáciles de estabilizar",
        })

    if fe is not None and fe > 0.0:
        instability_factors.append({
            "factor": "Energía de formación positiva",
            "severity": "medium",
            "value": round(float(fe), 4),
            "unit": "eV/atom",
            "explanation": (
                f"La energía de formación es +{fe:.3f} eV/átomo, lo que significa que el compuesto está energéticamente "
                "desfavorecido respecto a las referencias elementales a 0 K."
            ),
            "threshold_note": "Los valores negativos indican formación exotérmica",
        })

    # ---- Stability verdict ----
    if eah is not None:
        if eah <= 0.025:
            stability_verdict = "stable"
            verdict_text = "Termodinámicamente estable"
            verdict_detail = "Energía sobre el casco convexo ≤ 0.025 eV/átomo — probablemente está sobre o muy cerca del casco convexo."
        elif eah <= 0.10:
            stability_verdict = "metastable"
            verdict_text = "Metaestable"
            verdict_detail = "Por encima del casco convexo pero dentro de un rango accesible por síntesis. Puede estabilizarse por temperatura, presión o entropía."
        else:
            stability_verdict = "unstable"
            verdict_text = "Termodinámicamente inestable"
            verdict_detail = f"EAH = {eah:.3f} eV/átomo — este material tenderá a descomponerse en fases más estables."
    else:
        stability_verdict = "unknown"
        verdict_text = "Estabilidad desconocida"
        verdict_detail = "No hay datos de energía DFT disponibles para la evaluación termodinámica."

    return {
        "formula": material.formula,
        "reduced_formula": material.reduced_formula,
        "element_data": element_data,
        "composition_stats": {
            "n_elements": nelements,
            "electronegativity_spread": round(x_spread, 3),
            "electronegativity_mean": round(x_mean, 3),
            "size_mismatch_ratio": round(r_mismatch, 3),
            "charge_balanced": charge_balanced,
            "dominant_oxidation_states": dominant_oxi,
        },
        "dft_properties": {
            "energy_above_hull": float(eah) if eah is not None else None,
            "formation_energy_per_atom": float(fe) if fe is not None else None,
            "band_gap": float(band_gap) if band_gap is not None else None,
        },
        "instability_factors": instability_factors,
        "stability_verdict": stability_verdict,
        "verdict_text": verdict_text,
        "verdict_detail": verdict_detail,
        "structure_note": (
            "Los datos de estructura cristalina (CIF / posiciones atómicas) no están almacenados para este dataset. "
            "Este panel muestra el análisis químico a nivel de composición usando pymatgen. "
            "Para visualización 3D de la estructura cristalina, conecte con la API de Materials Project."
        ),
    }


@router.get("/{material_id}", response_model=MaterialDetailResponse)
async def get_material(
    material_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> MaterialDetailResponse:
    """Retrieve a single material with all its associated properties."""
    repo = MaterialRepository(db)
    material = repo.get_by_id(material_id)
    if not material:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Material no encontrado")

    props = [
        MaterialPropertyResponse.model_validate(p) for p in material.properties
    ]
    detail = MaterialDetailResponse.model_validate(material)
    detail.properties = props
    return detail
