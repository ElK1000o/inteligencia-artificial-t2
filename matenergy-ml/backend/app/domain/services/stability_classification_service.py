from app.core.constants import StabilityLabel
from app.core.config import settings


class StabilityClassificationService:
    """Pure domain service: classifies material thermodynamic stability from energy_above_hull."""

    def __init__(self, threshold_ev: float | None = None):
        self.threshold_ev = threshold_ev or settings.STABILITY_THRESHOLD_EV
        self.borderline_factor = 1.5  # borderline if <= threshold * factor

    def classify(self, energy_above_hull: float) -> StabilityLabel:
        if energy_above_hull <= self.threshold_ev:
            return StabilityLabel.STABLE
        elif energy_above_hull <= self.threshold_ev * self.borderline_factor:
            return StabilityLabel.BORDERLINE
        else:
            return StabilityLabel.UNSTABLE

    def is_stable(self, energy_above_hull: float) -> bool:
        return energy_above_hull <= self.threshold_ev

    def stability_score(self, energy_above_hull: float, max_hull: float = 2.0) -> float:
        """Returns a 0.0-1.0 score where 1.0 = perfectly stable."""
        if energy_above_hull <= 0:
            return 1.0
        return max(0.0, 1.0 - (energy_above_hull / max_hull))
