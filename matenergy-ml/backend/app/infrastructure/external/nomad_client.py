"""
NOMAD (Novel Materials Discovery) client for MatEnergy-ML.

Uses the public NOMAD REST API v1 at https://nomad-lab.eu/prod/v1/api/v1/
Optional authentication via NOMAD_TOKEN environment variable.

API reference: https://nomad-lab.eu/prod/v1/api/v1/extensions/docs
"""
from __future__ import annotations

import os
from typing import Optional

from app.core.logging_config import get_logger

logger = get_logger(__name__)

_BASE_URL = "https://nomad-lab.eu/prod/v1/api/v1"
_TIMEOUT = 30


class NomadClient:
    """
    Client for the NOMAD public REST API v1.

    Uses optional token from NOMAD_TOKEN env var for authenticated access
    (higher rate limits). Falls back gracefully if unavailable.
    """

    def __init__(self, token: Optional[str] = None) -> None:
        self.token = token or os.getenv("NOMAD_TOKEN", "")
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            import httpx  # noqa: F401
            return True
        except ImportError:
            logger.warning("httpx_not_installed", msg="httpx required for NOMAD client")
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
        Fetch materials from NOMAD.

        Args:
            elements:    Filter by element symbols.
            max_results: Maximum entries to retrieve (per-page 100, paginated).

        Returns:
            List of normalized material dicts.
        """
        if not self._available:
            return []

        import httpx

        headers: dict = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Build query payload for the entries endpoint
        query: dict = {
            "pagination": {"page_size": min(100, max_results)},
            "required": {
                "include": [
                    "results.material.chemical_formula_reduced",
                    "results.material.elements",
                    "results.properties.electronic.band_structure_electronic.band_gap",
                    "entry_id",
                ]
            },
        }
        if elements:
            query["query"] = {
                "results.material.elements": {"all": elements}
            }

        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(
                    f"{_BASE_URL}/entries/query",
                    json=query,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

            entries = data.get("data", [])
            normalized = []
            for entry in entries[:max_results]:
                n = self._normalize(entry)
                if n:
                    normalized.append(n)

            logger.info("nomad_fetch_success", n_fetched=len(normalized))
            return normalized

        except Exception as exc:
            logger.error("nomad_fetch_failed", error=str(exc))
            return []

    def _normalize(self, entry: dict) -> Optional[dict]:
        """Map NOMAD entry fields to MatEnergy-ML schema."""
        try:
            results = entry.get("results", {})
            material = results.get("material", {})
            formula = material.get("chemical_formula_reduced", "")
            if not formula:
                return None

            # Band gap: nested path
            band_gap: Optional[float] = None
            props = results.get("properties", {})
            electronic = props.get("electronic", {})
            bs_list = electronic.get("band_structure_electronic", [])
            if bs_list:
                bg_info = bs_list[0].get("band_gap", {})
                if isinstance(bg_info, dict):
                    band_gap = bg_info.get("value")
                elif isinstance(bg_info, (int, float)):
                    band_gap = float(bg_info)

            return {
                "formula": formula,
                "source_material_id": str(entry.get("entry_id", "")),
                "formation_energy_per_atom": None,   # not directly in entries query
                "energy_above_hull": None,            # requires convex hull calc
                "band_gap": float(band_gap) if band_gap is not None else None,
                "is_stable": None,
                "elements": material.get("elements", []),
                "source": "nomad",
            }
        except Exception as exc:
            logger.warning("nomad_normalize_failed", error=str(exc))
            return None
