# MatEnergy-ML Data Dictionary

## Target Properties

### energy_above_hull

| Attribute | Value |
|---|---|
| **Definition** | Energy of the material above the thermodynamic convex hull at 0 K |
| **Physical meaning** | Measure of thermodynamic stability relative to competing phases |
| **Unit** | eV/atom |
| **Valid range** | −0.5 to 10.0 eV/atom |
| **Stability criterion** | ≤ 0.05 eV/atom (configurable via `STABILITY_THRESHOLD_EV`) |
| **DFT source** | Computed from total energies using PBE functional |
| **Key limitation** | Does not account for finite temperature, pressure, or kinetic barriers |

A value of 0.0 indicates the material lies on the convex hull (thermodynamically stable at 0 K). Values > 0 indicate metastability.

### formation_energy_per_atom

| Attribute | Value |
|---|---|
| **Definition** | Energy to form the compound from elemental reference states |
| **Formula** | ΔEf = E(compound) − Σ xᵢ·E(elementᵢ) |
| **Unit** | eV/atom |
| **Valid range** | −10.0 to 5.0 eV/atom |
| **Sign convention** | Negative = exothermic formation (thermodynamically favorable) |
| **DFT source** | PBE total energies with standard elemental references |

### band_gap

| Attribute | Value |
|---|---|
| **Definition** | Electronic band gap (energy difference between VBM and CBM) |
| **Unit** | eV |
| **Valid range** | 0.0 to 20.0 eV |
| **0.0 = metal** | No gap; electronic conductor |
| **0.0–1.5 eV** | Semiconductor |
| **> 1.5 eV** | Wide-gap semiconductor or insulator |
| **Key limitation** | PBE systematically underestimates by 30–50%; use for relative comparisons only |

### is_stable

| Attribute | Value |
|---|---|
| **Definition** | Binary classification of thermodynamic stability |
| **Derivation** | `is_stable = (energy_above_hull <= STABILITY_THRESHOLD_EV)` |
| **Default threshold** | 0.05 eV/atom |
| **Values** | `True` (stable) / `False` (unstable/metastable) |
| **Note** | Threshold is configurable and should be reported in publications |

---

## Compositional Descriptors

### avg_atomic_number

Weighted average of atomic numbers by composition fraction:
```
avg_Z = Σᵢ xᵢ · Zᵢ
```
where xᵢ is the atomic fraction of element i and Zᵢ is its atomic number.

### electronegativity_range

```
χ_range = max(χᵢ) − min(χᵢ)
```
Pauling electronegativity range across all elements in the compound. Large values indicate significant ionic character.

### stoich_l2 (L2 norm of stoichiometric vector)

```
stoich_l2 = (Σᵢ xᵢ²)^(1/2)
```
Stoichiometric attributes (L2, L3, L5, L7, L10 norms) encode the composition distribution. Compounds with fewer elements and more equal fractions have lower L-norms.

### frac_transition_metals

```
frac_TM = Σᵢ xᵢ · 𝟙[i ∈ TM]
```
Sum of atomic fractions of transition metal elements. High values indicate redox-active compositions suitable for cathode materials.

### frac_Li

Atomic fraction of lithium. High Li fraction is associated with cathode and electrolyte materials for Li-ion batteries.

---

## Dataset Fields

| Column | Type | Description |
|---|---|---|
| `formula` | string | Chemical formula (required) |
| `energy_above_hull` | float | eV/atom above convex hull |
| `formation_energy_per_atom` | float | Formation energy (eV/atom) |
| `band_gap` | float | Electronic band gap (eV) |
| `is_stable` | bool | Thermodynamic stability classification |
| `chemsys` | string | Chemical system, sorted (e.g., "Fe-Li-O") |
| `nelements` | int | Number of distinct elements |
| `source` | string | Data source identifier |

---

## Candidate Scoring Components

| Component | Range | Description |
|---|---|---|
| `stability_score` | [0, 1] | Normalized from energy_above_hull |
| `target_property_score` | [0, 1] | Property-specific score |
| `energy_relevance_score` | [0, 1] | Overlap with application-relevant elements |
| `abundance_score` | [0, 1] | Fraction of earth-abundant elements |
| `toxicity_penalty` | [0, 1] | Fraction of toxic/scarce elements (penalized) |
| `uncertainty_penalty` | [0, 1] | Prediction uncertainty penalty |
| `out_of_domain_penalty` | 0 or 0.3 | Fixed penalty for OOD predictions |
| `candidate_score` | [0, 1] | Weighted sum of above components |
