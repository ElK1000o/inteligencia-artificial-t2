"""
Local simulation adapter — Etapa 13.

Runs DFT-like calculations without an HPC cluster:
  - Elements in EMT_ELEMENTS (Al, Cu, Ag, Au, Ni, Pd, Pt, Zn, Cd, Hg): real ASE/EMT calculation.
  - All other materials: deterministic approximation seeded by formula hash,
    clearly labelled source='deterministic_approximation'.

Jobs run in daemon threads; status is persisted to the background_jobs table.
"""
from __future__ import annotations

import hashlib
import random
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.infrastructure.simulation.job_queue_interface import (
    CalculationType,
    DFTInputParameters,
    DFTJobQueueInterface,
    DFTResults,
    JobStatus,
)

# Module-level registry: job_id → (thread, cancel_event)
_active: dict[str, tuple[threading.Thread, threading.Event]] = {}
_lock = threading.Lock()

# EMT is limited to these bulk metallic elements
EMT_ELEMENTS = frozenset({"Al", "Cu", "Ag", "Au", "Ni", "Pd", "Pt", "Zn", "Cd", "Hg"})

# Approximate per-element formation energies (eV/atom) for the approximation path
_ELEM_REFS: dict[str, float] = {
    "Li": -1.90, "Na": -1.31, "K": -1.02, "Fe": -8.31, "Co": -7.09,
    "Ni": -5.77, "Cu": -3.72, "Mn": -9.04, "Ti": -7.77, "V": -8.94,
    "Cr": -9.51, "Zn": -1.26, "Al": -3.74, "O": -4.95, "S": -4.13,
    "P": -5.41, "Si": -5.42, "N": -8.33, "C": -9.22, "F": -1.91,
    "Cl": -1.84, "Mg": -1.59, "Ca": -1.97, "Ba": -1.92,
}


def _get_session():
    from app.infrastructure.database.session import SessionLocal
    return SessionLocal()


def _run_ase_emt(structure: Any, parameters: DFTInputParameters) -> dict:
    """Real ASE/EMT calculation for EMT-compatible metallic systems."""
    from ase.calculators.emt import EMT  # type: ignore[import]
    from ase.optimize import BFGS  # type: ignore[import]
    from pymatgen.io.ase import AseAtomsAdaptor

    atoms = AseAtomsAdaptor.get_atoms(structure)
    calc = EMT()
    atoms.calc = calc

    if parameters.calculation_type == CalculationType.RELAX:
        opt = BFGS(atoms, logfile=None)
        opt.run(fmax=0.05, steps=150)

    total_energy = float(atoms.get_potential_energy())
    n_atoms = len(atoms)

    # Formation energy relative to EMT elemental references
    from ase.calculators.emt import EMT as _EMT
    elem_energies: dict[str, float] = {}
    for sym in set(atoms.get_chemical_symbols()):
        from ase.build import bulk  # type: ignore[import]
        ref = bulk(sym)
        ref.calc = _EMT()
        elem_energies[sym] = float(ref.get_potential_energy()) / len(ref)

    symbols = atoms.get_chemical_symbols()
    ref_energy = sum(elem_energies.get(s, 0.0) for s in symbols)
    formation_energy = (total_energy - ref_energy) / n_atoms

    return {
        "total_energy": round(total_energy, 6),
        "formation_energy": round(formation_energy, 6),
        "energy_above_hull": round(max(0.0, formation_energy * 0.08), 6),
        "band_gap": 0.0,
        "is_magnetic": False,
        "source": "ase_emt",
        "calculator": "EMT (ASE)",
        "n_atoms": n_atoms,
    }


def _run_approximation(structure: Any, parameters: DFTInputParameters) -> dict:
    """
    Deterministic approximation for materials not supported by EMT.

    Seeded by the formula hash so the same material always gives the same result.
    Values are in physically plausible ranges but are NOT real DFT.
    """
    from pymatgen.core import Composition

    formula = structure.formula
    seed = int(hashlib.md5(formula.encode()).hexdigest(), 16) % (2**31)
    rng = random.Random(seed)

    comp = structure.composition
    n_atoms = comp.num_atoms
    elements = list(comp.elements)

    # Formation energy estimate: weighted average of element references + mixing term
    ref_total = sum(
        comp.get_atomic_fraction(el) * _ELEM_REFS.get(str(el), -5.0)
        for el in elements
    )
    mixing_correction = rng.uniform(-0.3, 0.1)
    formation_energy = round(ref_total + mixing_correction, 4)

    # Energy above hull: random but biased toward stability for Li-bearing materials
    has_li = any(str(el) == "Li" for el in elements)
    eah_max = 0.15 if has_li else 0.35
    energy_above_hull = round(rng.uniform(0.0, eah_max), 4)

    # Band gap: metals → 0, compounds with O/S → positive
    has_anion = any(str(el) in ("O", "S", "F", "N") for el in elements)
    band_gap = round(rng.uniform(0.5, 4.5), 3) if has_anion else round(rng.uniform(0.0, 0.3), 3)

    total_energy = round(formation_energy * n_atoms - rng.uniform(0.1, 1.0), 4)

    return {
        "total_energy": total_energy,
        "formation_energy": formation_energy,
        "energy_above_hull": energy_above_hull,
        "band_gap": band_gap,
        "is_magnetic": rng.random() < 0.2,
        "source": "deterministic_approximation",
        "calculator": "Empirical + composition heuristics (NOT real DFT)",
        "n_atoms": int(n_atoms),
        "warning": (
            "These values are deterministic approximations seeded by formula hash. "
            "They are NOT the result of a real DFT calculation. "
            "Connect an HPC cluster with VASP or Quantum ESPRESSO for production use."
        ),
    }


