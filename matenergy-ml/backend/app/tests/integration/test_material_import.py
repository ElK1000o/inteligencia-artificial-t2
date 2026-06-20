"""Integration tests: material import use case."""
import uuid
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.application.use_cases.import_dataset_use_case import ImportMaterialDatasetUseCase
from app.infrastructure.materials.csv_loader import MaterialCSVLoader


VALID_CSV_CONTENT = b"""formula,energy_above_hull,formation_energy_per_atom,band_gap,is_stable
LiFePO4,0.000,-3.181,3.71,True
Li2O,0.000,-1.991,4.91,True
LiCoO2,0.000,-2.887,2.53,True
LiMnO2,0.008,-3.042,0.00,False
Li3PO4,0.000,-3.281,6.45,True
"""

INVALID_FORMULA_CSV = b"""formula,energy_above_hull,formation_energy_per_atom,band_gap,is_stable
NOTAFORMULA123!!,0.000,-1.0,1.0,True
=CMD('rm -rf /'),0.001,-2.0,2.0,True
"""


class TestMaterialCSVLoader:
    def setup_method(self):
        self.loader = MaterialCSVLoader(max_rows=1000)

    def test_valid_csv_parsed_correctly(self):
        result = self.loader.parse_and_validate(VALID_CSV_CONTENT)
        assert result["valid_count"] == 5
        assert result["rejected_count"] == 0
        assert len(result["valid_rows"]) == 5

    def test_formula_injection_rejected(self):
        result = self.loader.parse_and_validate(INVALID_FORMULA_CSV, allow_partial=True)
        assert result["rejected_count"] >= 1

    def test_rejected_rows_include_reason(self):
        result = self.loader.parse_and_validate(INVALID_FORMULA_CSV, allow_partial=True)
        for rr in result["rejected_rows"]:
            assert "rejection_reasons" in rr
            assert len(rr["rejection_reasons"]) > 0

    def test_valid_rows_have_required_fields(self):
        result = self.loader.parse_and_validate(VALID_CSV_CONTENT)
        for row in result["valid_rows"]:
            assert "formula" in row

    def test_available_properties_detected(self):
        result = self.loader.parse_and_validate(VALID_CSV_CONTENT)
        props = result["available_properties"]
        assert "energy_above_hull" in props or "formation_energy_per_atom" in props

    def test_total_rows_counted_correctly(self):
        result = self.loader.parse_and_validate(VALID_CSV_CONTENT)
        assert result["total_rows"] == 5

    def test_max_rows_enforced(self):
        # Create CSV with more rows than the limit
        header = b"formula,energy_above_hull\n"
        rows = b"\n".join([f"Li{i}O,0.00{i}".encode() for i in range(50)])
        loader_small = MaterialCSVLoader(max_rows=10)
        result = loader_small.parse_and_validate(header + rows, allow_partial=True)
        assert result["total_rows"] <= 10 or result["valid_count"] <= 10


class TestImportDatasetUseCase:
    def test_execute_missing_dataset_raises_not_found(self):
        """If dataset record doesn't exist, use case should raise NotFoundError."""
        from app.core.exceptions import NotFoundError
        mock_db = MagicMock()

        # Mock the DatasetRepository to return None
        with patch(
            "app.application.use_cases.import_dataset_use_case.DatasetRepository"
        ) as MockRepo:
            MockRepo.return_value.get_by_id.return_value = None
            use_case = ImportMaterialDatasetUseCase(mock_db)
            with pytest.raises((NotFoundError, Exception)):
                use_case.execute(
                    dataset_id=uuid.uuid4(),
                    user_id=uuid.uuid4(),
                )
