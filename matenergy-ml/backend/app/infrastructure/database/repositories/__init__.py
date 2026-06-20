"""SQLAlchemy 2.x repository layer for MatEnergy-ML."""
from .base_repository import BaseRepository
from .user_repository import UserRepository, RoleRepository, RefreshTokenRepository
from .dataset_repository import (
    DatasetRepository,
    DatasetValidationReportRepository,
    RejectedRowRepository,
    UploadedFileRepository,
)
from .material_repository import (
    MaterialRepository,
    MaterialCompositionRepository,
    MaterialPropertyRepository,
    MaterialStructureRepository,
)
from .model_repository import (
    ModelVersionRepository,
    ModelArtifactRepository,
    ModelTrainingRunRepository,
    ModelMetricRepository,
    ModelParameterRepository,
)
from .ranking_repository import (
    CandidateRankingRepository,
    CandidateRankingItemRepository,
    PredictionRepository,
    PredictionBatchRepository,
)
from .audit_repository import AuditLogRepository, SecurityEventRepository
from .descriptor_repository import (
    DescriptorSetRepository,
    DescriptorRepository,
    DescriptorVectorRepository,
)

__all__ = [
    # base
    "BaseRepository",
    # users / auth
    "UserRepository",
    "RoleRepository",
    "RefreshTokenRepository",
    # datasets
    "DatasetRepository",
    "DatasetValidationReportRepository",
    "RejectedRowRepository",
    "UploadedFileRepository",
    # materials
    "MaterialRepository",
    "MaterialCompositionRepository",
    "MaterialPropertyRepository",
    "MaterialStructureRepository",
    # ML models
    "ModelVersionRepository",
    "ModelArtifactRepository",
    "ModelTrainingRunRepository",
    "ModelMetricRepository",
    "ModelParameterRepository",
    # rankings & predictions
    "CandidateRankingRepository",
    "CandidateRankingItemRepository",
    "PredictionRepository",
    "PredictionBatchRepository",
    # audit
    "AuditLogRepository",
    "SecurityEventRepository",
    # descriptors
    "DescriptorSetRepository",
    "DescriptorRepository",
    "DescriptorVectorRepository",
]
