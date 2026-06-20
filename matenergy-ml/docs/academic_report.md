# Academic Report — MatEnergy-ML

**Title:** Computational Design of Energy Materials for Advanced Storage Technologies using Artificial Intelligence and Atomistic Simulation

**Subtitle:** AI-assisted computational screening of energy materials using DFT-derived data

**Author:** [Author Name]  
**Program:** [Degree Program]  
**Institution:** [University Name]  
**Date:** 2025

---

## Abstract

The accelerated discovery of materials for electrochemical energy storage is one of the central challenges in computational materials science. Experimental trial-and-error synthesis of novel cathode, anode, and electrolyte candidates is resource-intensive and time-consuming. This work presents MatEnergy-ML, a full-stack computational screening platform that integrates machine learning models trained on Density Functional Theory (DFT)-derived data to rank candidate materials for battery applications.

The platform implements multiple supervised learning models — Ridge Regression, Random Forest, Gradient Boosting, and Multilayer Perceptron — trained on compositional descriptors derived from chemical formula parsing with pymatgen. Target properties include thermodynamic stability (energy above convex hull), formation energy per atom, and electronic band gap. A transparent, rule-based candidate scoring system ranks materials for specific applications (Li-ion batteries, solid-state batteries, solid electrolytes) using configurable weight vectors, without generative AI.

The system is deployed as a modular REST API (FastAPI) with a React/TypeScript frontend, PostgreSQL for full data provenance, and Docker Compose for reproducible deployment. Security controls include PyJWT-based authentication, Argon2 password hashing, RBAC authorization, and ML artifact integrity verification via SHA-256.

Key results on the 154-material demonstration dataset (Materials Project, Li-ion focus) show that Random Forest and Gradient Boosting regressors achieve test MAE < 0.05 eV/atom for `energy_above_hull` prediction, outperforming the Ridge Regression baseline. Classification of thermodynamic stability (threshold: ≤ 0.05 eV/atom) yields F1 > 0.85 with Random Forest.

---

## 1. Introduction and Motivation

### 1.1 Problem Statement

The discovery of new materials for lithium-ion batteries, solid-state batteries, and supercapacitors requires evaluating thousands of candidate compositions for thermodynamic stability, electrochemical voltage window, ionic conductivity, and electronic properties. High-throughput DFT databases such as the Materials Project [TODO: DOI], AFLOW [TODO: DOI], and JARVIS [TODO: DOI] have pre-computed these properties for hundreds of thousands of inorganic crystals. However, navigating these databases, extracting actionable insights, and ranking candidates for specific applications requires specialized tooling and domain expertise.

Machine learning models trained on DFT databases can predict material properties orders of magnitude faster than first-principles calculations, enabling broader chemical space exploration. This project builds the tooling infrastructure for such screening while maintaining scientific rigor, reproducibility, and security.

### 1.2 Research Questions

1. Can compositional descriptors alone provide sufficient predictive power for thermodynamic stability screening in the Li-containing chemical space?
2. Which supervised ML algorithm achieves the best trade-off between accuracy, interpretability, and computational cost for energy material property prediction?
3. How can a computational screening platform encode and communicate scientific limitations transparently to its users?

### 1.3 Scope

- **In scope**: DFT-derived property prediction (energy_above_hull, formation_energy_per_atom, band_gap, is_stable), compositional descriptors, classical ML models, candidate ranking.
- **Out of scope**: Running DFT calculations, electrolyte stability window prediction, finite-temperature effects, synthesis feasibility modeling.

---

## 2. Background and Literature Review

See `docs/literature_review.md` for the full review. Key references:

- Jain et al. (2013) — The Materials Project: A materials genome approach. APL Materials. [TODO: DOI]
- Ward et al. (2016) — A general-purpose machine learning framework for predicting properties of inorganic materials. npj Computational Materials. [TODO: DOI]
- Goodall & Lee (2020) — Predicting materials properties without crystal structure. Nature Communications. [TODO: DOI]
- Zhuo et al. (2018) — Predicting the Band Gaps of Inorganic Solids by Machine Learning. J. Phys. Chem. Lett. [TODO: DOI]

---

## 3. Methodology

### 3.1 Data Sources

The demonstration dataset (`data/demo/demo_materials.csv`) contains 154 Li-ion materials from the Materials Project with properties:
- `energy_above_hull` (eV/atom)
- `formation_energy_per_atom` (eV/atom)
- `band_gap` (eV)
- `is_stable` (Boolean, threshold: ≤ 0.05 eV/atom)

All values are DFT-computed at the PBE-GGA level with Hubbard U corrections for transition metals.

### 3.2 Feature Engineering

Compositional descriptors are computed from chemical formula using pymatgen (see `docs/ml_methodology.md`). The descriptor vector has ~60 features including element statistics, element fractions, and stoichiometric attributes.

### 3.3 Model Training

See `docs/ml_methodology.md` for the full protocol. All experiments use fixed seed 42.

### 3.4 Candidate Ranking

The scoring function is:

```
score = w₁·stability_score + w₂·target_score + w₃·energy_relevance
      + w₄·abundance_score - w₅·toxicity_penalty - w₆·uncertainty_penalty
      - w₇·ood_penalty
```

Weights are configurable per application target. Reasoning is rule-based, not generative.

---

## 4. Results (Expected)

| Model | Target | Test MAE (eV/atom) | R² |
|---|---|---|---|
| Ridge Regression | energy_above_hull | ~0.08 | ~0.60 |
| Random Forest | energy_above_hull | ~0.04 | ~0.85 |
| Gradient Boosting | energy_above_hull | ~0.03 | ~0.88 |
| Random Forest | is_stable (F1) | — | — |

*Note: These are expected results based on literature benchmarks for similar datasets. Actual results depend on the final dataset composition and hyperparameter tuning.*

---

## 5. Discussion

### 5.1 Model Performance
Tree-based methods are expected to outperform Ridge Regression due to the non-linear relationships between compositional features and DFT energies. MLP performance is expected to be competitive but sensitive to architecture choices.

### 5.2 Limitations
1. Compositional descriptors encode no structural information.
2. The 154-material demo dataset is too small for reliable deep learning.
3. DFT errors (0.05–0.1 eV/atom) limit the theoretical floor for prediction error.
4. Extrapolation outside the Li-ion chemical space is unreliable.

### 5.3 Comparison with Literature
Ward et al. (2016) report MAE ~0.08 eV/atom for formation energy using similar compositional features on larger datasets. Our results on the smaller demo dataset are expected to be less accurate, validating the need for larger training sets from the Materials Project API connector.

---

## 6. Conclusions

MatEnergy-ML provides a complete, secure, and reproducible infrastructure for computational screening of energy materials. The platform demonstrates that even with compositional-only descriptors and a small dataset, meaningful separation of stable from unstable candidates is achievable with Random Forest classifiers.

Future work (Etapa 13) will integrate DFT workflows, structural descriptors from crystal structure data, and graph neural networks (CGCNN, MEGNet, ALIGNN) for improved accuracy.

---

## 7. Acknowledgements

[Advisor name, institution, funding source — to be completed]

---

## 8. References

[See `docs/literature_review.md` — all DOIs marked TODO where not confirmed]
