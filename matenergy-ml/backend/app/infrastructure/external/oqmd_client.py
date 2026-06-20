"""
OQMD (Open Quantum Materials Database) client for MatEnergy-ML.

Uses the public REST API at https://oqmd.org/oqmdapi/
No API key required. Graceful fallback if unavailable.

API reference: https://static.oqmd.org/static/docs/restful.html
"""
from __future__ import annotations

from typing import Optional

from app.core.logging_config import get_logger

logger = get_logger(__name__)

_BASE_URL = "https://oqmd.org/oqmdapi/formationenergy"
_TIMEOUT = 30


class OQMDClient:
    """
    Client for the OQMD public REST API.

    Fetches materials with formation energies and basic stability data.
    Falls back to an empty list if the API is unreachable.
    """

    def __init__(self) -> None:
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            import httpx  # noqa: F401
            return True
        except ImportError:
            logger.warning("httpx_not_installed", msg="httpx required for OQMD client")
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    def fetch_materials(
        self,
        elements: Optional[list[str]] = None,
        limit: int = 200,
    ) -> list[dict]:
        """
        Fetch materials from OQMD.

        Args:
            elements: Filter by element symbols (e.g. ["Li", "Fe", "O"]).
            limit:    Maximum number of entries to fetch.

        Returns:
            List of normalized material dicts compatible with the MatEnergy-ML schema.
        """
        if not self._available:
            return []

        import httpx

        params: dict = {
            "limit": min(limit, 200),
            "offset": 0,
            "fields": "name,entry_id,delta_e,stability,band_gap",
            "format": "json",
        }
        if elements:
            params["filter"] = f"element_set=AND({','.join(elements)})"

        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.get(_BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

            results = data.get("data", [])
            normalized = [self._normalize(r) for r in results if r.get("name")]
            logger.info(
                "oqmd_fetch_success",
                n_fetched=len(normalized),
                elements=elements,
            )
            return normalized

        except Exception as exc:
            logger.error("oqmd_fetch_failed", error=str(exc))
            return []

    def _normalize(self, entry: dict) -> dict:
        """Map OQMD fields to MatEnergy-ML schema."""
        delta_e = entry.get("delta_e")
        stability = entry.get("stability")
        band_gap = entry.get("band_gap")

        # OQMD uses delta_e for formation_energy_per_atom
        formation_e = float(delta_e) if delta_e is not None else None
        # Stability in OQMD is energy_above_hull equivalent (eV/atom)
        e_above_hull = float(stability) if stability is not None else None
        is_stable = (e_above_hull is not None and e_above_hull <= 0.05)

        return {
            "formula": str(entry.get("name", "")),
            "source_material_id": str(entry.get("entry_id", "")),
            "formation_energy_per_atom": formation_e,
            "energy_above_hull": e_above_hull,
            "band_gap": float(band_gap) if band_gap is not None else None,
            "is_stable": is_stable,
            "source": "oqmd",
        }
