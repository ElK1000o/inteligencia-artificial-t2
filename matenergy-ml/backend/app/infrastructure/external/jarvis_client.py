"""
JARVIS-DFT client stub for MatEnergy-ML.
Uses jarvis-tools if available.
"""
from typing import Optional
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class JarvisClient:
    """Client for JARVIS-DFT database via jarvis-tools."""

    def __init__(self):
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            import jarvis  # noqa: F401
            return True
        except ImportError:
            logger.warning("jarvis_not_installed", msg="jarvis-tools not installed")
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    def fetch_materials(self, max_results: int = 500) -> list[dict]:
        """Fetch DFT-3D materials from JARVIS database."""
        if not self._available:
            return []
        try:
            from jarvis.db.figshare import data as jdata
            dataset = jdata("dft_3d")
            results = []
            for entry in dataset[:max_results]:
                formula = entry.get("formula", "")
                if not formula:
                    continue
                results.append({
                    "formula": formula,
                    "source_material_id": entry.get("jid", ""),
                    "formation_energy_per_atom": entry.get("formation_energy_peratom"),
                    "band_gap": entry.get("optb88vdw_bandgap"),
                    "energy_above_hull": None,  # not directly in JARVIS-DFT
                    "source": "jarvis",
                })
            return results
        except Exception as e:
            logger.error("jarvis_fetch_failed", error=str(e))
            return []
