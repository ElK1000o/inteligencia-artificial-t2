"""Tests for compositional descriptor generation."""
import pytest
import numpy as np
from app.infrastructure.descriptors.compositional_descriptors import CompositionalDescriptorPipeline
from app.core.exceptions import MissingCompositionError

class TestCompositionalDescriptors:
    def setup_method(self):
        self.pipeline = CompositionalDescriptorPipeline()

    def test_lifepo4_returns_dict(self):
        result = self.pipeline.compute("LiFePO4")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_lifepo4_has_n_elements_4(self):
        result = self.pipeline.compute("LiFePO4")
        assert result["n_elements"] == 4.0

    def test_li2o_has_n_elements_2(self):
        result = self.pipeline.compute("Li2O")
        assert result["n_elements"] == 2.0

    def test_lifepo4_li_fraction_correct(self):
        result = self.pipeline.compute("LiFePO4")
        # LiFePO4: 1 Li, 1 Fe, 1 P, 4 O = 7 atoms total
        # Li fraction = 1/7 ≈ 0.143
        assert abs(result["frac_Li"] - 1/7) < 0.01

    def test_no_nan_in_output(self):
        result = self.pipeline.compute("LiFePO4")
        for k, v in result.items():
            assert not np.isnan(v), f"NaN in {k}"

    def test_empty_formula_raises(self):
        with pytest.raises(MissingCompositionError):
            self.pipeline.compute("")

    def test_feature_names_consistent(self):
        result = self.pipeline.compute("Li2O")
        names = self.pipeline.get_feature_names()
        # All returned keys should be in feature names
        for k in result.keys():
            assert k in names

    def test_complex_formula_works(self):
        result = self.pipeline.compute("LiNi0.33Mn0.33Co0.33O2")
        assert result["n_elements"] >= 4.0
