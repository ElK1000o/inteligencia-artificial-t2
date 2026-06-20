# Model Card Template — MatEnergy-ML

*Copy and fill this template for each trained model. Replace all [PLACEHOLDER] values.*

---

## Model Information

| Field | Value |
|---|---|
| **Model Name** | [e.g., random_forest_energy_above_hull_v20250101] |
| **Model Type** | [Ridge / Random Forest / Gradient Boosting / MLP] |
| **Task** | [Regression / Classification] |
| **Target Property** | [energy_above_hull / formation_energy_per_atom / band_gap / is_stable] |
| **Version Tag** | [v20250101120000] |
| **MatEnergy-ML Version** | 0.1.0 |
| **Creation Date** | [YYYY-MM-DD] |
| **SHA-256 (artifact)** | [64-character hash] |

---

## Intended Use

This model is intended for **computational screening** of energy materials as part of the MatEnergy-ML pipeline. It predicts `[target_property]` for materials described by compositional descriptors.

**Appropriate use cases:**
- Rapid initial screening of candidate materials for [application_target]
- Prioritizing materials for further DFT calculation or experimental synthesis
- Comparative analysis of chemical trends

**Out-of-scope uses:**
- Direct engineering decisions without experimental validation
- Prediction of materials far outside the training chemical space
- Replacement of accurate DFT calculations for property determination

---

## Training Data

| Field | Value |
|---|---|
| **Dataset Name** | [dataset_name] |
| **Dataset SHA-256** | [hash] |
| **Data Source** | [Materials Project / JARVIS / CSV local] |
| **Number of training samples** | [N_train] |
| **Number of test samples** | [N_test] |
| **Chemical systems covered** | [e.g., Li-Fe-O, Li-Mn-O, Li-P-S, ...] |
| **Property range (train)** | [min] to [max] [unit] |
| **Class balance (if classification)** | [stable: X%, unstable: Y%] |

---

## Features

| Feature Set | N Features | Description |
|---|---|---|
| Compositional (composition-only) | 57 | avg_atomic_number, electronegativity stats, element fractions, stoichiometric norms |
| Structural (if used) | 12 | density, lattice parameters, space group, crystal system |
| **Total** | **[57 or 69]** | |

**Descriptor set version**: [e.g., default_1.0.0]

**Preprocessing**: Median imputation for missing values; RobustScaler for models requiring scaling (Ridge, MLP, SVR).

---

## Evaluation Metrics

### Regression (if applicable)

| Metric | Train | Test | CV (5-fold) |
|---|---|---|---|
| MAE (eV/atom) | [value] | [value] | [value ± std] |
| RMSE (eV/atom) | [value] | [value] | — |
| R² | [value] | [value] | — |
| Median AE | [value] | [value] | — |

### Classification (if applicable)

| Metric | Train | Test |
|---|---|---|
| Accuracy | [value] | [value] |
| Balanced Accuracy | [value] | [value] |
| F1 (macro) | [value] | [value] |
| ROC-AUC | [value] | [value] |

---

## Top Feature Importances

| Rank | Feature | Importance |
|---|---|---|
| 1 | [feature_name] | [value] |
| 2 | [feature_name] | [value] |
| 3 | [feature_name] | [value] |
| ... | ... | ... |

---

## Limitations

1. **Extrapolation**: Predictions for compositions outside the training chemical space are unreliable. Out-of-domain warnings are issued automatically.
2. **DFT errors**: The training targets carry PBE functional errors (band gap underestimation ~30–50%, correlation errors for d-electron systems).
3. **Structural information**: Composition-only descriptors cannot distinguish polymorphs.
4. **Uncertainty**: Confidence scores are based on ensemble spread (RF/GBM) and are not formally calibrated probability estimates.

---

## Ethical Considerations

This model is developed for academic research in computational materials science. No personal data is involved. Results should not be used to make safety-critical decisions without experimental validation.

---

## Contact

For questions about this model, contact the thesis author or raise an issue in the MatEnergy-ML repository.
