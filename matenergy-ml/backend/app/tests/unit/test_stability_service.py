"""Tests for StabilityClassificationService."""
import pytest
from app.domain.services.stability_classification_service import StabilityClassificationService
from app.core.constants import StabilityLabel

class TestStabilityClassification:
    def setup_method(self):
        self.svc = StabilityClassificationService(threshold_ev=0.05)

    def test_stable_material(self):
        assert self.svc.classify(0.001) == StabilityLabel.STABLE

    def test_exactly_at_threshold_is_stable(self):
        assert self.svc.classify(0.05) == StabilityLabel.STABLE

    def test_borderline_material(self):
        result = self.svc.classify(0.07)
        assert result == StabilityLabel.BORDERLINE

    def test_unstable_material(self):
        assert self.svc.classify(0.5) == StabilityLabel.UNSTABLE

    def test_is_stable_true(self):
        assert self.svc.is_stable(0.02) is True

    def test_is_stable_false(self):
        assert self.svc.is_stable(0.1) is False

    def test_stability_score_perfect(self):
        score = self.svc.stability_score(0.0)
        assert score == 1.0

    def test_stability_score_zero_at_max(self):
        score = self.svc.stability_score(2.0)
        assert score == 0.0

    def test_stability_score_intermediate(self):
        score = self.svc.stability_score(1.0)
        assert 0.0 < score < 1.0

    def test_stability_score_negative_hull_is_1(self):
        score = self.svc.stability_score(-0.1)
        assert score == 1.0
