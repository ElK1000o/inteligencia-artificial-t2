"""
Materials Project API client for MatEnergy-ML.
Uses mp-api if available. Falls back gracefully if API key not set.
NEVER hardcodes API keys.
"""
import os
from typing import Optional
from app.core.logging_config import get_logger

logger = get_logger(__name__)

TARGET_PROPERTIES = [
    "material_id", "formula_pretty", "energy_above_hull",
    "formation_energy_per_atom", "band_gap", "is_stable",
    "nelements", "elements", "chemsys",
]

STRUCTURE_FIELDS = [
    "material_id", "formula_pretty", "energy_above_hull",
    "structure", "symmetry",
]

# Module-level caches — avoids redundant MP API calls per worker lifetime
_STRUCTURE_CACHE: dict[str, dict] = {}
_DECOMP_CACHE: dict[str, dict] = {}
_PD_CACHE: dict[str, tuple] = {}  # chemsys_key -> (entries, PhaseDiagram)


class MaterialsProjectClient:
    """
    Client for Materials Project API v2 (mp-api).
    Only imports mp-api if available — graceful degradation if not installed.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("MATERIALS_PROJECT_API_KEY", "")
        self._available = self._check_availability()

    def _check_availability(self) -> bool:
        if not self.api_key:
            logger.warning("mp_client_no_api_key", msg="Materials Project API key not set")
            return False
        try:
            import mp_api  # noqa: F401
            return True
        except ImportError:
            logger.warning("mp_api_not_installed", msg="mp-api package not installed")
            return False

    @property
    def is_available(self) -> bool:
        return self._available

    def fetch_materials(
        self,
        elements: Optional[list[str]] = None,
        chemsys: Optional[str] = None,
        max_results: int = 1000,
    ) -> list[dict]:
        """
        Fetch materials from Materials Project.
        Returns list of dicts with standardized property names.
        Falls back to empty list if unavailable.
        """
        if not self._available:
            logger.info("mp_client_unavailable", action="returning_empty")
            return []

        try:
            from mp_api.client import MPRester
            with MPRester(self.api_key) as mpr:
                kwargs: dict = {}
                if chemsys:
                    kwargs["chemsys"] = chemsys
                elif elements:
                    kwargs["elements"] = elements

                docs = mpr.materials.summary.search(
                    **kwargs,
                    fields=TARGET_PROPERTIES,
                    num_chunks=10,
                )
                return [self._normalize(d) for d in docs[:max_results]]
        except Exception as e:
            logger.error("mp_fetch_failed", error=str(e))
            return []

    def fetch_structure(self, formula: str) -> Optional[dict]:
        """
        Fetch the most stable crystal structure for *formula* from Materials Project.

        Returns a dict with:
          mp_material_id, formula, energy_above_hull,
          cif (CIF string), n_sites, n_species,
          lattice (a/b/c/alpha/beta/gamma/volume/density),
          space_group, space_group_number, crystal_system,
          sites (list of {element, frac_coords, cart_coords}),
          coordination (list of {element, site_index, cn, neighbor_elements}),
          bond_analysis (list of {pair, mean_Å, std_Å, min_Å, max_Å})

        Returns None when API unavailable or formula not found.
        Caches results in _STRUCTURE_CACHE (module-level) for the process lifetime.
        """
        cache_key = formula.strip()
        if cache_key in _STRUCTURE_CACHE:
            return _STRUCTURE_CACHE[cache_key]

        if not self._available:
            return None

        try:
            from mp_api.client import MPRester
            with MPRester(self.api_key) as mpr:
                docs = mpr.materials.summary.search(
                    formula=cache_key,
                    fields=STRUCTURE_FIELDS,
                )
                docs = list(docs)

            if not docs:
                logger.info("mp_structure_not_found", formula=formula)
                return None

            # Pick the most stable (lowest EAH)
            docs.sort(key=lambda d: d.energy_above_hull if d.energy_above_hull is not None else 999)
            best = docs[0]
            structure = best.structure

            # ---- CIF export ----
            cif_string: str = structure.to(fmt="cif")

            # ---- Lattice parameters ----
            lat = structure.lattice
            lattice = {
                "a": round(lat.a, 4),
                "b": round(lat.b, 4),
                "c": round(lat.c, 4),
                "alpha": round(lat.alpha, 3),
                "beta": round(lat.beta, 3),
                "gamma": round(lat.gamma, 3),
                "volume": round(lat.volume, 3),
            }

            # ---- Space group ----
            from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
            sga = SpacegroupAnalyzer(structure)
            sg_symbol = sga.get_space_group_symbol()
            sg_number = sga.get_space_group_number()
            crystal_system = sga.get_crystal_system()

            # Density
            density = round(structure.density, 4)

            # ---- Site list ----
            sites = []
            for site in structure:
                sites.append({
                    "element": site.specie.symbol,
                    "frac_coords": [round(x, 4) for x in site.frac_coords.tolist()],
                    "cart_coords": [round(x, 4) for x in site.coords.tolist()],
                })

            # ---- Coordination analysis ----
            coordination = []
            bond_pairs: dict[str, list[float]] = {}
            try:
                from pymatgen.analysis.local_env import CrystalNN
                cnn = CrystalNN()
                for i, site in enumerate(structure):
                    try:
                        nn_info = cnn.get_nn_info(structure, i)
                        neighbors = [n["site"].specie.symbol for n in nn_info]
                        coordination.append({
                            "element": site.specie.symbol,
                            "site_index": i,
                            "cn": len(neighbors),
                            "neighbor_elements": neighbors,
                        })
                        # Collect bond lengths
                        for n_info in nn_info:
                            pair = "-".join(sorted([site.specie.symbol, n_info["site"].specie.symbol]))
                            dist = round(float(n_info["weight"]) if hasattr(n_info["weight"], "__float__") else
                                         float(structure.get_distance(i, n_info["site_index"])), 4)
                            bond_pairs.setdefault(pair, []).append(dist)
                    except Exception:
                        coordination.append({
                            "element": site.specie.symbol,
                            "site_index": i,
                            "cn": None,
                            "neighbor_elements": [],
                        })
            except Exception as e:
                logger.warning("mp_coordination_failed", error=str(e))

            # ---- Bond analysis ----
            import numpy as np
            bond_analysis = []
            for pair, lengths in bond_pairs.items():
                arr = np.array(lengths)
                bond_analysis.append({
                    "pair": pair,
                    "mean_ang": round(float(arr.mean()), 4),
                    "std_ang": round(float(arr.std()), 4),
                    "min_ang": round(float(arr.min()), 4),
                    "max_ang": round(float(arr.max()), 4),
                    "n_bonds": len(lengths),
                })
            bond_analysis.sort(key=lambda x: x["mean_ang"])

            result = {
                "mp_material_id": str(best.material_id),
                "formula": str(best.formula_pretty),
                "energy_above_hull": float(best.energy_above_hull) if best.energy_above_hull is not None else None,
                "cif": cif_string,
                "n_sites": len(structure),
                "n_species": len(structure.composition.elements),
                "lattice": lattice,
                "density": density,
                "space_group": sg_symbol,
                "space_group_number": sg_number,
                "crystal_system": crystal_system,
                "sites": sites,
                "coordination": coordination,
                "bond_analysis": bond_analysis,
                "n_polymorphs": len(docs),
                "structure_source": f"Materials Project ({best.material_id}). Most stable of {len(docs)} polymorph(s) found for formula '{formula}'.",
            }

            _STRUCTURE_CACHE[cache_key] = result
            logger.info("mp_structure_fetched", formula=formula, mp_id=str(best.material_id))
            return result

        except Exception as e:
            logger.error("mp_structure_fetch_failed", formula=formula, error=str(e))
            return None

    def fetch_decomposition(self, formula: str, chemsys_list: list[str]) -> Optional[dict]:
        """
        Compute the thermodynamic decomposition pathway for *formula* using the
        Materials Project phase diagram for the given chemical system.

        Returns a dict with:
          formula, chemsys, energy_above_hull (eV/atom from MP),
          decomposition_products: [{formula, fraction, mp_id}],
          decomposition_reaction: human-readable string,
          is_stable: bool,
          n_pd_entries: int,
          source: str

        Returns None when API unavailable or formula not found in the phase diagram.
        Results are cached per formula for the process lifetime.
        """
        cache_key = formula.strip()
        if cache_key in _DECOMP_CACHE:
            return _DECOMP_CACHE[cache_key]

        if not self._available:
            return None

        try:
            from mp_api.client import MPRester
            from pymatgen.analysis.phase_diagram import PhaseDiagram
            from pymatgen.core import Composition

            chemsys_key = "-".join(sorted(chemsys_list))

            # Build or retrieve cached phase diagram
            if chemsys_key in _PD_CACHE:
                entries, pd = _PD_CACHE[chemsys_key]
            else:
                with MPRester(self.api_key) as mpr:
                    entries = mpr.get_entries_in_chemsys(chemsys_list)
                if not entries:
                    logger.warning("mp_decomp_no_entries", chemsys=chemsys_key)
                    return None
                pd = PhaseDiagram(entries)
                _PD_CACHE[chemsys_key] = (entries, pd)

            # Find the target entry (lowest energy for this formula)
            target_comp = Composition(formula)
            target_entry = None
            min_energy = float("inf")
            for entry in entries:
                try:
                    if entry.composition.reduced_composition == target_comp.reduced_composition:
                        e_pa = entry.energy_per_atom
                        if e_pa < min_energy:
                            min_energy = e_pa
                            target_entry = entry
                except Exception:
                    continue

            if target_entry is None:
                logger.info("mp_decomp_formula_not_found", formula=formula)
                _DECOMP_CACHE[cache_key] = {"formula": formula, "not_in_mp": True}
                return _DECOMP_CACHE[cache_key]

            decomp, e_above_hull = pd.get_decomp_and_e_above_hull(target_entry)

            # Build product list
            products = []
            for entry, fraction in decomp.items():
                mp_id = str(getattr(entry, "entry_id", "") or "")
                products.append({
                    "formula": entry.composition.reduced_formula,
                    "fraction": round(float(fraction), 4),
                    "mp_id": mp_id if mp_id else None,
                })
            products.sort(key=lambda x: x["fraction"], reverse=True)

            # Human-readable reaction string
            rhs = " + ".join(
                f"{p['fraction']:.3f} {p['formula']}"
                for p in products
                if p["fraction"] > 1e-6
            )
            reaction = f"{target_comp.reduced_formula} → {rhs}"

            result = {
                "formula": formula,
                "reduced_formula": target_comp.reduced_formula,
                "chemsys": chemsys_key,
                "energy_above_hull": round(float(e_above_hull), 4),
                "decomposition_products": products,
                "decomposition_reaction": reaction,
                "is_stable": float(e_above_hull) <= 0.025,
                "n_pd_entries": len(entries),
                "not_in_mp": False,
                "source": (
                    f"Materials Project phase diagram for {chemsys_key} system "
                    f"({len(entries)} entries). EAH computed via pymatgen PhaseDiagram."
                ),
            }

            _DECOMP_CACHE[cache_key] = result
            logger.info("mp_decomposition_computed", formula=formula, e_above_hull=e_above_hull)
            return result

        except Exception as e:
            logger.error("mp_decomposition_failed", formula=formula, error=str(e))
            return None

    def _normalize(self, doc) -> dict:
        return {
            "formula": str(doc.formula_pretty),
            "source_material_id": str(doc.material_id),
            "energy_above_hull": float(doc.energy_above_hull) if doc.energy_above_hull is not None else None,
            "formation_energy_per_atom": float(doc.formation_energy_per_atom) if doc.formation_energy_per_atom is not None else None,
            "band_gap": float(doc.band_gap) if doc.band_gap is not None else None,
            "is_stable": bool(doc.is_stable),
            "nelements": int(doc.nelements),
            "elements": [str(e) for e in doc.elements],
            "chemsys": str(doc.chemsys),
            "source": "materials_project",
        }
