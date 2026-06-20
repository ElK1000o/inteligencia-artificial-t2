"""Tests for MaterialCSVLoader validation logic."""
import pytest
import io
from app.infrastructure.materials.csv_loader import MaterialCSVLoader
from app.core.exceptions import MissingRequiredColumnError, DatasetValidationError

class TestCSVLoader:
    def setup_method(self):
        self.loader = MaterialCSVLoader(max_rows=1000)

    def _make_csv(self, rows: list[dict], headers: list[str] | None = None) -> bytes:
        import csv
        output = io.StringIO()
        fieldnames = headers or (list(rows[0].keys()) if rows else ["formula"])
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue().encode("utf-8")

    def test_valid_csv_parses_correctly(self):
        rows = [
            {"formula": "LiFePO4", "energy_above_hull": "0.001"},
            {"formula": "Li2O", "energy_above_hull": "0.0"},
        ]
        result = self.loader.parse_and_validate(self._make_csv(rows))
        assert result["valid_count"] == 2
        assert result["rejected_count"] == 0

    def test_missing_formula_column_raises(self):
        rows = [{"energy": "0.001"}]
        with pytest.raises(MissingRequiredColumnError):
            self.loader.parse_and_validate(self._make_csv(rows, headers=["energy"]))

    def test_empty_formula_rejected(self):
        rows = [{"formula": ""}, {"formula": "Li2O"}]
        result = self.loader.parse_and_validate(self._make_csv(rows))
        assert result["rejected_count"] == 1
        assert result["valid_count"] == 1

    def test_invalid_formula_rejected(self):
        rows = [{"formula": "NOT_A_FORMULA_XYZ999"}]
        result = self.loader.parse_and_validate(self._make_csv(rows), allow_partial=True)
        assert result["rejected_count"] >= 1

    def test_out_of_range_energy_rejected(self):
        rows = [{"formula": "LiFePO4", "energy_above_hull": "999.0"}]
        result = self.loader.parse_and_validate(self._make_csv(rows), allow_partial=True)
        assert result["rejected_count"] == 1

    def test_empty_csv_raises(self):
        with pytest.raises(DatasetValidationError):
            self.loader.parse_and_validate(b"")

    def test_available_properties_detected(self):
        rows = [{"formula": "LiFePO4", "energy_above_hull": "0.001", "band_gap": "3.7"}]
        result = self.loader.parse_and_validate(self._make_csv(rows))
        assert "energy_above_hull" in result["available_properties"]
        assert "band_gap" in result["available_properties"]
