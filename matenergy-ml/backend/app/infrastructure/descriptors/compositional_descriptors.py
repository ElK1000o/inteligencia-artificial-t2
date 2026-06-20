"""
Compositional descriptor pipeline for MatEnergy-ML.
Computes element-level statistical features from chemical formula.
"""
import numpy as np
from typing import Optional
from pymatgen.core import Composition, Element

from app.core.exceptions import (
    InvalidChemicalFormulaError, MissingCompositionError, DescriptorNaNError
)

# Periodic table properties used as descriptors
ELEMENT_PROPERTIES = {
    "atomic_number": lambda el: float(el.Z),
    "atomic_mass": lambda el: float(el.atomic_mass),
    "electronegativity": lambda el: float(el.X) if el.X is not None else np.nan,
    "atomic_radius": lambda el: float(el.atomic_radius.to("ang")) if el.atomic_radius is not None else np.nan,
    "ionization_energy": lambda el: float(el.ionization_energies[0]) if el.ionization_energies else np.nan,
    "electron_affinity": lambda el: float(el.electron_affinity) if el.electron_affinity is not None else np.nan,
}

TRANSITION_METALS = {
    "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
    "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd",
    "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
}

ENERGY_ELEMENTS = ["Li", "Cu", "O", "S", "P", "Fe", "Mn", "Co", "Ni"]


class CompositionalDescriptorPipeline:
    """Computes composition-based feature vectors from chemical formulas."""

    def compute(self, formula: str) -> dict[str, float]:
        """Main entry: parse formula and compute all compositional descriptors."""
        if not formula or not formula.strip():
            raise MissingCompositionError(
                code="EMPTY_FORMULA",
                message="Cannot compute descriptors: formula is empty",
                detail="formula string is empty or None",
                recommended_action="Provide a valid chemical formula",
            )

        try:
            comp = Composition(formula)
        except Exception as e:
            raise InvalidChemicalFormulaError(
                code="FORMULA_PARSE_ERROR",
                message="Cannot parse chemical formula",
                detail=f"pymatgen failed: {e}",
                recommended_action="Check the formula for typos and ensure all elements are valid",
            )

        elements = list(comp.elements)
        fractions = [comp.get_atomic_fraction(el) for el in elements]

        features: dict[str, float] = {}

        # === Element count ===
        features["n_elements"] = float(len(elements))

        # === Per-element property statistics ===
        for prop_name, prop_fn in ELEMENT_PROPERTIES.items():
            # Collect valid values and their matching fractions
            valid_values: list[float] = []
            valid_fractions: list[float] = []
            for el, frac in zip(elements, fractions):
                try:
                    v = prop_fn(el)
                    if not np.isnan(v):
                        valid_values.append(v)
                        valid_fractions.append(frac)
                except Exception:
                    pass

            if valid_values:
                frac_sum = sum(valid_fractions)
                if frac_sum > 0:
                    norm_weights = [f / frac_sum for f in valid_fractions]
                    weighted_avg = float(np.dot(valid_values, norm_weights))
                else:
                    weighted_avg = float(np.mean(valid_values))

                features[f"avg_{prop_name}"] = weighted_avg
                features[f"max_{prop_name}"] = float(max(valid_values))
                features[f"min_{prop_name}"] = float(min(valid_values))
                features[f"range_{prop_name}"] = float(max(valid_values) - min(valid_values))
                features[f"std_{prop_name}"] = float(np.std(valid_values)) if len(valid_values) > 1 else 0.0
            else:
                features[f"avg_{prop_name}"] = 0.0
                features[f"max_{prop_name}"] = 0.0
                features[f"min_{prop_name}"] = 0.0
                features[f"range_{prop_name}"] = 0.0
                features[f"std_{prop_name}"] = 0.0

        # === Element-specific fractions ===
        for symbol in ENERGY_ELEMENTS:
            features[f"frac_{symbol}"] = (
                float(comp.get_atomic_fraction(symbol)) if symbol in comp else 0.0
            )

        # === Transition metal fraction ===
        tm_frac = sum(
            comp.get_atomic_fraction(el)
            for el in elements
            if el.symbol in TRANSITION_METALS
        )
        features["frac_transition_metals"] = float(tm_frac)

        # === Stoichiometric attributes (L-norm based) ===
        frac_array = np.array(fractions)
        for p in [2, 3, 5, 7, 10]:
            features[f"stoich_l{p}"] = float(np.sum(frac_array ** p) ** (1.0 / p))

        # === Valence electrons ===
        ve_counts: list[float] = []
        for el in elements:
            try:
                ve = sum(el.valence)
                ve_counts.append(float(ve))
            except Exception:
                pass

        if ve_counts:
            features["n_valence_electrons_avg"] = float(np.mean(ve_counts))
            features["n_valence_electrons_max"] = float(max(ve_counts))
            features["n_valence_electrons_min"] = float(min(ve_counts))
        else:
            features["n_valence_electrons_avg"] = 0.0
            features["n_valence_electrons_max"] = 0.0
            features["n_valence_electrons_min"] = 0.0

        # Validate: replace any residual NaN/Inf with 0.0 and keep the dict clean
        for k, v in features.items():
            if not np.isfinite(v):
                features[k] = 0.0

        return features

    @classmethod
    def get_feature_names(cls) -> list[str]:
        """Return the ordered list of feature names this pipeline produces."""
        names: list[str] = ["n_elements"]
        for prop in ELEMENT_PROPERTIES:
            for stat in ["avg", "max", "min", "range", "std"]:
                names.append(f"{stat}_{prop}")
        for symbol in ENERGY_ELEMENTS:
            names.append(f"frac_{symbol}")
        names.append("frac_transition_metals")
        for p in [2, 3, 5, 7, 10]:
            names.append(f"stoich_l{p}")
        names.extend([
            "n_valence_electrons_avg",
            "n_valence_electrons_max",
            "n_valence_electrons_min",
        ])
        return names
