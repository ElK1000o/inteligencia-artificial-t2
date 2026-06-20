# Scientific and Technical Limitations of MatEnergy-ML

This document provides an honest account of the limitations inherent to MatEnergy-ML's current design. Understanding these limitations is essential for interpreting results correctly and for using the platform responsibly in academic and research contexts.

---

## 1. DFT Data Limitations

### 1.1 Functional Approximation Error

All DFT data used in MatEnergy-ML is computed using the Perdew–Burke–Ernzerhof (PBE) generalized gradient approximation (GGA). PBE is known to:

- **Underestimate band gaps** by 30–50% for many semiconductors and insulators. Band gap predictions should be interpreted with this systematic bias in mind.
- **Fail for strongly correlated systems** (e.g., transition-metal oxides with localized d-electrons such as FeO, NiO, CoO). DFT+U or hybrid functionals are required for accurate treatment of these materials.
- **Neglect van der Waals interactions**, which are important for layered materials (e.g., graphite-based anodes, some 2D electrolytes).
- **Introduce spin-orbit coupling errors** for heavy elements (e.g., materials containing Pb, Bi, or heavy lanthanides).

### 1.2 T = 0 K, P = 0 Assumption

DFT calculations represent materials at 0 K and 0 Pa. Real battery operation occurs at finite temperature (room temperature to ~80°C) and under mechanical stress. Phase diagrams, thermal stability, and electrode volume changes are not captured by static DFT.

### 1.3 Neglect of Defect Chemistry

The DFT data in MatEnergy-ML corresponds to ideal, stoichiometric, defect-free crystals. Real materials contain vacancies, interstitials, substitutional defects, and grain boundaries that significantly affect:
- Ionic conductivity
- Electrochemical cycling stability
- Capacity retention

---

## 2. Energy Above Hull Is Not Proof of Synthesizability

`energy_above_hull` is the energy of a compound relative to the thermodynamic convex hull — the set of phases that are thermodynamically stable at 0 K. While it is a widely used screening criterion:

- **A material with `energy_above_hull = 0` is thermodynamically stable at 0 K** but may not be synthesizable under practical conditions.
- **Materials with `energy_above_hull > 0` are metastable** but can exist as long-lived phases (e.g., many battery cathodes are metastable against decomposition during cycling).
- **The hull itself is approximate**, depending on the completeness of the phase diagram in the reference database. Missing competing phases can shift hull energies.
- **Synthesis conditions** (temperature, pressure, atmosphere, kinetics) determine what forms, not thermodynamics alone.

> **Important**: A high ranking score in MatEnergy-ML indicates thermodynamic favorability and compositional compatibility — not guaranteed synthesizability. Experimental validation is always required.

---

## 3. Compositional Descriptor Limitations

The primary descriptor pipeline in MatEnergy-ML uses **composition-only features** (no structural information). This means:

- **Crystal structure is ignored**: Two polymorphs with the same formula (e.g., TiO₂ in rutile vs. anatase vs. brookite) produce identical descriptors despite having very different properties.
- **Coordination environment is not captured**: The local bonding geometry around Li⁺ sites strongly influences ionic conductivity and voltage, but this is invisible to composition-only models.
- **No long-range order information**: Amorphous vs. crystalline phases, superlattices, and ordered vacancies are indistinguishable.

Structural descriptors (available when crystallographic data is provided) partially address this, but are still limited compared to graph neural networks (CGCNN, MEGNet, ALIGNN) that operate on full atomic graphs.

---

## 4. Machine Learning Model Limitations

### 4.1 Extrapolation Risk

All ML models in MatEnergy-ML are trained on known, characterized materials. Predictions for **out-of-distribution** chemical compositions (flagged with `is_out_of_domain = True`) are unreliable. The 3-sigma OOD heuristic used is a simple first-order check — it does not guarantee that in-distribution predictions are reliable either.

### 4.2 Correlative, Not Causative

The ML models learn statistical correlations between chemical descriptors and properties. They do not encode physical mechanisms. A high predicted formation energy does not tell you *why* a material is stable or *how* to make it.

### 4.3 Training Data Bias

Materials Project and similar databases over-represent:
- Well-studied systems (Li–Fe–O, Li–Co–O, Li–Mn–O families)
- Simple binary and ternary compounds
- Materials that have been experimentally reported (survivorship bias)

This bias propagates into the ML models, which may systematically underperform for novel or understudied chemical spaces.

### 4.4 Class Imbalance in Stability Classification

The majority of materials in computational databases are thermodynamically stable (energy_above_hull ≤ 0.05 eV/atom), creating class imbalance for the `is_stable` classification task. Class-balanced training (via `class_weight="balanced"`) partially mitigates this but does not eliminate it.

---

## 5. Electrochemical Properties Not Predicted

MatEnergy-ML's primary targets are thermodynamic properties (formation energy, stability) and electronic structure (band gap). The following electrochemical properties **are not currently predicted**:

- Average intercalation voltage
- Theoretical gravimetric and volumetric capacity
- Li-ion diffusion barriers (requires NEB calculations)
- Ionic conductivity (requires molecular dynamics or AIMD)
- Electrochemical stability window
- Solid-electrolyte interface (SEI) formation
- Capacity fade and cycling stability

These properties require substantially more complex simulations (NEB, AIMD, DFPT) and are planned for Etapa 13 (atomistic simulation integration).

---

## 6. Experimental Validation Is Always Required

MatEnergy-ML is a **computational screening tool**, not a synthesis or characterization platform. Any material flagged as a high-priority candidate must be:

1. Synthesized and structurally characterized (XRD, TEM)
2. Electrochemically tested (galvanostatic cycling, impedance spectroscopy)
3. Validated for safety (thermal stability, chemical compatibility with electrolyte)

The output of this platform should be treated as a **prioritized shortlist for experimental investigation**, not as a validated prediction of performance.

---

## 7. Summary Table

| Limitation | Impact | Mitigation Available |
|---|---|---|
| PBE band gap underestimation | Band gap predictions ~30-50% too low | Use HSE06 data if available |
| T=0 K, P=0 assumption | Thermal effects not modeled | Planned AIMD integration |
| Composition-only descriptors | Polymorph-blind predictions | Structural descriptors (optional) |
| ML extrapolation | Unreliable OOD predictions | OOD warnings flagged automatically |
| Training data bias | Understudied spaces underperform | Document chemical space coverage |
| Hull energy approximation | Synthesizability not guaranteed | State explicitly in reports |
| No electrochemical properties | Incomplete performance picture | Planned for future versions |

---

*This limitations document should be cited and included in any academic work based on MatEnergy-ML results.*