def _worker(
    job_id_str: str,
    structure: Any,
    parameters: DFTInputParameters,
    cancel_event: threading.Event,
) -> None:
    """Background thread: runs the calculation and updates the DB."""
    job_id = uuid.UUID(job_id_str)

    # Mark running
    with _get_session() as db:
        from app.infrastructure.database.models.job_models import BackgroundJob
        job = db.get(BackgroundJob, job_id)
        if job:
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            db.commit()

    try:
        # Simulate setup delay
        for i in range(10):
            if cancel_event.is_set():
                _finalize_cancelled(job_id_str)
                return
            time.sleep(0.5)

        elements = {str(el) for el in structure.composition.elements}
        if elements.issubset(EMT_ELEMENTS):
            result = _run_ase_emt(structure, parameters)
        else:
            result = _run_approximation(structure, parameters)

        if cancel_event.is_set():
            _finalize_cancelled(job_id_str)
            return

        with _get_session() as db:
            from app.infrastructure.database.models.job_models import BackgroundJob
            job = db.get(BackgroundJob, job_id)
            if job:
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.result = result
                job.progress_pct = 100.0
                db.commit()

    except Exception as exc:
        with _get_session() as db:
            from app.infrastructure.database.models.job_models import BackgroundJob
            job = db.get(BackgroundJob, job_id)
            if job:
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                job.error_message = str(exc)
                db.commit()
    finally:
        with _lock:
            _active.pop(job_id_str, None)


def _finalize_cancelled(job_id_str: str) -> None:
    job_id = uuid.UUID(job_id_str)
    with _get_session() as db:
        from app.infrastructure.database.models.job_models import BackgroundJob
        job = db.get(BackgroundJob, job_id)
        if job:
            job.status = "cancelled"
            job.completed_at = datetime.now(timezone.utc)
            db.commit()


class LocalSimulationAdapter(DFTJobQueueInterface):
    """
    Local DFT simulation adapter (Etapa 13 — development / demo use).

    No HPC or external DFT software required.
    Production deployment should replace this with SlurmAdapter + VaspWorkflow.
    """

    def submit_job(
        self,
        structure: Any,
        parameters: DFTInputParameters,
        job_name: Optional[str] = None,
    ) -> str:
        job_id = str(uuid.uuid4())

        with _get_session() as db:
            from app.infrastructure.database.models.job_models import BackgroundJob
            job = BackgroundJob(
                id=uuid.UUID(job_id),
                job_type="dft_calculation",
                status="pending",
                payload={
                    "formula": structure.formula,
                    "n_atoms": int(structure.composition.num_atoms),
                    "calculation_type": parameters.calculation_type.value,
                    "functional": parameters.functional,
                    "encut": parameters.encut,
                    "job_name": job_name or structure.reduced_formula,
                    "adapter": "local",
                },
            )
            db.add(job)
            db.commit()

        cancel_event = threading.Event()
        thread = threading.Thread(
            target=_worker,
            args=(job_id, structure, parameters, cancel_event),
            daemon=True,
            name=f"dft-{job_id[:8]}",
        )
        with _lock:
            _active[job_id] = (thread, cancel_event)
        thread.start()
        return job_id

    def get_job_status(self, job_id: str) -> JobStatus:
        with _get_session() as db:
            from app.infrastructure.database.models.job_models import BackgroundJob
            job = db.get(BackgroundJob, uuid.UUID(job_id))
            if not job:
                raise KeyError(f"Job {job_id} not found")
            return JobStatus(job.status)

    def get_job_results(self, job_id: str) -> DFTResults:
        with _get_session() as db:
            from app.infrastructure.database.models.job_models import BackgroundJob
            job = db.get(BackgroundJob, uuid.UUID(job_id))
            if not job:
                raise KeyError(f"Job {job_id} not found")
            if job.status != "completed":
                raise RuntimeError(f"Job {job_id} is not completed (status={job.status})")
            r = job.result or {}
            return DFTResults(
                job_id=job_id,
                status=JobStatus.COMPLETED,
                total_energy=r.get("total_energy"),
                formation_energy=r.get("formation_energy"),
                energy_above_hull=r.get("energy_above_hull"),
                band_gap=r.get("band_gap"),
                is_magnetic=r.get("is_magnetic"),
                error_message=r.get("warning"),
            )

    def cancel_job(self, job_id: str) -> bool:
        with _lock:
            entry = _active.get(job_id)
        if entry:
            _, cancel_event = entry
            cancel_event.set()
            return True
        # Job may already be done; mark cancelled in DB if still pending/running
        with _get_session() as db:
            from app.infrastructure.database.models.job_models import BackgroundJob
            job = db.get(BackgroundJob, uuid.UUID(job_id))
            if job and job.status in ("pending", "running"):
                job.status = "cancelled"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
                return True
        return False
