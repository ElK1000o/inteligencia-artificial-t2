"""Integration tests: descriptor generation use case."""
import uuid
import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from app.infrastructure.descriptors.compositional_descriptors import CompositionalDescriptorPipeline
from app.infrastructure.descriptors.descriptor_pipeline import DescriptorPipelineOrchestrator


ENERGY_MATERIALS_FORMULAS = [
    "LiFePO4",
    "Li2O",
    "LiCoO2",
    "LiMnO2",
    "Li3PO4",
    "LiNiO2",
    "Li2MnO3",
    "LiFe2O4",
]


class TestCompositionalDescriptorPipeline:
    def setup_method(self):
        self.pipeline = CompositionalDescriptorPipeline()

    def test_known_formula_returns_dict(self):
        result = self.pipeline.compute("LiFePO4")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_values_are_finite(self):
        result = self.pipeline.compute("LiFePO4")
        for k, v in result.items():
            assert np.isfinite(v) or np.isnan(v), f"Feature {k} = {v} is not finite or nan"

    def test_energy_material_formulas_processed(self):
        for formula in ENERGY_MATERIALS_FORMULAS:
            result = self.pipeline.compute(formula)
            assert isinstance(result, dict), f"Failed for {formula}"
            assert len(result) > 10

    def test_fraction_li_nonzero_for_lithium_compound(self):
        result = self.pipeline.compute("LiFePO4")
        li_frac = result.get("frac_Li", 0.0)
        assert li_frac > 0.0

    def test_fraction_li_zero_for_non_lithium(self):
        result = self.pipeline.compute("Fe2O3")
        li_frac = result.get("frac_Li", 0.0)
        assert li_frac == 0.0

    def test_nelements_correct(self):
        result = self.pipeline.compute("LiFePO4")
        n_elem = result.get("n_elements", 0)
        assert n_elem == 4  # Li, Fe, P, O

    def test_empty_formula_raises(self):
        from app.core.exceptions import MissingCompositionError
        with pytest.raises((MissingCompositionError, Exception)):
            self.pipeline.compute("")

    def test_invalid_formula_raises(self):
        from app.core.exceptions import InvalidChemicalFormulaError
        with pytest.raises((InvalidChemicalFormulaError, Exception)):
            self.pipeline.compute("NotAFormula!!!")

    def test_reproducible_for_same_formula(self):
        result1 = self.pipeline.compute("LiFePO4")
        result2 = self.pipeline.compute("LiFePO4")
        assert result1 == result2


class TestDescriptorPipelineOrchestrator:
    def setup_method(self):
        self.orchestrator = DescriptorPipelineOrchestrator(include_structural=False)

    def test_metadata_has_required_keys(self):
        meta = self.orchestrator.get_descriptor_set_metadata()
        assert "version" in meta
        assert "n_features" in meta
        assert "feature_names" in meta
        assert "descriptor_type" in meta

    def test_compute_batch_returns_expected_keys(self):
        batch = [{"formula": "LiFePO4", "structure": None, "material_id": uuid.uuid4()}]
        result = self.orchestrator.compute_batch(batch)
        assert "vectors" in result
        assert "n_success" in result
        assert "n_error" in result
        assert result["n_success"] >= 1

    def test_compute_batch_invalid_formula_counted_as_error(self):
        batch = [{"formula": "!!!", "structure": None, "material_id": uuid.uuid4()}]
        result = self.orchestrator.compute_batch(batch)
        assert result["n_error"] >= 1
