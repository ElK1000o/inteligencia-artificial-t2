# ML Methodology — MatEnergy-ML

## 1. Problem Framing

MatEnergy-ML addresses two complementary ML tasks over DFT-computed material data:

### 1.1 Regression
Predict continuous material properties:
- `energy_above_hull` (eV/atom) — thermodynamic stability relative to competing phases
- `formation_energy_per_atom` (eV/atom) — energy released during synthesis from elemental references
- `band_gap` (eV) — electronic band gap

### 1.2 Classification
- `is_stable` — binary label derived from `energy_above_hull ≤ 0.05 eV/atom`

---

## 2. Feature Engineering

### 2.1 Compositional Descriptors
Computed from the chemical formula alone using pymatgen:

| Descriptor | Description |
|---|---|
| `n_elements` | Number of distinct elements |
| `avg_atomic_number` | Composition-weighted mean atomic number |
| `avg_atomic_mass` | Composition-weighted mean atomic mass |
| `avg_electronegativity` | Composition-weighted mean Pauling electronegativity |
| `electronegativity_range` | max − min electronegativity across elements |
| `avg_atomic_radius` | Composition-weighted mean atomic radius (Å) |
| `frac_{El}` | Atomic fraction of Li, Cu, O, S, P, Fe, Mn, Co, Ni |
| `frac_transition_metals` | Total fraction of transition metal atoms |
| `{stat}_{prop}` | max/min/mean/std of elemental properties (Z, mass, X, r) |

**Limitations**: Compositional descriptors contain no structural information.
Two polymorphs of the same formula are indistinguishable.

### 2.2 Structural Descriptors (when crystal structure available)
- Density (g/cm³)
- Volume per atom (Å³/atom)
- Space group number and crystal system
- Lattice parameters (a, b, c, α, β, γ)
- Nearest-neighbor statistics

**Limitations**: Requires DFT-relaxed structure; not available for hypothetical materials.

---

## 3. Preprocessing Pipeline

### 3.1 Data Cleaning
1. Parse formula with pymatgen; reject invalid formulas.
2. Validate property values against physical bounds.
3. Remove exact duplicate (formula, dataset) pairs.
4. Flag and reject rows with NaN targets.
5. Detect and remove constant features (zero variance).
6. Check for target leakage (feature name == target name).

### 3.2 Imputation
- Numerical NaN features: median imputation (scikit-learn `SimpleImputer`).
- No imputation for target variables — rows with missing target are excluded.

### 3.3 Scaling
- `StandardScaler` applied inside the sklearn `Pipeline` to prevent test-set leakage.
- Ridge Regression and MLP Regressor require scaling; tree-based methods do not but scaling is applied uniformly for pipeline consistency.

### 3.4 Train / Test Split
- Stratified split for classification tasks (preserves class balance).
- Fixed `random_state=42` (FIXED_RANDOM_SEED constant) for reproducibility.
- Default test fraction: 20%.
- Duplicate check performed **before** split to prevent contamination.

---

## 4. Model Selection

### 4.1 Regression Models

| Model | Strengths | Limitations |
|---|---|---|
| Ridge Regression | Fast, interpretable, baseline | Assumes linearity |
| Random Forest Regressor | Handles non-linearity, robust | Cannot extrapolate beyond training range |
| Gradient Boosting Regressor | Often best accuracy | Slower, hyperparameter-sensitive |
| MLP Regressor | Flexible, learns complex patterns | Requires tuning, no feature importance |
| SVR (optional) | Effective in high dimensions | Slow for n > 5000 |
| Gaussian Process Regressor (optional) | Native uncertainty estimates | O(n³) training, n < 1000 only |

### 4.2 Classification Models

| Model | Strengths | Limitations |
|---|---|---|
| Logistic Regression | Baseline, calibrated probabilities | Linear boundary |
| Random Forest Classifier | Robust, balanced class handling | No probability calibration |
| Gradient Boosting Classifier | Often top accuracy | Not calibrated by default |
| MLP Classifier | Flexible | Not calibrated by default |

---

## 5. Evaluation Protocol

### 5.1 Regression Metrics

| Metric | Formula | Interpretation |
|---|---|---|
| MAE | mean(|y − ŷ|) | Average absolute error in original units (eV/atom) |
| RMSE | sqrt(mean((y − ŷ)²)) | Penalizes large errors more than MAE |
| R² | 1 − SS_res/SS_tot | Fraction of variance explained; 1 = perfect |
| Median AE | median(|y − ŷ|) | Robust to outliers |

### 5.2 Classification Metrics

| Metric | Notes |
|---|---|
| Accuracy | Misleading under class imbalance |
| Balanced Accuracy | Mean recall per class; preferred for imbalanced data |
| Precision / Recall / F1 | Per-class and macro-averaged |
| ROC-AUC | Overall discrimination ability |
| PR-AUC | Preferred when positive class is rare |
| Confusion Matrix | Full breakdown of TP/FP/TN/FN |

### 5.3 Cross-Validation
- 5-fold KFold (regression) or StratifiedKFold (classification).
- CV MAE reported alongside holdout test metrics.
- CV results are used for model comparison; holdout test set is used for final evaluation only.

### 5.4 Feature Importance
- Random Forest: built-in impurity-based importance (fast).
- Permutation importance: model-agnostic, available for all models.
- SHAP values: optional, via `shap` library, computationally expensive.

---

## 6. Reproducibility Controls

- Fixed random seed: `FIXED_RANDOM_SEED = 42` in `constants.py`.
- All sklearn `Pipeline` objects include the full preprocessing + estimator chain.
- Artifacts serialized with `joblib.dump(compress=3)`.
- SHA-256 hash of every artifact recorded in `model_artifacts` table.
- Library versions recorded in `DescriptorSet.library_versions` and `ModelVersion` metadata.
- Dataset hash (SHA-256) checked before training to prevent silent data substitution.

---

## 7. Scientific Limitations

1. **DFT approximation errors**: Training labels inherit the systematic errors of PBE-GGA (typical MAE ~0.1 eV/atom for formation energies).
2. **Dataset coverage bias**: Materials Project predominantly covers inorganic crystalline materials; predictions for organic, amorphous, or surface materials are unreliable.
3. **Compositional-only features**: Without structural information, isomers and polymorphs are indistinguishable.
4. **Extrapolation**: Random Forests cannot predict below the training minimum or above the training maximum. Use Gaussian Processes with caution for uncertainty quantification.
5. **Stability ≠ synthesizability**: `energy_above_hull = 0` does not imply the material can be synthesized; kinetic barriers, entropy effects, and synthesis conditions are not modeled.
6. **Calibration**: Probability estimates from Random Forests and Gradient Boosting are not calibrated. Do not use `confidence_score` as a probability without post-hoc calibration.

---

## 8. Model Card Reference

See `docs/model_card_template.md` for the per-model documentation template.

## 9. Dataset Card Reference

See `docs/dataset_card_template.md` for the per-dataset documentation template.
