"""
AFLOW (Automatic FLOW for Materials Discovery) client for MatEnergy-ML.

Uses the AFLOW REST API at http://aflowlib.duke.edu/API/
No API key required.

API reference: http://aflowlib.org/aflowAPI.html
"""
from __future__ import annotations

from typing import Optional

from app.core.logging_config import get_logger

logger = get_logger(__name__)

_BASE_URL = "http://aflowlib.duke.edu/API"
_TIMEOUT = 30


class AFLOWClient:
    """
    Client for the AFLOW Materials Repository REST API.

    Provides access to formation energies, band gaps, and structural data
    for hundreds of thousands of DFT-computed materials.
    Falls back gracefully if the API is unavailable.
    """

    def __init__(self) -> None:
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            import httpx  # noqa: F401
            return True
        except ImportError:
            logger.warning("httpx_not_installed", msg="httpx required for AFLOW client")
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    def fetch_materials(
        self,
        elements: Optional[list[str]] = None,
        max_results: int = 200,
    ) -> list[dict]:
        """
        Fetch materials from the AFLOW REST API.

        Args:
            elements:    Filter by element list (all elements must be present).
            max_results: Cap on returned entries.

        Returns:
            List of normalized material dicts.
        """
        if not self._available:
            return []

        import httpx

        # AFLOW AFLUX query language: SELECT compound,auid,enthalpy_formation_atom,Egap
        # WHERE species includes requested elements
        species_filter = ""
        if elements:
            # AFLUX: $species(Li:Fe:O) means the alloy system Li-Fe-O
            species_str = ":".join(sorted(elements))
            species_filter = f"$species({species_str}),"

        aflux_query = (
            f"{species_filter}"
            f"$paging(1,{min(max_results, 500)}),"
            f"compound,auid,enthalpy_formation_atom,Egap,nspecies"
        )

        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.get(
                    f"{_BASE_URL}/search",
                    params={"AFLUX": aflux_query, "format": "json"},
                )
                resp.raise_for_status()
                data = resp.json()

            if not isinstance(data, list):
                data = data.get("data", []) if isinstance(data, dict) else []

            normalized = [self._normalize(r) for r in data if r.get("compound")]
            normalized = [n for n in normalized if n is not None]
            logger.info("aflow_fetch_success", n_fetched=len(normalized))
            return normalized

        except Exception as exc:
            logger.error("aflow_fetch_failed", error=str(exc))
            return []

    def _normalize(self, entry: dict) -> Optional[dict]:
        """Map AFLOW entry fields to MatEnergy-ML schema."""
        try:
            formula = str(entry.get("compound", "")).strip()
            if not formula:
                return None

            formation_e = entry.get("enthalpy_formation_atom")
            band_gap = entry.get("Egap")

            return {
                "formula": formula,
                "source_material_id": str(entry.get("auid", "")),
                "formation_energy_per_atom": float(formation_e) if formation_e is not None else None,
                "energy_above_hull": None,   # not directly available from AFLOW AFLUX
                "band_gap": float(band_gap) if band_gap is not None else None,
                "is_stable": None,
                "nelements": int(entry.get("nspecies", 0)) or None,
                "source": "aflow",
            }
        except Exception as exc:
            logger.warning("aflow_normalize_failed", error=str(exc))
            return None
