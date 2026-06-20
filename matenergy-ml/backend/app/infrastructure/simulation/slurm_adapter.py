"""
SLURM HPC adapter stub — Etapa 13.

Generates real SLURM submission scripts and VASP/QE input files.
Actual job submission requires:
  - SSH access to an HPC cluster running SLURM.
  - VASP license (commercial) or Quantum ESPRESSO (GPL).
  - Set SLURM_HOST, SLURM_USER, SLURM_WORKDIR in environment.

In the current stub implementation, submit_job() logs the generated script
and returns a synthetic job ID without connecting to any cluster.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from app.infrastructure.simulation.job_queue_interface import (
    CalculationType,
    DFTInputParameters,
    DFTJobQueueInterface,
    DFTResults,
    JobStatus,
)

_SLURM_TEMPLATE = """\
#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --nodes=1
#SBATCH --ntasks-per-node={n_cores}
#SBATCH --time={walltime}
#SBATCH --mem={mem_gb}GB
#SBATCH --output={job_name}_%j.out
#SBATCH --error={job_name}_%j.err

module load vasp/6.3.0
module load intel/2023.1
module load mpi/intel/2023.1

cd $SLURM_SUBMIT_DIR
mpirun -np {n_cores} vasp_std > vasp.log 2>&1
"""

# In-memory store for stub jobs (lost on restart; production should use DB)
_stub_jobs: dict[str, dict] = {}


class SlurmAdapter(DFTJobQueueInterface):
    """
    SLURM + VASP adapter.

    Stub: generates real input files and SLURM scripts but does NOT submit.
    Replace _submit_via_ssh() with a real paramiko/fabric call for production.
    """

    def __init__(
        self,
        host: str = "hpc.cluster.example.edu",
        user: str = "researcher",
        workdir: str = "/scratch/matenergy",
        n_cores: int = 32,
        walltime: str = "04:00:00",
        mem_gb: int = 64,
    ):
        self.host = host
        self.user = user
        self.workdir = workdir
        self.n_cores = n_cores
        self.walltime = walltime
        self.mem_gb = mem_gb

    def submit_job(
        self,
        structure: Any,
        parameters: DFTInputParameters,
        job_name: Optional[str] = None,
    ) -> str:
        job_name = (job_name or structure.reduced_formula).replace(" ", "_")
        fake_job_id = f"slurm_{str(uuid.uuid4())[:8]}"

        slurm_script = _SLURM_TEMPLATE.format(
            job_name=job_name,
            n_cores=self.n_cores,
            walltime=self.walltime,
            mem_gb=self.mem_gb,
        )

        vasp_inputs = self._generate_vasp_inputs(structure, parameters)

        _stub_jobs[fake_job_id] = {
            "status": JobStatus.PENDING,
            "formula": structure.formula,
            "slurm_script": slurm_script,
            "vasp_inputs": vasp_inputs,
            "note": (
                "STUB: no real HPC submission. "
                "Connect SSH credentials (SLURM_HOST, SLURM_USER) for production use."
            ),
        }
        return fake_job_id

    def get_job_status(self, job_id: str) -> JobStatus:
        if job_id not in _stub_jobs:
            raise KeyError(f"Slurm job {job_id} not found in stub registry")
        return _stub_jobs[job_id]["status"]

    def get_job_results(self, job_id: str) -> DFTResults:
        if job_id not in _stub_jobs:
            raise KeyError(f"Slurm job {job_id} not found in stub registry")
        if _stub_jobs[job_id]["status"] != JobStatus.COMPLETED:
            raise RuntimeError(f"Job {job_id} is not completed")
        return DFTResults(job_id=job_id, status=JobStatus.COMPLETED)

    def cancel_job(self, job_id: str) -> bool:
        if job_id in _stub_jobs:
            _stub_jobs[job_id]["status"] = JobStatus.CANCELLED
            return True
        return False

    def get_generated_inputs(self, job_id: str) -> dict:
        """Return the generated SLURM + VASP inputs for inspection."""
        return _stub_jobs.get(job_id, {})

    def _generate_vasp_inputs(self, structure: Any, parameters: DFTInputParameters) -> dict:
        """Generate VASP-compatible input files using pymatgen."""
        try:
            from pymatgen.io.vasp.inputs import Incar, Kpoints, Poscar
            from pymatgen.io.vasp.sets import MPRelaxSet, MPStaticSet

            if parameters.calculation_type == CalculationType.RELAX:
                vis = MPRelaxSet(structure)
            else:
                vis = MPStaticSet(structure)

            poscar = Poscar(structure).get_string()
            incar_dict = vis.incar.as_dict()
            incar_dict["ENCUT"] = parameters.encut
            if parameters.hubbard_u:
                incar_dict["LDAU"] = True
                incar_dict["LDAUTYPE"] = 2
                incar_dict["LDAUU"] = [
                    parameters.hubbard_u.get(str(el), 0.0)
                    for el in structure.composition.elements
                ]
            kpoints = Kpoints.automatic_density(structure, parameters.kpoints_density)
            return {
                "POSCAR": poscar,
                "INCAR": str(Incar(incar_dict)),
                "KPOINTS": str(kpoints),
                "note": "POTCAR omitted — requires VASP license.",
            }
        except Exception as exc:
            return {"error": f"Input generation failed: {exc}"}
