"""
DFT simulation job routes — Etapa 13.

Endpoints:
  POST   /dft-jobs                        — submit a DFT calculation
  GET    /dft-jobs                        — list jobs (current user)
  GET    /dft-jobs/{job_id}               — job detail + results
  DELETE /dft-jobs/{job_id}               — cancel a pending/running job
  POST   /dft-jobs/{job_id}/ingest        — persist results as MaterialProperty
  GET    /dft-jobs/{job_id}/inputs        — download generated SLURM+VASP inputs
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.security import get_current_user_payload
from app.infrastructure.database.models.job_models import BackgroundJob
from app.infrastructure.database.repositories.job_repository import JobRepository
from app.infrastructure.database.session import get_db
from app.infrastructure.simulation import (
    CalculationType,
    DFTInputParameters,
    DFTResultIngester,
    LocalSimulationAdapter,
    SlurmAdapter,
)
from app.schemas.dft_schemas import (
    DftIngestRequest,
    DftIngestResponse,
    DftJobResponse,
    DftJobSubmitRequest,
    GeneratedInputsResponse,
)

router = APIRouter(prefix="/dft-jobs", tags=["dft-simulation"])
logger = get_logger(__name__)

_local_adapter = LocalSimulationAdapter()
_slurm_adapter = SlurmAdapter()


def _resolve_structure(formula: str, structure_json: dict | None):
    """Return a pymatgen Structure from JSON dict or fetch from Materials Project."""
    from pymatgen.core import Structure

    if structure_json:
        return Structure.from_dict(structure_json)

    # Attempt MP fetch using stored API key
    try:
        from app.core.config import settings
        if settings.MATERIALS_PROJECT_API_KEY:
            from mp_api.client import MPRester  # type: ignore[import]
            with MPRester(settings.MATERIALS_PROJECT_API_KEY) as mpr:
                docs = mpr.summary.search(formula=formula, fields=["structure"])
                if docs:
                    return docs[0].structure
    except Exception:
        pass

    # Final fallback: build a minimal dummy structure for testing
    from pymatgen.core import Lattice, PeriodicSite
    from pymatgen.core import Structure as Struct

    comp = __import__("pymatgen.core", fromlist=["Composition"]).Composition(formula)
    elements = list(comp.elements)
    if not elements:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No se pudo interpretar la fórmula '{formula}' como una composición química válida.",
        )
    lattice = Lattice.cubic(4.0)
    sites = [PeriodicSite(str(el), [i / len(elements), 0, 0], lattice) for i, el in enumerate(elements)]
    return Struct.from_sites(sites)


def _get_job_or_404(db: Session, job_id: uuid.UUID) -> BackgroundJob:
    repo = JobRepository(db)
    job = repo.get_by_id(job_id)
    if not job or job.job_type != "dft_calculation":
        raise HTTPException(status_code=404, detail="Trabajo DFT no encontrado")
    return job


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=DftJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_dft_job(
    body: DftJobSubmitRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Submit a DFT calculation. Returns immediately; poll GET /dft-jobs/{id} for status."""
    try:
        structure = _resolve_structure(body.formula, body.structure_json)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        calc_type = CalculationType(body.calculation_type)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"calculation_type desconocido: '{body.calculation_type}'. "
                   "Opciones válidas: static, relax, band_structure, dos",
        )

    params = DFTInputParameters(
        calculation_type=calc_type,
        encut=body.encut,
        kpoints_density=body.kpoints_density,
        functional=body.functional,
        hubbard_u=body.hubbard_u,
    )

    adapter = body.adapter.lower()
    if adapter == "slurm":
        job_id_str = _slurm_adapter.submit_job(structure, params, job_name=body.job_name)
        # For the slurm stub, create a DB record manually
        user_id = uuid.UUID(payload["sub"]) if "sub" in payload else None
        job = BackgroundJob(
            id=uuid.UUID(job_id_str.replace("slurm_", "")) if "slurm_" in job_id_str else uuid.uuid4(),
            job_type="dft_calculation",
            status="pending",
            created_by=user_id,
            payload={
                "formula": body.formula,
                "calculation_type": body.calculation_type,
                "functional": body.functional,
                "adapter": "slurm",
                "job_name": body.job_name or structure.reduced_formula,
                "slurm_job_id": job_id_str,
                "note": "SLURM stub — no real HPC submission",
            },
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        logger.info("dft_job_submitted_slurm_stub", formula=body.formula)
        return DftJobResponse.from_orm_job(job)
    else:
        user_id = uuid.UUID(payload["sub"]) if "sub" in payload else None
        job_id_str = _local_adapter.submit_job(structure, params, job_name=body.job_name)
        # Set created_by on the record created inside the adapter thread
        job = db.get(BackgroundJob, uuid.UUID(job_id_str))
        if job and user_id:
            job.created_by = user_id
            db.commit()
        db.refresh(job)
        logger.info("dft_job_submitted_local", formula=body.formula, job_id=job_id_str)
        return DftJobResponse.from_orm_job(job)


@router.get("", response_model=list[DftJobResponse])
async def list_dft_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """List DFT jobs submitted by the current user, newest first."""
    repo = JobRepository(db)
    user_id = uuid.UUID(payload["sub"]) if "sub" in payload else None
    if user_id:
        jobs = repo.list_by_user(user_id, job_type="dft_calculation", skip=skip, limit=limit)
    else:
        jobs = repo.list_by_type("dft_calculation", skip=skip, limit=limit)
    return [DftJobResponse.from_orm_job(j) for j in jobs]


@router.get("/{job_id}", response_model=DftJobResponse)
async def get_dft_job(
    job_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Get current status and results of a DFT job."""
    job = _get_job_or_404(db, job_id)
    return DftJobResponse.from_orm_job(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_dft_job(
    job_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Cancel a pending or running DFT job."""
    job = _get_job_or_404(db, job_id)
    if job.status in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=409,
            detail=f"El trabajo ya está en un estado terminal: '{job.status}'.",
        )
    adapter_name = (job.payload or {}).get("adapter", "local")
    adapter = _slurm_adapter if adapter_name == "slurm" else _local_adapter
    adapter.cancel_job(str(job_id))
    logger.info("dft_job_cancelled", job_id=str(job_id))


@router.post("/{job_id}/ingest", response_model=DftIngestResponse)
async def ingest_dft_results(
    job_id: uuid.UUID,
    body: DftIngestRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """
    Persist completed DFT results as MaterialProperty rows for the given material.
    """
    _get_job_or_404(db, job_id)
    ingester = DFTResultIngester(db)
    try:
        ingested = ingester.ingest(job_id, body.material_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    logger.info("dft_results_ingested", job_id=str(job_id), material_id=str(body.material_id))
    return DftIngestResponse(
        job_id=job_id,
        material_id=body.material_id,
        ingested_properties=ingested,
        message=f"Se incorporaron {len(ingested)} "
                f"{'propiedad' if len(ingested)==1 else 'propiedades'} "
                f"al material {body.material_id}.",
    )


@router.get("/{job_id}/inputs", response_model=GeneratedInputsResponse)
async def get_generated_inputs(
    job_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
):
    """Return the generated SLURM script and VASP input files for a SLURM job."""
    job = _get_job_or_404(db, job_id)
    p = job.payload or {}
    if p.get("adapter") != "slurm":
        raise HTTPException(status_code=400, detail="Los archivos de entrada solo están disponibles para trabajos SLURM.")
    slurm_job_id = p.get("slurm_job_id", "")
    raw = _slurm_adapter.get_generated_inputs(slurm_job_id)
    return GeneratedInputsResponse(
        job_id=str(job_id),
        formula=p.get("formula"),
        slurm_script=raw.get("slurm_script"),
        vasp_inputs=raw.get("vasp_inputs"),
        note=raw.get("note"),
    )
