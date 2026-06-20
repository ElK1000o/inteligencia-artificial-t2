"""Pydantic schemas for DFT job endpoints (Etapa 13)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class DftJobSubmitRequest(BaseModel):
    formula: str = Field(..., description="Chemical formula, e.g. LiFePO4")
    structure_json: Optional[dict] = Field(
        None,
        description=(
            "Pymatgen-serialised structure (dict from Structure.as_dict()). "
            "If omitted the platform attempts to fetch the structure from Materials Project."
        ),
    )
    calculation_type: str = Field(
        "static",
        description="One of: static, relax, band_structure, dos",
    )
    functional: str = Field("PBE", description="XC functional: PBE, PBE+U, HSE06")
    encut: float = Field(520.0, ge=200.0, le=900.0, description="Plane-wave cutoff (eV)")
    kpoints_density: float = Field(1000.0, ge=100.0, description="K-point density (per Å⁻³)")
    hubbard_u: dict[str, float] = Field(
        default_factory=dict,
        description="Hubbard U values per element, e.g. {'Fe': 5.3}",
    )
    adapter: str = Field(
        "local",
        description="Simulation adapter: 'local' (ASE/EMT or approximation) or 'slurm' (HPC stub)",
    )
    job_name: Optional[str] = Field(None, description="Human-readable job label")


class DftJobResultResponse(BaseModel):
    total_energy: Optional[float] = None
    formation_energy: Optional[float] = None
    energy_above_hull: Optional[float] = None
    band_gap: Optional[float] = None
    is_magnetic: Optional[bool] = None
    source: Optional[str] = None
    calculator: Optional[str] = None
    n_atoms: Optional[int] = None
    warning: Optional[str] = None


class DftJobResponse(BaseModel):
    id: uuid.UUID
    job_type: str
    status: str
    formula: Optional[str] = None
    calculation_type: Optional[str] = None
    adapter: Optional[str] = None
    job_name: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress_pct: Optional[float] = None
    error_message: Optional[str] = None
    result: Optional[DftJobResultResponse] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_job(cls, job: Any) -> "DftJobResponse":
        payload: dict = job.payload or {}
        result_raw: dict = job.result or {}
        result_obj = DftJobResultResponse(**result_raw) if result_raw else None
        return cls(
            id=job.id,
            job_type=job.job_type,
            status=job.status,
            formula=payload.get("formula"),
            calculation_type=payload.get("calculation_type"),
            adapter=payload.get("adapter"),
            job_name=payload.get("job_name"),
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            progress_pct=job.progress_pct,
            error_message=job.error_message,
            result=result_obj,
        )


class DftIngestRequest(BaseModel):
    material_id: uuid.UUID = Field(
        ..., description="Target material to attach the DFT results to"
    )


class DftIngestResponse(BaseModel):
    job_id: uuid.UUID
    material_id: uuid.UUID
    ingested_properties: list[str]
    message: str


class GeneratedInputsResponse(BaseModel):
    job_id: str
    formula: Optional[str] = None
    slurm_script: Optional[str] = None
    vasp_inputs: Optional[dict] = None
    note: Optional[str] = None
