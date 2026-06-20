# MatEnergy-ML — Connection to Thesis Research

**Thesis Title**: "Diseño computacional de materiales energéticos para tecnologías de almacenamiento avanzado mediante inteligencia artificial y simulación atomística"

**Platform**: MatEnergy-ML v0.1.0

---

## 1. How MatEnergy-ML Supports the Thesis

MatEnergy-ML is the primary computational artifact of this thesis. It serves as a concrete, working demonstration of the proposed methodology for AI-accelerated computational screening of energy materials. The platform integrates:

1. **DFT-derived data management**: Structured ingestion, validation, and storage of precomputed DFT properties from public databases (Materials Project, JARVIS)
2. **Chemical descriptor engineering**: Systematic computation of composition-based and structure-based feature vectors using pymatgen and custom pipelines
3. **Machine learning models**: Reproducible training and evaluation of multiple regression and classification models for thermodynamic stability prediction
4. **Transparent candidate ranking**: Rule-based, explainable scoring system for energy material candidates — aligned with the thesis requirement for interpretable, non-generative AI
5. **Academic-grade reproducibility**: Fixed random seeds, SHA-256 artifact hashing, dataset versioning, and Alembic migrations ensure full computational reproducibility

---

## 2. Thesis Objectives Addressed

| Thesis Objective | MatEnergy-ML Component |
|---|---|
| Computational screening of candidate battery materials | Candidate ranking engine with 7-component weighted scoring |
| AI-assisted property prediction | ML pipeline: Ridge, RF, GBM, MLP for regression/classification |
| DFT data integration | Dataset pipeline with Materials Project and JARVIS connectors |
| Feature engineering for energy materials | Compositional (57 features) + structural (12 features) descriptors |
| Validation and reproducibility | SHA-256 hashing, fixed seeds, Alembic migrations, audit logs |
| Security and data integrity | RBAC, JWT, artifact integrity, security event logging |

---

## 3. Alignment with the DFT–ML Paradigm

The thesis proposes a two-stage approach:

**Stage 1 (implemented in MatEnergy-ML)**: Use precomputed DFT data from public repositories as the ground truth for training ML surrogate models. This dramatically reduces the computational cost of screening by replacing DFT calculations with fast ML predictions.

**Stage 2 (planned — Etapa 13)**: Perform targeted DFT calculations on top-ranked candidates identified by Stage 1, using VASP, Quantum ESPRESSO, or GPAW through an external workflow engine. This closes the loop between ML screening and atomistic validation.

MatEnergy-ML's architecture explicitly prepares for Stage 2:
- The `DataSource` model supports DFT-calculated vs. ML-predicted properties
- The `material_structures` table stores CIF/POSCAR-compatible structure data
- The external connector module is designed to receive data from DFT workflow outputs
- The infrastructure is decoupled from specific DFT codes

---

## 4. Scientific Contributions

MatEnergy-ML enables the following academic contributions:

1. **Screening study**: A systematic comparison of ML model performance for predicting `energy_above_hull` and `formation_energy_per_atom` across a curated Li-ion battery materials dataset
2. **Descriptor analysis**: Quantitative evaluation of which compositional features are most predictive of thermodynamic stability (feature importance analysis)
3. **Candidate identification**: A ranked list of computationally promising battery materials for experimental follow-up
4. **Platform methodology**: A reusable, documented framework for computational materials screening that other research groups can deploy

---

## 5. Planned Evolution Toward Full Thesis Scope

The current MatEnergy-ML (Etapa 1–12) covers the ML screening layer. The full thesis scope includes:

### Etapa 13: Atomistic Simulation Integration

- **Job queue system**: Integration with a task queue (Celery + Redis or SLURM) for managing DFT calculation jobs
- **HPC interface**: SSH-based submission to university HPC cluster or cloud VMs
- **DFT workflow engine**: VASP/QE input file generation, convergence checking, output parsing
- **Property extraction**: Automatic extraction of optimized structures, energies, and electronic properties
- **Database update**: Parsed DFT results fed back into MatEnergy-ML's materials database
- **Graph neural networks**: Optional integration of CGCNN or ALIGNN for structure-property prediction without explicit descriptor engineering

This roadmap is documented in `docs/technical_architecture.md` (Section 9: Future Extensions).

---

## 6. Limitations Relevant to Thesis

The following limitations must be explicitly acknowledged in the thesis:

1. All ML training data derives from DFT calculations using the PBE functional — systematic errors propagate into predictions
2. The platform does not replace experimental synthesis and characterization
3. Compositional descriptors cannot distinguish polymorphs
4. Electrochemical properties (voltage, capacity, conductivity) require dedicated simulations not yet integrated
5. The candidate ranking is transparent and rule-based but involves subjective weight choices

See `docs/limitations.md` for a full treatment.

---

## 7. Citation

When citing MatEnergy-ML in the thesis or publications:

```
MatEnergy-ML: AI-assisted computational screening of energy materials using DFT-derived data.
[Author Name], [Year]. GitHub: [repository URL].
```

The platform's methodology section (`docs/ml_methodology.md`) and database design (`docs/database_design.md`) are suitable for direct inclusion or adaptation in the thesis Methods chapter.
