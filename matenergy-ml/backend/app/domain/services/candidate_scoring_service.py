from app.core.constants import CandidatePriority, ApplicationTarget
from app.domain.entities.candidate_ranking import RankingWeights, CandidateRankingItem
from app.domain.entities.material import Material
from app.domain.entities.prediction import Prediction
from typing import Optional
from uuid import UUID

ABUNDANT_ELEMENTS = {"Li", "Na", "Fe", "Mn", "Ti", "Al", "Si", "O", "S", "P", "Ca", "Mg"}
TOXIC_OR_SCARCE = {"Co", "Ni", "As", "Hg", "Pb", "Cd", "Cr"}
ENERGY_RELEVANT = {"Li", "Na", "Fe", "Mn", "Co", "Ni", "O", "S", "P", "Cu"}

TARGET_RELEVANT_ELEMENTS: dict[ApplicationTarget, set[str]] = {
    ApplicationTarget.LI_ION_BATTERIES: {"Li", "Fe", "Mn", "Co", "Ni", "O", "P"},
    ApplicationTarget.SOLID_STATE_BATTERIES: {"Li", "P", "S", "O", "Ge", "La"},
    ApplicationTarget.CATHODE_MATERIALS: {"Li", "Fe", "Mn", "Co", "Ni", "O"},
    ApplicationTarget.ANODE_MATERIALS: {"Li", "Si", "C", "Ti", "Sn"},
    ApplicationTarget.SOLID_ELECTROLYTES: {"Li", "P", "S", "O", "La", "Zr"},
    ApplicationTarget.GENERAL_ENERGY_STORAGE: {"Li", "Na", "Fe", "Mn", "O", "S", "P"},
}


class CandidateScoringService:
    """Transparent, rule-based candidate scoring. No generative AI."""

    def __init__(self, weights: RankingWeights, application_target: ApplicationTarget):
        self.weights = weights
        self.target = application_target
        self._relevant = TARGET_RELEVANT_ELEMENTS.get(application_target, set())

    def compute_score(
        self,
        material: Material,
        stability_score: float,
        predicted_value: Optional[float],
        is_out_of_domain: bool,
        uncertainty: Optional[float],
        target_property: str,
    ) -> CandidateRankingItem:
        # Component scores
        stab_score = stability_score
        target_score = self._target_property_score(predicted_value, target_property)
        energy_score = self._energy_relevance_score(material)
        abund_score = self._abundance_score(material)
        tox_penalty = self._toxicity_penalty(material)
        unc_penalty = self._uncertainty_penalty(uncertainty)
        ood_penalty = 0.3 if is_out_of_domain else 0.0

        w = self.weights
        raw_score = (
            w.stability_weight * stab_score
            + w.target_property_weight * target_score
            + w.energy_relevance_weight * energy_score
            + w.abundance_weight * abund_score
            - w.toxicity_penalty_weight * tox_penalty
            - w.uncertainty_penalty_weight * unc_penalty
            - w.out_of_domain_penalty_weight * ood_penalty
        )
        final_score = max(0.0, min(1.0, raw_score))
        priority = self._assign_priority(final_score, is_out_of_domain, uncertainty)
        reasoning = self._build_reasoning(
            material,
            stab_score,
            target_score,
            energy_score,
            is_out_of_domain,
            uncertainty,
            target_property,
            predicted_value,
        )

        return CandidateRankingItem(
            material_id=material.id,
            rank_position=0,  # set externally after sorting
            candidate_score=final_score,
            priority_label=priority,
            reasoning_summary=reasoning,
            stability_score=stab_score,
            target_property_score=target_score,
            energy_relevance_score=energy_score,
            abundance_score=abund_score,
            toxicity_penalty=tox_penalty,
            uncertainty_penalty=unc_penalty,
            out_of_domain_penalty=ood_penalty,
        )

    def _target_property_score(self, value: Optional[float], prop: str) -> float:
        if value is None:
            return 0.0
        if prop == "energy_above_hull":
            return max(0.0, 1.0 - value / 2.0)
        if prop == "formation_energy_per_atom":
            return max(0.0, 1.0 - (value + 5.0) / 10.0) if value < 0 else 0.0
        if prop == "band_gap":
            # For battery materials: prefer low band gap (conductor/semiconductor)
            return max(0.0, 1.0 - value / 5.0)
        return 0.5

    def _energy_relevance_score(self, material: Material) -> float:
        overlap = sum(1 for e in material.elements if e in self._relevant)
        return min(1.0, overlap / max(1, len(self._relevant) * 0.5))

    def _abundance_score(self, material: Material) -> float:
        abundant = sum(1 for e in material.elements if e in ABUNDANT_ELEMENTS)
        return abundant / len(material.elements) if material.elements else 0.0

    def _toxicity_penalty(self, material: Material) -> float:
        toxic = sum(1 for e in material.elements if e in TOXIC_OR_SCARCE)
        return min(1.0, toxic / len(material.elements)) if material.elements else 0.0

    def _uncertainty_penalty(self, uncertainty: Optional[float]) -> float:
        if uncertainty is None:
            return 0.1  # small penalty for unknown uncertainty
        return min(1.0, uncertainty / 0.5)

    def _assign_priority(
        self, score: float, ood: bool, unc: Optional[float]
    ) -> CandidatePriority:
        if ood and score < 0.4:
            return CandidatePriority.INSUFFICIENT
        if score >= 0.70:
            return CandidatePriority.HIGH
        if score >= 0.50:
            return CandidatePriority.MODERATE
        if score >= 0.30:
            return CandidatePriority.LOW
        return CandidatePriority.NOT_RECOMMENDED

    def _build_reasoning(
        self,
        material: Material,
        stab: float,
        target: float,
        energy: float,
        ood: bool,
        unc: Optional[float],
        prop: str,
        value: Optional[float],
    ) -> str:
        parts = []
        if stab >= 0.8:
            parts.append("la estabilidad termodinámica predicha es alta")
        elif stab >= 0.5:
            parts.append("la estabilidad termodinámica predicha es moderada")
        else:
            parts.append("la estabilidad termodinámica predicha es baja")

        if value is not None:
            parts.append(f"el valor predicho de {prop.replace('_', ' ')} es {value:.4f}")

        relevant = [e for e in material.elements if e in self._relevant]
        if relevant:
            parts.append(f"contiene elementos relevantes para energía ({', '.join(relevant)})")

        toxic = [e for e in material.elements if e in TOXIC_OR_SCARCE]
        if toxic:
            parts.append(
                f"contiene elementos con riesgos de toxicidad o de cadena de suministro ({', '.join(toxic)})"
            )

        if ood:
            parts.append(
                "la predicción está fuera del dominio químico de entrenamiento — los resultados requieren precaución"
            )

        if unc and unc > 0.3:
            parts.append(f"la alta incertidumbre de predicción ({unc:.3f}) reduce la confianza")

        parts.append(
            "la viabilidad de síntesis y la estabilidad de ciclado electroquímico requieren validación experimental"
        )

        reasoning = "; ".join(parts)
        return reasoning[0].upper() + reasoning[1:] + "."
