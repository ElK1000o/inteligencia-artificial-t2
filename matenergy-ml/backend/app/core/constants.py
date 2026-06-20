"""
Domain constants and enumerations for MatEnergy-ML.
"""
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    RESEARCHER = "researcher"
    VIEWER = "viewer"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class StabilityLabel(str, Enum):
    STABLE = "stable"
    UNSTABLE = "unstable"
    BORDERLINE = "borderline"


class CandidatePriority(str, Enum):
    HIGH = "high_priority"
    MODERATE = "moderate_priority"
    LOW = "low_priority"
    NOT_RECOMMENDED = "not_recommended"
    INSUFFICIENT = "insufficient_evidence"


class ApplicationTarget(str, Enum):
    LI_ION_BATTERIES = "li_ion_batteries"
    SOLID_STATE_BATTERIES = "solid_state_batteries"
    CATHODE_MATERIALS = "cathode_materials"
    ANODE_MATERIALS = "anode_materials"
    SOLID_ELECTROLYTES = "solid_electrolytes"
    GENERAL_ENERGY_STORAGE = "general_energy_storage"


class DataSource(str, Enum):
    CSV_LOCAL = "csv_local"
    MATERIALS_PROJECT = "materials_project"
    JARVIS = "jarvis"
    OQMD = "oqmd"
    NOMAD = "nomad"
    AFLOW = "aflow"
    MATBENCH = "matbench"
    DEMO = "demo"


class ModelType(str, Enum):
    RIDGE_REGRESSION = "ridge_regression"
    RANDOM_FOREST_REGRESSOR = "random_forest_regressor"
    RANDOM_FOREST_CLASSIFIER = "random_forest_classifier"
    GRADIENT_BOOSTING_REGRESSOR = "gradient_boosting_regressor"
    GRADIENT_BOOSTING_CLASSIFIER = "gradient_boosting_classifier"
    MLP_REGRESSOR = "mlp_regressor"
    MLP_CLASSIFIER = "mlp_classifier"
    SVR = "svr"
    SVC = "svc"
    LOGISTIC_REGRESSION = "logistic_regression"
    GAUSSIAN_PROCESS_REGRESSOR = "gaussian_process_regressor"


class TaskType(str, Enum):
    REGRESSION = "regression"
    CLASSIFICATION = "classification"


# ---------------------------------------------------------------------------
# Physical property constraints (eV/atom unless noted)
# ---------------------------------------------------------------------------

# Negative values are allowed — slight DFT noise can push hull energy below zero
ENERGY_ABOVE_HULL_MIN: float = -0.5   # eV/atom
ENERGY_ABOVE_HULL_MAX: float = 10.0   # eV/atom

FORMATION_ENERGY_MIN: float = -10.0   # eV/atom
FORMATION_ENERGY_MAX: float = 5.0     # eV/atom

BAND_GAP_MIN: float = 0.0             # eV
BAND_GAP_MAX: float = 20.0            # eV

# ---------------------------------------------------------------------------
# ML / pipeline defaults
# ---------------------------------------------------------------------------

STABILITY_THRESHOLD_DEFAULT: float = 0.05  # eV/atom — boundary for "stable" label
MIN_TRAINING_SAMPLES: int = 20
MAX_FEATURES_DEFAULT: int = 500
FIXED_RANDOM_SEED: int = 42
