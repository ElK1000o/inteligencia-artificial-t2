"""Integration tests: candidate ranking use case."""
import uuid
import pytest
from unittest.mock import MagicMock, patch

from app.domain.entities.candidate_ranking import RankingWeights
from app.domain.entities.material import Material
from app.domain.entities.prediction import Prediction
from app.domain.services.candidate_scoring_service import CandidateScoringService
from app.core.constants import ApplicationTarget, CandidatePriority


DEFAULT_WEIGHTS = RankingWeights(
    stability_weight=0.35,
    target_property_weight=0.30,
    energy_relevance_weight=0.15,
    abundance_weight=0.10,
    toxicity_penalty_weight=0.05,
    uncertainty_penalty_weight=0.03,
    out_of_domain_penalty_weight=0.02,
)


def _make_material(formula: str, elements: list) -> Material:
    m = MagicMock(spec=Material)
    m.formula = formula
    m.elements = elements
    return m


def _make_prediction(predicted_value: float) -> Prediction:
    p = MagicMock(spec=Prediction)
    p.predicted_value = predicted_value
    p.is_out_of_domain = False
    p.confidence_score = None
    return p


class TestCandidateScoringService:
    def setup_method(self):
        self.scorer = CandidateScoringService(
            weights=DEFAULT_WEIGHTS,
            application_target=ApplicationTarget.LI_ION_BATTERIES,
        )

    def test_lifepo4_gets_high_score(self):
        mat = _make_material("LiFePO4", ["Li", "Fe", "P", "O"])
        item = self.scorer.compute_score(
            material=mat,
            stability_score=1.0,   # very stable
            predicted_value=0.001, # near zero energy above hull
            is_out_of_domain=False,
            uncertainty=None,
            target_property="energy_above_hull",
        )
        assert item.candidate_score >= 0.5

    def test_toxic_material_penalized(self):
        mat_clean = _make_material("LiFePO4", ["Li", "Fe", "P", "O"])
        mat_toxic = _make_material("LiCoO2", ["Li", "Co", "O"])

        item_clean = self.scorer.compute_score(
            material=mat_clean,
            stability_score=1.0,
            predicted_value=0.001,
            is_out_of_domain=False,
            uncertainty=None,
            target_property="energy_above_hull",
        )
        item_toxic = self.scorer.compute_score(
            material=mat_toxic,
            stability_score=1.0,
            predicted_value=0.001,
            is_out_of_domain=False,
            uncertainty=None,
            target_property="energy_above_hull",
        )
        # LiFePO4 (no toxic elements) should score >= LiCoO2 (Co is penalized)
        assert item_clean.candidate_score >= item_toxic.candidate_score

    def test_ood_material_penalized(self):
        mat = _make_material("LiFePO4", ["Li", "Fe", "P", "O"])
        item_in_domain = self.scorer.compute_score(
            material=mat, stability_score=1.0, predicted_value=0.001,
            is_out_of_domain=False, uncertainty=None, target_property="energy_above_hull",
        )
        item_ood = self.scorer.compute_score(
            material=mat, stability_score=1.0, predicted_value=0.001,
            is_out_of_domain=True, uncertainty=None, target_property="energy_above_hull",
        )
        assert item_in_domain.candidate_score > item_ood.candidate_score

    def test_score_clamped_between_0_and_1(self):
        mat = _make_material("LiFePO4", ["Li", "Fe", "P", "O"])
        item = self.scorer.compute_score(
            material=mat, stability_score=1.0, predicted_value=0.0001,
            is_out_of_domain=False, uncertainty=None, target_property="energy_above_hull",
        )
        assert 0.0 <= item.candidate_score <= 1.0

    def test_reasoning_summary_is_not_empty(self):
        mat = _make_material("LiFePO4", ["Li", "Fe", "P", "O"])
        item = self.scorer.compute_score(
            material=mat, stability_score=0.9, predicted_value=0.005,
            is_out_of_domain=False, uncertainty=None, target_property="energy_above_hull",
        )
        assert len(item.reasoning_summary) > 20

    def test_priority_labels_are_valid(self):
        mat = _make_material("LiFePO4", ["Li", "Fe", "P", "O"])
        item = self.scorer.compute_score(
            material=mat, stability_score=1.0, predicted_value=0.001,
            is_out_of_domain=False, uncertainty=None, target_property="energy_above_hull",
        )
        valid_labels = {p.value for p in CandidatePriority}
        assert item.priority_label in valid_labels

    def test_different_application_targets(self):
        for target in ApplicationTarget:
            scorer = CandidateScoringService(
                weights=DEFAULT_WEIGHTS,
                application_target=target,
            )
            mat = _make_material("LiFePO4", ["Li", "Fe", "P", "O"])
            item = scorer.compute_score(
                material=mat, stability_score=0.8, predicted_value=0.01,
                is_out_of_domain=False, uncertainty=None, target_property="energy_above_hull",
            )
            assert 0.0 <= item.candidate_score <= 1.0
