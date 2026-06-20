"""Integration tests: report generator."""
import pytest
from app.infrastructure.reports.report_generator import ReportGenerator


SAMPLE_METRICS = [
    {"split": "train", "metric_name": "mae", "metric_value": 0.15},
    {"split": "train", "metric_name": "r2", "metric_value": 0.82},
    {"split": "test", "metric_name": "mae", "metric_value": 0.22},
    {"split": "test", "metric_name": "r2", "metric_value": 0.74},
    {"split": "cv", "metric_name": "mae_cv_mean", "metric_value": 0.20},
]

SAMPLE_ITEMS = [
    {
        "rank_position": 1,
        "material_id": "aaa",
        "candidate_score": 0.92,
        "priority_label": "high_priority",
        "reasoning_summary": "Low energy above hull, contains Li and Fe.",
        "stability_score": 1.0,
        "uncertainty_penalty": 0.0,
        "is_out_of_domain": False,
    },
    {
        "rank_position": 2,
        "material_id": "bbb",
        "candidate_score": 0.75,
        "priority_label": "moderate_priority",
        "reasoning_summary": "Stable but contains Co (toxicity penalty).",
        "stability_score": 0.9,
        "uncertainty_penalty": 0.0,
        "is_out_of_domain": False,
    },
]

SAMPLE_DATASET = {
    "name": "Demo Dataset",
    "sha256_hash": "abc123" * 10,
    "status": "valid",
    "row_count": 154,
    "valid_row_count": 152,
    "rejected_row_count": 2,
    "available_properties": ["energy_above_hull", "band_gap"],
}


class TestReportGenerator:
    def setup_method(self):
        self.gen = ReportGenerator()

    def test_ranking_csv_is_bytes(self):
        result = self.gen.generate_ranking_csv(
            ranking_name="Test Ranking",
            items=SAMPLE_ITEMS,
            material_formulas={"aaa": "LiFePO4", "bbb": "LiCoO2"},
        )
        assert isinstance(result, bytes)

    def test_ranking_csv_has_header(self):
        result = self.gen.generate_ranking_csv(
            ranking_name="Test Ranking",
            items=SAMPLE_ITEMS,
            material_formulas={"aaa": "LiFePO4", "bbb": "LiCoO2"},
        )
        text = result.decode("utf-8")
        assert "Rank" in text or "rank" in text.lower()
        assert "Formula" in text or "formula" in text.lower()

    def test_ranking_csv_contains_all_items(self):
        result = self.gen.generate_ranking_csv(
            ranking_name="Test Ranking",
            items=SAMPLE_ITEMS,
            material_formulas={"aaa": "LiFePO4", "bbb": "LiCoO2"},
        )
        text = result.decode("utf-8")
        assert "LiFePO4" in text
        assert "LiCoO2" in text

    def test_model_metrics_report_is_string(self):
        result = self.gen.generate_model_metrics_report("Test Model", SAMPLE_METRICS)
        assert isinstance(result, str)
        assert len(result) > 100

    def test_model_metrics_report_contains_all_splits(self):
        result = self.gen.generate_model_metrics_report("Test Model", SAMPLE_METRICS)
        assert "train" in result.lower()
        assert "test" in result.lower()

    def test_model_metrics_report_has_model_name(self):
        result = self.gen.generate_model_metrics_report("RandomForestRegressor", SAMPLE_METRICS)
        assert "RandomForestRegressor" in result

    def test_dataset_summary_is_string(self):
        result = self.gen.generate_dataset_summary(SAMPLE_DATASET)
        assert isinstance(result, str)
        assert "Demo Dataset" in result

    def test_dataset_summary_has_sha256(self):
        result = self.gen.generate_dataset_summary(SAMPLE_DATASET)
        assert "abc123" in result

    def test_dataset_summary_with_validation_report(self):
        val_report = {
            "validated_at": "2025-01-01T00:00:00Z",
            "validation_rules_applied": ["formula_parseable", "range_checks"],
            "warnings": ["2 rows had missing band_gap values"],
        }
        result = self.gen.generate_dataset_summary(SAMPLE_DATASET, validation_report=val_report)
        assert "Validation Report" in result
        assert "formula_parseable" in result

    def test_empty_items_produces_valid_csv(self):
        result = self.gen.generate_ranking_csv(
            ranking_name="Empty", items=[], material_formulas={}
        )
        assert isinstance(result, bytes)
        text = result.decode("utf-8")
        # Should at minimum have the header row
        assert len(text.strip().split("\n")) >= 1
