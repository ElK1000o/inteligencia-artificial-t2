"""Tests for candidate scoring service."""
import pytest
import uuid
from app.domain.entities.material import Material, MaterialCompositionItem
from app.domain.entities.candidate_ranking import RankingWeights
from app.domain.services.candidate_scoring_service import CandidateScoringService
from app.core.constants import ApplicationTarget, CandidatePriority

def make_lifepo4() -> Material:
    return Material(
        id=uuid.uuid4(),
        formula="LiFePO4",
        reduced_formula="LiFePO4",
        chemsys="Fe-Li-O-P",
        dataset_id=uuid.uuid4(),
        nelements=4,
        elements=["Li", "Fe", "P", "O"],
        composition=[
            MaterialCompositionItem("Li", 0.143),
            MaterialCompositionItem("Fe", 0.143),
            MaterialCompositionItem("P", 0.143),
            MaterialCompositionItem("O", 0.571),
        ],
    )

class TestCandidateScoring:
    def setup_method(self):
        self.weights = RankingWeights()
        self.scorer = CandidateScoringService(self.weights, ApplicationTarget.LI_ION_BATTERIES)
        self.mat = make_lifepo4()

    def test_score_is_in_range(self):
        item = self.scorer.compute_score(
            material=self.mat,
            stability_score=0.9,
            predicted_value=0.001,
            is_out_of_domain=False,
            uncertainty=None,
            target_property="energy_above_hull",
        )
        assert 0.0 <= item.candidate_score <= 1.0

    def test_stable_material_scores_higher(self):
        item_stable = self.scorer.compute_score(
            material=self.mat, stability_score=0.95, predicted_value=0.001,
            is_out_of_domain=False, uncertainty=None, target_property="energy_above_hull"
        )
        item_unstable = self.scorer.compute_score(
            material=self.mat, stability_score=0.1, predicted_value=1.5,
            is_out_of_domain=False, uncertainty=None, target_property="energy_above_hull"
        )
        assert item_stable.candidate_score > item_unstable.candidate_score

    def test_ood_material_gets_penalty(self):
        item_ood = self.scorer.compute_score(
            material=self.mat, stability_score=0.8, predicted_value=0.001,
            is_out_of_domain=True, uncertainty=None, target_property="energy_above_hull"
        )
        item_in_domain = self.scorer.compute_score(
            material=self.mat, stability_score=0.8, predicted_value=0.001,
            is_out_of_domain=False, uncertainty=None, target_property="energy_above_hull"
        )
        assert item_ood.candidate_score < item_in_domain.candidate_score

    def test_reasoning_is_not_empty(self):
        item = self.scorer.compute_score(
            material=self.mat, stability_score=0.9, predicted_value=0.001,
            is_out_of_domain=False, uncertainty=None, target_property="energy_above_hull"
        )
        assert len(item.reasoning_summary) > 10

    def test_reasoning_mentions_ood_when_ood(self):
        item = self.scorer.compute_score(
            material=self.mat, stability_score=0.5, predicted_value=0.05,
            is_out_of_domain=True, uncertainty=None, target_property="energy_above_hull"
        )
        assert "domain" in item.reasoning_summary.lower()

    def test_high_priority_for_excellent_score(self):
        item = self.scorer.compute_score(
            material=self.mat, stability_score=0.99, predicted_value=0.0001,
            is_out_of_domain=False, uncertainty=0.01, target_property="energy_above_hull"
        )
        assert item.priority_label == CandidatePriority.HIGH

    def test_not_recommended_for_very_low_score(self):
        item = self.scorer.compute_score(
            material=self.mat, stability_score=0.01, predicted_value=2.0,
            is_out_of_domain=True, uncertainty=0.8, target_property="energy_above_hull"
        )
        assert item.priority_label in (CandidatePriority.NOT_RECOMMENDED, CandidatePriority.LOW, CandidatePriority.INSUFFICIENT)
