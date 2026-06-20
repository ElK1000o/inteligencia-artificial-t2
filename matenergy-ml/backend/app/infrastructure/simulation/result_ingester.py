"""
Result ingester — Etapa 13.

Reads DFT job results from background_jobs and stores computed properties
as MaterialProperty records associated with the target material.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.infrastructure.database.models.job_models import BackgroundJob
from app.infrastructure.database.models.material_models import Material, MaterialProperty
from app.infrastructure.simulation.job_queue_interface import JobStatus


_PROPERTY_UNITS: dict[str, str] = {
    "formation_energy": "eV/atom",
    "energy_above_hull": "eV/atom",
    "band_gap": "eV",
    "total_energy": "eV",
}


class DFTResultIngester:
    """
    Transfers completed DFT job results into the materials database.

    Each numeric result field becomes a MaterialProperty row tagged with
    ``data_source='dft_local'`` or ``data_source='dft_slurm'`` depending on
    the job's adapter field in payload.
    """

    def __init__(self, db: Session):
        self.db = db

    def ingest(
        self,
        job_id: uuid.UUID,
        material_id: uuid.UUID,
    ) -> list[str]:
        """
        Persist DFT results from *job_id* as MaterialProperty rows for *material_id*.

        Returns a list of property names that were ingested.
        Raises ValueError if the job is not completed or already ingested.
        """
        job: Optional[BackgroundJob] = self.db.get(BackgroundJob, job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        if job.status != "completed":
            raise ValueError(
                f"Job {job_id} is not completed (status={job.status}). "
                "Wait for the calculation to finish before ingesting results."
            )

        material: Optional[Material] = self.db.get(Material, material_id)
        if not material:
            raise ValueError(f"Material {material_id} not found")

        result: dict = job.result or {}
        adapter = (job.payload or {}).get("adapter", "local")
        source = f"dft_{adapter}"

        ingested: list[str] = []
        for prop_name in ("formation_energy", "energy_above_hull", "band_gap", "total_energy"):
            value = result.get(prop_name)
            if value is None:
                continue

            # Avoid duplicate — skip if this property already has a DFT-sourced row
            existing = (
                self.db.query(MaterialProperty)
                .filter_by(
                    material_id=material_id,
                    property_name=prop_name,
                    data_source=source,
                )
                .first()
            )
            if existing:
                continue

            prop = MaterialProperty(
                id=uuid.uuid4(),
                material_id=material_id,
                property_name=prop_name,
                value=float(value),
                unit=_PROPERTY_UNITS.get(prop_name, ""),
                data_source=source,
            )
            self.db.add(prop)
            ingested.append(prop_name)

        # Tag job with ingestion metadata
        payload = dict(job.payload or {})
        payload["ingested_to_material"] = str(material_id)
        payload["ingested_properties"] = ingested
        job.payload = payload

        self.db.commit()
        return ingested
