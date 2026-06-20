"""
Structural descriptor pipeline for MatEnergy-ML.
Requires pymatgen Structure objects serialised as dicts.
"""
import numpy as np

from app.core.exceptions import MissingStructureError

CRYSTAL_SYSTEM_MAP = {
    "triclinic": 1,
    "monoclinic": 2,
    "orthorhombic": 3,
    "tetragonal": 4,
    "trigonal": 5,
    "hexagonal": 6,
    "cubic": 7,
}


class StructuralDescriptorPipeline:
    """Computes structure-based descriptors from a pymatgen Structure dict."""

    def compute(self, structure_dict: dict) -> dict[str, float]:
        """
        Compute structural features from a pymatgen-serialisable structure dict.

        Args:
            structure_dict: A dict produced by ``Structure.as_dict()`` or equivalent.

        Returns:
            Mapping of feature name to float value.

        Raises:
            MissingStructureError: if the dict is absent, empty, or cannot be parsed.
        """
        if not structure_dict:
            raise MissingStructureError(
                code="MISSING_STRUCTURE",
                message="Structural descriptors require a crystal structure",
                detail="structure_dict is empty or None",
                recommended_action=(
                    "Provide a pymatgen-compatible structure in POSCAR/CIF format or as dict"
                ),
            )

        try:
            from pymatgen.core import Structure  # deferred to avoid import cost when unused

            structure = Structure.from_dict(structure_dict)
        except Exception as e:
            raise MissingStructureError(
                code="STRUCTURE_PARSE_ERROR",
                message="Cannot parse crystal structure",
                detail=str(e),
                recommended_action="Ensure structure is in pymatgen-compatible format",
            )

        features: dict[str, float] = {}
        lattice = structure.lattice
        n_atoms = len(structure)

        # --- Basic lattice / cell features ---
        features["density"] = float(structure.density)
        features["volume_per_atom"] = float(lattice.volume / n_atoms)
        features["lattice_a"] = float(lattice.a)
        features["lattice_b"] = float(lattice.b)
        features["lattice_c"] = float(lattice.c)
        features["alpha"] = float(lattice.alpha)
        features["beta"] = float(lattice.beta)
        features["gamma"] = float(lattice.gamma)
        features["n_sites"] = float(n_atoms)

        # --- Symmetry ---
        try:
            from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

            sga = SpacegroupAnalyzer(structure)
            features["space_group_number"] = float(sga.get_space_group_number())
            crystal_sys = sga.get_crystal_system()
            features["crystal_system_encoded"] = float(
                CRYSTAL_SYSTEM_MAP.get(crystal_sys, 0)
            )
        except Exception:
            features["space_group_number"] = 0.0
            features["crystal_system_encoded"] = 0.0

        # --- Packing fraction (approximation via atomic radii) ---
        try:
            atomic_volumes: list[float] = []
            for site in structure:
                for el, occ in site.species.items():
                    r = el.atomic_radius
                    if r is not None:
                        radius_ang = float(r.to("ang"))
                        atomic_volumes.append(
                            float(occ) * (4.0 / 3.0) * np.pi * radius_ang ** 3
                        )
            if atomic_volumes:
                features["packing_fraction"] = float(
                    sum(atomic_volumes) / lattice.volume
                )
            else:
                features["packing_fraction"] = 0.0
        except Exception:
            features["packing_fraction"] = 0.0

        # Safety: replace any NaN/Inf that slipped through
        for k, v in features.items():
            if not np.isfinite(v):
                features[k] = 0.0

        return features

    @classmethod
    def get_feature_names(cls) -> list[str]:
        """Return the ordered list of feature names this pipeline produces."""
        return [
            "density",
            "volume_per_atom",
            "lattice_a",
            "lattice_b",
            "lattice_c",
            "alpha",
            "beta",
            "gamma",
            "n_sites",
            "space_group_number",
            "crystal_system_encoded",
            "packing_fraction",
        ]
