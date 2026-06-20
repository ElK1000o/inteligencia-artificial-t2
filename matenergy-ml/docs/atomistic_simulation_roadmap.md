# Atomistic Simulation Roadmap — MatEnergy-ML (Etapa 13)

## Status: IMPLEMENTED (Session 8, 2026-06-09)

Etapa 13 is now fully implemented. The platform supports end-to-end DFT job management
with two adapters: a local ASE/EMT adapter (real calculations for metallic systems,
deterministic approximation for others) and a SLURM stub (generates real VASP input
files and SLURM scripts for HPC deployment). All jobs are tracked in the database.

### Implemented components (session 8)

```
infrastructure/simulation/
├── __init__.py                  ✅ Exports all adapters
├── job_queue_interface.py       ✅ Abstract interface
├── local_adapter.py             ✅ ASE/EMT + deterministic approximation
├── slurm_adapter.py             ✅ SLURM stub + VASP input generation
└── result_ingester.py           ✅ DFT results → MaterialProperty rows

infrastructure/database/
├── models/job_models.py         ✅ BackgroundJob ORM
└── repositories/job_repository.py ✅ CRUD

api/v1/dft_routes.py             ✅ 6 endpoints (see below)
schemas/dft_schemas.py           ✅ Pydantic schemas

frontend/src/
├── api/dft.ts                   ✅ API client
└── pages/DftJobsPage.tsx        ✅ Full UI with submit + queue + results
```

### Implemented API endpoints
```
POST   /api/v1/dft-jobs                    — Submit a DFT calculation (202 Accepted)
GET    /api/v1/dft-jobs                    — List jobs (current user)
GET    /api/v1/dft-jobs/{job_id}           — Poll status + results
DELETE /api/v1/dft-jobs/{job_id}           — Cancel pending/running job
POST   /api/v1/dft-jobs/{job_id}/ingest    — Persist results as MaterialProperty
GET    /api/v1/dft-jobs/{job_id}/inputs    — Download SLURM script + VASP inputs
```

### Still TODO (future sessions)
- QE (Quantum ESPRESSO) workflow adapter
- GPAW workflow adapter
- Real SLURM SSH submission (requires paramiko, HPC credentials)
- CGCNN / ALIGNN graph neural network descriptors

---

## Original Design

This section preserves the original design specification for reference.

---

## 1. Architecture Extension

### 1.1 New Module: `infrastructure/simulation/`

```
infrastructure/simulation/
├── __init__.py
├── job_queue_interface.py      — Abstract interface ✅ DONE
├── local_adapter.py            — ASE/EMT local simulation ✅ DONE
├── slurm_adapter.py            — SLURM HPC job submission ✅ DONE (stub)
├── result_ingester.py          — Parse DFT output → DB material properties ✅ DONE
├── quantum_espresso_workflow.py— QE input/output handling (TODO)
└── gpaw_workflow.py            — GPAW workflow (TODO)
```

### 1.2 API Routes
```
POST   /api/v1/dft-jobs                    ✅ DONE
GET    /api/v1/dft-jobs                    ✅ DONE
GET    /api/v1/dft-jobs/{job_id}           ✅ DONE
DELETE /api/v1/dft-jobs/{job_id}           ✅ DONE
POST   /api/v1/dft-jobs/{job_id}/ingest    ✅ DONE
GET    /api/v1/dft-jobs/{job_id}/inputs    ✅ DONE
```

### 1.3 Background Jobs Table
The `background_jobs` table (added in migration 002) tracks:
- DFT job submission time
- HPC job ID (in payload JSONB)
- Status polling results
- Result ingestion status

---

## 2. DFT Software Integration

### 2.1 VASP (Vienna Ab Initio Simulation Package)
- **License required**: Commercial license necessary for VASP.
- **pymatgen integration**: `pymatgen.io.vasp` provides INCAR, POSCAR, KPOINTS, and POTCAR generation.
- **Workflow**: MatEnergy-ML generates VASP input → submits to SLURM → polls for completion → parses vasprun.xml.

### 2.2 Quantum ESPRESSO (QE)
- **License**: Open-source (GPL).
- **pymatgen integration**: `pymatgen.io.espresso` provides input card generation.
- **Recommended for**: Band structure, DOS, phonon calculations.

### 2.3 GPAW
- **License**: Open-source (GPL).
- **Python-native**: Can be called directly from Python without I/O files.
- **Recommended for**: Small molecules, testing workflows without HPC.

---

## 3. HPC Integration

### 3.1 SLURM
```python
# Planned implementation in slurm_adapter.py
class SlurmAdapter(DFTJobQueueInterface):
    def submit_job(self, structure, parameters, job_name=None) -> str:
        # 1. Write structure to POSCAR/CIF
        # 2. Generate INCAR/KPOINTS via pymatgen
        # 3. Write SLURM batch script
        # 4. subprocess.run(["sbatch", script]) → job_id
        ...
```

### 3.2 Security Considerations
- DFT jobs run in isolated user accounts on HPC, not as the web server user.
- Input files are validated before submission; no user-controlled content reaches the HPC.
- Output files are parsed in a sandboxed subprocess.
- Resource limits (wall time, memory) are enforced per job.

---

## 4. Graph Neural Networks for Structure-Based Prediction

Once structural data is available (from Etapa 13 DFT outputs), graph neural networks can replace compositional descriptors:

### 4.1 CGCNN (Crystal Graph Convolutional Neural Networks)
- Requires: Crystal structure (pymatgen Structure object)
- Repository: https://github.com/txie-93/cgcnn
- Expected MAE for energy_above_hull: ~0.02 eV/atom (vs ~0.04 for RF with compositional features)

### 4.2 MEGNet
- Repository: https://github.com/materialsvirtuallab/megnet
- Includes graph-level state attributes (temperature, pressure)

### 4.3 ALIGNN (Atomistic Line Graph Neural Network)
- Repository: https://github.com/usnistgov/alignn
- State-of-the-art on JARVIS benchmark; included in JARVIS-tools

### 4.4 Integration Plan
- GNN models will be registered as a new `ModelType` enum value.
- The `ModelTrainer` class will be extended with a `GNNTrainer` subclass.
- Input will be pymatgen Structure objects from the `material_structures` table.
- Inference will use the same `PredictMaterialPropertyUseCase` interface.

---

## 5. Timeline Estimate

| Task | Estimated Effort | Prerequisites |
|---|---|---|
| SLURM adapter | 2 weeks | HPC access |
| VASP workflow | 2 weeks | VASP license |
| Result ingester | 1 week | DFT outputs |
| CGCNN integration | 2 weeks | GPU hardware |
| MEGNet integration | 1 week | CGCNN done |
| Full Etapa 13 testing | 2 weeks | All above |

Total: ~10 weeks of development work.

---

## 6. What Does NOT Change in Existing Architecture

- The existing `ImportMaterialDatasetUseCase` will accept DFT-generated CSV as normal input.
- The `DescriptorSet` system will add a new `gnn_structural` descriptor type.
- The `ModelVersion` / `ModelArtifact` registry is already designed for GNN checkpoints.
- The `PredictMaterialPropertyUseCase` calls `Predictor.predict_single()` — the interface is model-agnostic.
- Security controls (artifact hash verification, RBAC) apply equally to GNN models.

---

*Etapa 13 is not part of the mandatory thesis scope. It represents the natural evolution of the platform toward full computational materials discovery.*
