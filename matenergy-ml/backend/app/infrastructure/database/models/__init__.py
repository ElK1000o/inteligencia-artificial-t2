"""
SQLAlchemy ORM models for MatEnergy-ML.

All models are imported here so that:
  - Alembic autogenerate sees every table.
  - Application code can import from a single namespace.
"""
from .base import Base
from .user_models import User, Role, UserRole, RefreshToken, PasswordResetToken
from .dataset_models import (
    DataSource,
    Dataset,
    DatasetColumn,
    DatasetValidationReport,
    RejectedDatasetRow,
    UploadedFile,
)
from .material_models import (
    Material,
    MaterialComposition,
    MaterialProperty,
    MaterialStructure,
)
from .descriptor_models import DescriptorSet, Descriptor, DescriptorVector
from .model_models import (
    ModelVersion,
    ModelArtifact,
    ModelTrainingRun,
    ModelMetric,
    ModelParameter,
)
from .prediction_models import PredictionBatch, Prediction
from .ranking_models import CandidateRanking, CandidateRankingItem
from .audit_models import AuditLog, SecurityEvent, SystemSetting, ApiUsageLog
from .job_models import BackgroundJob

__all__ = [
    "Base",
    # auth / users
    "User",
    "Role",
    "UserRole",
    "RefreshToken",
    "PasswordResetToken",
    # datasets
    "DataSource",
    "Dataset",
    "DatasetColumn",
    "DatasetValidationReport",
    "RejectedDatasetRow",
    "UploadedFile",
    # materials
    "Material",
    "MaterialComposition",
    "MaterialProperty",
    "MaterialStructure",
    # descriptors
    "DescriptorSet",
    "Descriptor",
    "DescriptorVector",
    # models
    "ModelVersion",
    "ModelArtifact",
    "ModelTrainingRun",
    "ModelMetric",
    "ModelParameter",
    # predictions
    "PredictionBatch",
    "Prediction",
    # rankings
    "CandidateRanking",
    "CandidateRankingItem",
    # audit / operations
    "AuditLog",
    "SecurityEvent",
    "SystemSetting",
    "ApiUsageLog",
    # jobs / simulation (Etapa 13)
    "BackgroundJob",
]
