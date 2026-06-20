"""
infrastructure/simulation — Atomistic simulation integration (Etapa 13).

Implemented:
  - DFTJobQueueInterface     abstract base (job_queue_interface.py)
  - LocalSimulationAdapter   ASE/EMT for metals + deterministic approx for others (local_adapter.py)
  - SlurmAdapter             SLURM+VASP stub: generates real inputs, no real submission (slurm_adapter.py)
  - DFTResultIngester        stores completed DFT results as MaterialProperty rows (result_ingester.py)

Stubs / future:
  - QuantumEspressoWorkflow  (TODO — QE input generation)
  - GpawWorkflow             (TODO — GPAW Python-native calculation)
  - CgcnnPredictor           (TODO — crystal graph neural network)

See docs/atomistic_simulation_roadmap.md for the full design.
"""
from app.infrastructure.simulation.job_queue_interface import (
    DFTJobQueueInterface,
    DFTInputParameters,
    DFTResults,
    JobStatus,
    CalculationType,
)
from app.infrastructure.simulation.local_adapter import LocalSimulationAdapter
from app.infrastructure.simulation.slurm_adapter import SlurmAdapter
from app.infrastructure.simulation.result_ingester import DFTResultIngester

__all__ = [
    "DFTJobQueueInterface",
    "DFTInputParameters",
    "DFTResults",
    "JobStatus",
    "CalculationType",
    "LocalSimulationAdapter",
    "SlurmAdapter",
    "DFTResultIngester",
]
