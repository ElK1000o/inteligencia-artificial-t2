"""
Matbench client for MatEnergy-ML.

Loads benchmark datasets from the matminer / matbench library.
This is a local-download client — data is fetched once and cached;
it does NOT stream from a remote API at request time.

Supported datasets:
  - matbench_mp_e_form     : formation energy (eV/atom), ~132k materials
  - matbench_mp_gap        : band gap (eV), ~106k materials
  - matbench_mp_is_metal   : metal/insulator classification, ~106k materials
  - matbench_perovskites   : formation energy of perovskites, ~18k materials

Reference: https://matbench.materialsproject.org/
"""
from __future__ import annotations

from typing import Optional

from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Matbench dataset names and their primary target column
_SUPPORTED_DATASETS: dict[str, dict] = {
    "matbench_mp_e_form": {
        "target": "e_form",
        "property_map": "formation_energy_per_atom",
        "description": "DFT formation energy from Materials Project (~132k)",
    },
    "matbench_mp_gap": {
        "target": "gap pbe",
        "property_map": "band_gap",
        "description": "DFT PBE band gap from Materials Project (~106k)",
    },
    "matbench_mp_is_metal": {
        "target": "is_metal",
        "property_map": "is_metal",
        "description": "Metal vs insulator classification (~106k)",
    },
    "matbench_perovskites": {
        "target": "e_form",
        "property_map": "formation_energy_per_atom",
        "description": "Formation energy of perovskites (~18k)",
    },
}


class MatbenchClient:
    """
    Loads Matbench benchmark datasets via matminer.

    matminer must be installed: pip install matminer
    Data is downloaded on first access and cached locally by matminer.
    """

    def __init__(self) -> None:
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            import matminer  # noqa: F401
            return True
        except ImportError:
            logger.warning(
                "matminer_not_installed",
                msg="matminer required for Matbench client — install with: pip install matminer",
            )
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    def list_supported_datasets(self) -> list[dict]:
        """Return metadata for all supported Matbench datasets."""
        return [
            {"name": k, **v} for k, v in _SUPPORTED_DATASETS.items()
        ]

    def fetch_materials(
        self,
        dataset_name: str = "matbench_mp_e_form",
        max_results: int = 5000,
        fold: int = 0,
    ) -> list[dict]:
        """
        Load a Matbench dataset and return normalized material dicts.

        Args:
            dataset_name: One of the supported Matbench dataset names.
            max_results:  Cap on the number of entries returned.
            fold:         Matbench cross-validation fold (0–4).

        Returns:
            List of dicts with formula + target property columns.
        """
        if not self._available:
            return []

        if dataset_name not in _SUPPORTED_DATASETS:
            logger.error(
                "matbench_unsupported_dataset",
                name=dataset_name,
                supported=list(_SUPPORTED_DATASETS),
            )
            return []

        meta = _SUPPORTED_DATASETS[dataset_name]
        target_col = meta["target"]
        property_name = meta["property_map"]

        try:
            from matminer.datasets import load_dataset

            df = load_dataset(dataset_name)
            df = df.head(max_results)

            results = []
            for _, row in df.iterrows():
                formula = self._extract_formula(row)
                if not formula:
                    continue

                target_val = row.get(target_col)
                entry = {
                    "formula": formula,
                    "source_material_id": None,
                    "source": f"matbench:{dataset_name}",
                }

                if property_name == "formation_energy_per_atom":
                    entry["formation_energy_per_atom"] = (
                        float(target_val) if target_val is not None else None
                    )
                    entry["energy_above_hull"] = None
                    entry["band_gap"] = None
                    entry["is_stable"] = None
                elif property_name == "band_gap":
                    entry["band_gap"] = (
                        float(target_val) if target_val is not None else None
                    )
                    entry["formation_energy_per_atom"] = None
                    entry["energy_above_hull"] = None
                    entry["is_stable"] = None
                elif property_name == "is_metal":
                    entry["band_gap"] = 0.0 if target_val else None
                    entry["formation_energy_per_atom"] = None
                    entry["energy_above_hull"] = None
                    entry["is_stable"] = None
                else:
                    entry["formation_energy_per_atom"] = None
                    entry["energy_above_hull"] = None
                    entry["band_gap"] = None
                    entry["is_stable"] = None

                results.append(entry)

            logger.info(
                "matbench_load_success",
                dataset=dataset_name,
                n_loaded=len(results),
            )
            return results

        except Exception as exc:
            logger.error("matbench_fetch_failed", dataset=dataset_name, error=str(exc))
            return []

    def _extract_formula(self, row) -> Optional[str]:
        """Extract formula string from a Matbench row."""
        # Most Matbench datasets have a 'structure' column (pymatgen Structure)
        # or a 'composition' column (pymatgen Composition)
        if "structure" in row.index:
            try:
                return row["structure"].formula
            except Exception:
                pass
        if "composition" in row.index:
            try:
                comp = row["composition"]
                return str(comp.reduced_formula) if hasattr(comp, "reduced_formula") else str(comp)
            except Exception:
                pass
        if "formula" in row.index:
            return str(row["formula"])
        return None
