"""Tests for chemical formula parsing and validation."""
import pytest
from app.domain.services.material_validation_service import MaterialValidationService
from app.core.exceptions import InvalidChemicalFormulaError, InvalidTargetValueError

class TestFormulaValidation:
    def setup_method(self):
        self.svc = MaterialValidationService()

    def test_valid_formula_lifePO4(self):
        self.svc.validate_formula_string("LiFePO4")

    def test_valid_formula_li2o(self):
        self.svc.validate_formula_string("Li2O")

    def test_empty_formula_raises(self):
        with pytest.raises(InvalidChemicalFormulaError) as exc:
            self.svc.validate_formula_string("")
        assert exc.value.code == "EMPTY_FORMULA"

    def test_none_formula_raises(self):
        with pytest.raises(InvalidChemicalFormulaError):
            self.svc.validate_formula_string(None)

    def test_formula_starts_lowercase_raises(self):
        with pytest.raises(InvalidChemicalFormulaError):
            self.svc.validate_formula_string("lifepo4")

    def test_whitespace_only_raises(self):
        with pytest.raises(InvalidChemicalFormulaError):
            self.svc.validate_formula_string("   ")

    def test_valid_complex_formula(self):
        self.svc.validate_formula_string("Li7La3Zr2O12")

    def test_valid_nmc(self):
        self.svc.validate_formula_string("LiNi0.33Mn0.33Co0.33O2")

class TestPropertyRangeValidation:
    def setup_method(self):
        self.svc = MaterialValidationService()

    def test_valid_energy_above_hull(self):
        self.svc.validate_property_value("energy_above_hull", 0.001)

    def test_energy_above_hull_too_high(self):
        with pytest.raises(InvalidTargetValueError) as exc:
            self.svc.validate_property_value("energy_above_hull", 15.0)
        assert exc.value.code == "OUT_OF_RANGE_VALUE"

    def test_energy_above_hull_too_low(self):
        with pytest.raises(InvalidTargetValueError):
            self.svc.validate_property_value("energy_above_hull", -2.0)

    def test_valid_formation_energy(self):
        self.svc.validate_property_value("formation_energy_per_atom", -3.5)

    def test_formation_energy_too_positive(self):
        with pytest.raises(InvalidTargetValueError):
            self.svc.validate_property_value("formation_energy_per_atom", 8.0)

    def test_valid_band_gap(self):
        self.svc.validate_property_value("band_gap", 3.7)

    def test_band_gap_negative_raises(self):
        with pytest.raises(InvalidTargetValueError):
            self.svc.validate_property_value("band_gap", -0.5)

    def test_unknown_property_no_raise(self):
        # Unknown properties have no range constraint
        self.svc.validate_property_value("unknown_property", 999.0)
