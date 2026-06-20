# Dataset Card Template — MatEnergy-ML

> Copy this template for each dataset used in the platform.
> Fill in all fields. Mark unknown fields as `[TODO]`.

---

## Dataset: [DATASET NAME]

### Basic Information

| Field | Value |
|---|---|
| **Name** | [Human-readable name] |
| **Internal ID** | [UUID from `datasets` table] |
| **Source** | [Materials Project / JARVIS / OQMD / AFLOW / Matbench / CSV Local] |
| **Source URL** | [URL or N/A] |
| **Version / Date Downloaded** | [e.g., 2024-11-01] |
| **License** | [CC BY 4.0 / CC0 / Custom / TODO] |
| **Citation** | [BibTeX or TODO] |
| **SHA-256 Hash** | [64-char hex from `datasets.sha256_hash`] |

---

### Content

| Field | Value |
|---|---|
| **Number of materials** | [n] |
| **Valid materials** | [n after validation] |
| **Rejected rows** | [n] |
| **Chemical systems** | [e.g., Li-Fe-O, Li-Mn-O, Li-Co-O] |
| **Number of distinct elements** | [n] |
| **Element coverage** | [List of elements present] |

---

### Available Properties

| Property | Unit | DFT Method | Coverage |
|---|---|---|---|
| `energy_above_hull` | eV/atom | PBE-GGA + U | [%] |
| `formation_energy_per_atom` | eV/atom | PBE-GGA + U | [%] |
| `band_gap` | eV | PBE-GGA | [%] |
| `is_stable` | Boolean | Derived (≤0.05 eV/atom) | [%] |
| [other] | [unit] | [method] | [%] |

---

### Target Property Statistics

| Property | Min | Max | Mean | Std | % Null |
|---|---|---|---|---|---|
| `energy_above_hull` | | | | | |
| `formation_energy_per_atom` | | | | | |
| `band_gap` | | | | | |

---

### Quality and Validation

| Check | Result |
|---|---|
| All formulas parseable by pymatgen | [✓ / ✗ — n failures] |
| No duplicate (formula, dataset) pairs | [✓ / ✗ — n duplicates] |
| No values outside physical bounds | [✓ / ✗ — n outliers] |
| Column completeness > 90% | [✓ / ✗] |
| Known data quality issues | [Describe or None] |

---

### Known Biases and Limitations

1. [Describe any known bias in the data, e.g., "Predominantly ternary oxides; binary sulfides underrepresented"]
2. [Describe DFT method limitations relevant to this dataset]
3. [Describe any filtering applied, e.g., "Only materials with energy_above_hull < 1 eV/atom included"]
4. [Other limitations]

---

### Usage in MatEnergy-ML

| Experiment | Model Type | Target | Result |
|---|---|---|---|
| [e.g., Regression baseline] | Ridge Regression | energy_above_hull | MAE = [TODO] eV/atom |
| [e.g., Stability classifier] | Random Forest | is_stable | F1 = [TODO] |

---

### Import Record

| Field | Value |
|---|---|
| Imported by | [username / admin] |
| Imported at | [ISO timestamp] |
| Import script | `scripts/import_demo_data.py` or manual upload |
| Storage path | `data/uploads/[UUID].csv` |

---

*Template version: 1.0 — MatEnergy-ML 2025*
