"""
Abstract interface for DFT job queues — Etapa 13 stub.

Concrete implementations will wrap:
  - SLURM / PBS HPC schedulers
  - Local subprocess execution (for testing only)
  - Cloud HPC providers (AWS, Azure, GCP batch)

No actual DFT code is imported or executed here.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CalculationType(str, Enum):
    STATIC = "static"              # Single-point energy
    RELAX = "relax"                # Geometry optimization
    BAND_STRUCTURE = "band_structure"
    DOS = "dos"
    NEB = "neb"                    # Nudged elastic band (diffusion barrier)
    PHONON = "phonon"


@dataclass
class DFTInputParameters:
    """Parameters passed to a DFT calculation."""
    calculation_type: CalculationType
    encut: float = 520.0            # plane-wave cutoff energy (eV)
    kpoints_density: float = 1000.0 # k-point density (per Å⁻³)
    functional: str = "PBE"         # XC functional
    hubbard_u: dict[str, float] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class DFTResults:
    """Results returned from a completed DFT calculation."""
    job_id: str
    status: JobStatus
    total_energy: Optional[float] = None        # eV
    formation_energy: Optional[float] = None    # eV/atom
    energy_above_hull: Optional[float] = None   # eV/atom
    band_gap: Optional[float] = None            # eV
    is_magnetic: Optional[bool] = None
    structure_relaxed: Optional[Any] = None     # pymatgen Structure
    raw_output_path: Optional[str] = None
    error_message: Optional[str] = None


class DFTJobQueueInterface(ABC):
    """
    Abstract interface for submitting and monitoring DFT jobs.

    Implementations must override all abstract methods.
    """

    @abstractmethod
    def submit_job(
        self,
        structure: Any,  # pymatgen Structure
        parameters: DFTInputParameters,
        job_name: Optional[str] = None,
    ) -> str:
        """
        Submit a DFT calculation.

        Returns:
            job_id: Unique identifier for the submitted job.
        """
        ...

    @abstractmethod
    def get_job_status(self, job_id: str) -> JobStatus:
        """Return the current status of a submitted job."""
        ...

    @abstractmethod
    def get_job_results(self, job_id: str) -> DFTResults:
        """
        Retrieve results for a completed job.

        Raises:
            RuntimeError: If job is not yet completed.
        """
        ...

    @abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running or pending job. Returns True if successful."""
        ...
