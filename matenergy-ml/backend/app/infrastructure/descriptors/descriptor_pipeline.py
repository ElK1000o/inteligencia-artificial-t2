"""
Main descriptor pipeline orchestrator for MatEnergy-ML.
Handles caching, versioning, NaN handling, and error tracking.
"""
import numpy as np
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.infrastructure.descriptors.compositional_descriptors import (
    CompositionalDescriptorPipeline,
)
from app.infrastructure.descriptors.structural_descriptors import (
    StructuralDescriptorPipeline,
)
from app.core.exceptions import DescriptorGenerationError, DescriptorNaNError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

DESCRIPTOR_SET_VERSION = "1.0.0"


class DescriptorPipelineOrchestrator:
    """
    Orchestrates descriptor computation for a batch of materials.

    Responsibilities:
      - Delegates to ``CompositionalDescriptorPipeline`` (always).
      - Optionally delegates to ``StructuralDescriptorPipeline``.
      - Applies NaN / Inf imputation (replace with 0.0) when ``impute_nan=True``.
      - Accumulates per-material errors without aborting the whole batch.
      - Tags every result with a ``computed_at`` UTC timestamp and the
        descriptor-set ``version`` string.
    """

    def __init__(
        self,
        include_structural: bool = False,
        impute_nan: bool = True,
    ) -> None:
        self.comp_pipeline = CompositionalDescriptorPipeline()
        self.struct_pipeline = (
            StructuralDescriptorPipeline() if include_structural else None
        )
        self.include_structural = include_structural
        self.impute_nan = impute_nan
        self.version = DESCRIPTOR_SET_VERSION

    # ------------------------------------------------------------------
    # Single-material computation
    # ------------------------------------------------------------------

    def compute_for_material(
        self,
        formula: str,
        structure_dict: Optional[dict] = None,
    ) -> tuple[dict[str, float], list[str]]:
        """
        Compute descriptors for a single material.

        Args:
            formula: Chemical formula string (e.g. ``"LiFePO4"``).
            structure_dict: Optional pymatgen-serialisable structure dict.

        Returns:
            A tuple ``(feature_dict, nan_feature_names)`` where
            ``nan_feature_names`` lists keys whose values were non-finite
            before imputation.

        Raises:
            DescriptorGenerationError: if compositional descriptors fail.
            DescriptorNaNError: if ``impute_nan=False`` and NaN values remain.
        """
        features: dict[str, float] = {}

        # --- Compositional descriptors (mandatory) ---
        try:
            comp_features = self.comp_pipeline.compute(formula)
            features.update(comp_features)
        except Exception as e:
            logger.warning(
                "compositional_descriptor_error",
                formula=formula,
                error=str(e),
            )
            raise DescriptorGenerationError(
                code="COMPOSITIONAL_ERROR",
                message="Failed to compute compositional descriptors",
                detail=str(e),
                recommended_action="Check the chemical formula",
            )

        # --- Structural descriptors (optional) ---
        if self.include_structural and structure_dict:
            try:
                struct_features = self.struct_pipeline.compute(structure_dict)  # type: ignore[union-attr]
                features.update(struct_features)
            except Exception as e:
                logger.warning(
                    "structural_descriptor_error",
                    formula=formula,
                    error=str(e),
                )
                # Degrade gracefully: fill structural slots with 0.0
                for name in StructuralDescriptorPipeline.get_feature_names():
                    features.setdefault(name, 0.0)
        elif self.include_structural and not structure_dict:
            # Pipeline configured for structural but no structure provided
            for name in StructuralDescriptorPipeline.get_feature_names():
                features.setdefault(name, 0.0)

        # --- NaN / Inf handling ---
        nan_features = [
            k for k, v in features.items() if not np.isfinite(v)
        ]
        if nan_features:
            if self.impute_nan:
                for k in nan_features:
                    features[k] = 0.0
            else:
                raise DescriptorNaNError(
                    code="DESCRIPTOR_NAN",
                    message=(
                        f"Non-finite values in descriptor vector for {formula}"
                    ),
                    detail=f"Affected features: {nan_features}",
                    recommended_action=(
                        "Enable NaN imputation or check the formula / structure"
                    ),
                )

        return features, nan_features

    # ------------------------------------------------------------------
    # Batch computation
    # ------------------------------------------------------------------

    def compute_batch(
        self,
        materials: list[dict],
    ) -> dict:
        """
        Compute descriptors for a list of materials.

        Each element of *materials* is expected to have the shape::

            {
                "formula":     str,          # required
                "structure":   dict | None,  # optional
                "material_id": UUID | str | None,
            }

        Returns a result dict with keys:

        * ``vectors``      — list of per-material result dicts.
        * ``feature_names``— ordered list of descriptor names.
        * ``errors``       — list of per-material error dicts.
        * ``n_success``    — count of successfully computed vectors.
        * ``n_error``      — count of failures.
        * ``version``      — descriptor-set version string.
        """
        feature_names = self.get_feature_names()
        vectors: list[dict] = []
        errors: list[dict] = []

        for mat in materials:
            formula: str = mat.get("formula", "")
            structure: Optional[dict] = mat.get("structure")
            mid = mat.get("material_id")

            try:
                feat_dict, nan_feats = self.compute_for_material(
                    formula, structure
                )
                vector = [feat_dict.get(name, 0.0) for name in feature_names]
                vectors.append(
                    {
                        "material_id": mid,
                        "vector": vector,
                        "has_nan": len(nan_feats) > 0,
                        "nan_features": nan_feats,
                        "computed_at": datetime.now(tz=timezone.utc).isoformat(),
                    }
                )
            except Exception as e:
                errors.append(
                    {
                        "material_id": mid,
                        "formula": formula,
                        "error": str(e),
                    }
                )

        return {
            "vectors": vectors,
            "feature_names": feature_names,
            "errors": errors,
            "n_success": len(vectors),
            "n_error": len(errors),
            "version": self.version,
        }

    # ------------------------------------------------------------------
    # Metadata helpers
    # ------------------------------------------------------------------

    def get_feature_names(self) -> list[str]:
        """Return the full ordered list of descriptor feature names."""
        names = CompositionalDescriptorPipeline.get_feature_names()
        if self.include_structural:
            names = names + StructuralDescriptorPipeline.get_feature_names()
        return names

    def get_descriptor_set_metadata(self) -> dict:
        """
        Return a metadata dict describing this descriptor configuration.

        Includes library versions so that stored vectors can be validated
        against the environment that produced them.
        """
        import pymatgen
        import sklearn
        from importlib.metadata import version as _pkg_version

        return {
            "version": self.version,
            "n_features": len(self.get_feature_names()),
            "include_structural": self.include_structural,
            "feature_names": self.get_feature_names(),
            "library_versions": {
                "pymatgen": getattr(pymatgen, "__version__", None) or _pkg_version("pymatgen"),
                "sklearn": sklearn.__version__,
            },
            "descriptor_type": (
                "combined" if self.include_structural else "compositional"
            ),
        }
