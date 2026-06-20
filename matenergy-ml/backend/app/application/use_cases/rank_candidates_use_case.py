"""
RankCandidatesUseCase
=====================
Scores and ranks every material in a dataset using transparent,
rule-based scoring via ``CandidateScoringService``.

No generative AI is involved.  All scores are deterministic and
derived from stored material properties plus optional model predictions.

Pipeline
--------
1. Fetch all materials for the dataset.
2. For each material:
   a. Resolve energy_above_hull → stability score.
   b. Pull the latest model prediction (if a model_version_id is given).
   c. Compute a composite score via ``CandidateScoringService``.
3. Sort by composite score (descending).
4. Persist ``CandidateRanking`` + ``CandidateRankingItem`` rows.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.constants import ApplicationTarget, CandidatePriority
from app.core.logging_config import get_logger
from app.domain.entities.candidate_ranking import CandidateRankingItem, RankingWeights
from app.domain.entities.material import Material as MaterialEntity, MaterialCompositionItem
from app.domain.services.candidate_scoring_service import CandidateScoringService
from app.domain.services.stability_classification_service import (
    StabilityClassificationService,
)
from app.infrastructure.database.models.material_models import Material as MaterialModel
from app.infrastructure.database.models.ranking_models import (
    CandidateRanking as CandidateRankingModel,
    CandidateRankingItem as CandidateRankingItemModel,
)
from app.infrastructure.database.repositories import (
    MaterialRepository,
    PredictionRepository,
)
from app.infrastructure.database.repositories.material_repository import (
    MaterialPropertyRepository,
)

logger = get_logger(__name__)

_stability_svc = StabilityClassificationService()


class RankCandidatesUseCase:
    """
    Scores and ranks candidate materials for a given application target.

    Args:
        db: Active SQLAlchemy ``Session``.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def execute(
        self,
        name: str,
        application_target: ApplicationTarget,
        dataset_id: uuid.UUID,
        user_id: uuid.UUID,
        weights: RankingWeights,
        model_version_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Score and rank all materials in *dataset_id*.

        Args:
            name:               Human-readable name for this ranking run.
            application_target: Energy-storage application context.
            dataset_id:         Source dataset.
            user_id:            Requesting user.
            weights:            ``RankingWeights`` instance (must sum to 1.0
                                if ``validate()`` is called externally).
            model_version_id:   Optional — use predictions from this model
                                instead of raw property values.
            description:        Free-text annotation stored on the ranking.

        Returns:
            {
                "ranking_id"  : str,
                "n_candidates": int,
                "top_5"       : list[dict],  — [{rank, material_id, score, priority}]
            }

        Raises:
            ValueError: No materials found for the dataset.
        """
        mat_repo = MaterialRepository(self.db)
        pred_repo = PredictionRepository(self.db)
        prop_repo = MaterialPropertyRepository(self.db)

        materials = mat_repo.get_by_dataset(dataset_id, limit=10_000)
        if not materials:
            raise ValueError(
                f"No materials found for dataset {dataset_id}. "
                "Import the dataset first."
            )

        scorer = CandidateScoringService(
            weights=weights, application_target=application_target
        )

        # ---- Create CandidateRanking header ------------------------------
        ranking_db = CandidateRankingModel(
            id=uuid.uuid4(),
            name=name,
            application_target=application_target.value,
            dataset_id=dataset_id,
            model_version_id=model_version_id,
            weights={
                "stability_weight": weights.stability_weight,
                "target_property_weight": weights.target_property_weight,
                "energy_relevance_weight": weights.energy_relevance_weight,
                "abundance_weight": weights.abundance_weight,
                "toxicity_penalty_weight": weights.toxicity_penalty_weight,
                "uncertainty_penalty_weight": weights.uncertainty_penalty_weight,
                "out_of_domain_penalty_weight": weights.out_of_domain_penalty_weight,
            },
            n_candidates=0,
            description=description,
            created_by=user_id,
        )
        self.db.add(ranking_db)
        self.db.flush()

        # ---- Score each material -----------------------------------------
        scored_items: list[tuple[uuid.UUID, CandidateRankingItem]] = []

        for mat in materials:
            mat_entity = self._to_entity(mat)

            # Stability score from energy_above_hull
            energy_hull = self._get_float_property(prop_repo, mat.id, "energy_above_hull")
            stab_score: float = (
                _stability_svc.stability_score(energy_hull)
                if energy_hull is not None
                else 0.3  # unknown stability → moderate-low default
            )

            # Prediction value: use model output if available, else fallback
            is_ood = False
            uncertainty: Optional[float] = None
            pred_val: Optional[float] = energy_hull

            if model_version_id is not None:
                predictions = pred_repo.get_by_material(mat.id)
                # Filter to predictions whose batch was produced by the
                # requested model version.  ``Prediction.batch`` is eagerly
                # accessible via the ORM relationship.
                mv_preds = [
                    p for p in predictions
                    if p.batch and str(p.batch.model_version_id) == str(model_version_id)
                ]
                if mv_preds:
                    latest = mv_preds[0]
                    pred_val = latest.predicted_value
                    is_ood = bool(latest.is_out_of_domain)
                    # confidence_score used as a proxy for uncertainty when
                    # dedicated uncertainty is not stored
                    uncertainty = (
                        1.0 - latest.confidence_score
                        if latest.confidence_score is not None
                        else None
                    )
            else:
                # No model specified — use the most recent prediction if any
                predictions = pred_repo.get_by_material(mat.id)
                if predictions:
                    latest = predictions[0]
                    pred_val = latest.predicted_value if latest.predicted_value is not None else energy_hull
                    is_ood = bool(latest.is_out_of_domain)

            item = scorer.compute_score(
                material=mat_entity,
                stability_score=stab_score,
                predicted_value=pred_val,
                is_out_of_domain=is_ood,
                uncertainty=uncertainty,
                target_property="energy_above_hull",
            )
            scored_items.append((mat.id, item))

        # ---- Sort by score descending ------------------------------------
        scored_items.sort(key=lambda x: x[1].candidate_score, reverse=True)

        # ---- Persist ranking items ---------------------------------------
        for rank_pos, (mat_id, item) in enumerate(scored_items, start=1):
            self.db.add(
                CandidateRankingItemModel(
                    id=uuid.uuid4(),
                    ranking_id=ranking_db.id,
                    material_id=mat_id,
                    rank_position=rank_pos,
                    candidate_score=item.candidate_score,
                    priority_label=item.priority_label.value,
                    stability_score=item.stability_score,
                    target_property_score=item.target_property_score,
                    energy_relevance_score=item.energy_relevance_score,
                    abundance_score=item.abundance_score,
                    toxicity_penalty=item.toxicity_penalty,
                    uncertainty_penalty=item.uncertainty_penalty,
                    out_of_domain_penalty=item.out_of_domain_penalty,
                    reasoning_summary=item.reasoning_summary,
                )
            )

        ranking_db.n_candidates = len(scored_items)
        self.db.commit()

        logger.info(
            "candidates_ranked",
            ranking_id=str(ranking_db.id),
            n_candidates=len(scored_items),
            application_target=application_target.value,
        )

        top_5 = [
            {
                "rank": i + 1,
                "material_id": str(scored_items[i][0]),
                "score": scored_items[i][1].candidate_score,
                "priority": scored_items[i][1].priority_label.value,
            }
            for i in range(min(5, len(scored_items)))
        ]

        return {
            "ranking_id": str(ranking_db.id),
            "n_candidates": len(scored_items),
            "top_5": top_5,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_entity(mat: MaterialModel) -> MaterialEntity:
        """Convert ORM ``Material`` to domain ``Material`` entity."""
        composition = [
            MaterialCompositionItem(
                element_symbol=c.element_symbol,
                fraction=c.fraction,
            )
            for c in (mat.compositions if hasattr(mat, "compositions") else [])
        ]
        return MaterialEntity(
            id=mat.id,
            formula=mat.formula,
            reduced_formula=mat.reduced_formula or mat.formula,
            chemsys=mat.chemsys or "",
            dataset_id=mat.dataset_id,
            nelements=mat.nelements or 1,
            elements=mat.elements or [],
            composition=composition,
        )

    @staticmethod
    def _get_float_property(
        repo: MaterialPropertyRepository,
        material_id: uuid.UUID,
        prop_name: str,
    ) -> Optional[float]:
        """Return the float value of a material property, or None."""
        prop = repo.get_by_material_and_property(material_id, prop_name)
        return prop.value_float if prop else None
