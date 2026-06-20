"""
MatEnergy-ML Pydantic v2 schemas.

Re-exports all public schema classes for convenient single-import usage:
    from app.schemas import TokenResponse, DatasetResponse, ...
"""
from app.schemas.common import (
    TimestampMixin,
    PaginatedResponse,
    MessageResponse,
    ErrorResponse,
)
from app.schemas.auth_schemas import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    RegisterRequest,
    UserResponse,
)
from app.schemas.dataset_schemas import (
    DatasetUploadMetadata,
    DatasetResponse,
    DatasetValidationReportResponse,
    RejectedRowResponse,
)
from app.schemas.material_schemas import (
    MaterialResponse,
    MaterialPropertyResponse,
    MaterialDetailResponse,
    MaterialSearchRequest,
)
from app.schemas.model_schemas import (
    TrainModelRequest,
    ModelVersionResponse,
    ModelMetricResponse,
    ModelTrainingRunResponse,
    ModelEvaluationResponse,
)
from app.schemas.prediction_schemas import (
    PredictionRequest,
    PredictionResponse,
    PredictionBatchResponse,
)
from app.schemas.ranking_schemas import (
    RankingWeightsSchema,
    CreateRankingRequest,
    RankingItemResponse,
    CandidateRankingResponse,
    CandidateRankingDetailResponse,
)
from app.schemas.descriptor_schemas import (
    GenerateDescriptorsRequest,
    DescriptorSetResponse,
    DescriptorGenerationResult,
)

__all__ = [
    # common
    "TimestampMixin",
    "PaginatedResponse",
    "MessageResponse",
    "ErrorResponse",
    # auth
    "LoginRequest",
    "TokenResponse",
    "RefreshRequest",
    "RegisterRequest",
    "UserResponse",
    # datasets
    "DatasetUploadMetadata",
    "DatasetResponse",
    "DatasetValidationReportResponse",
    "RejectedRowResponse",
    # materials
    "MaterialResponse",
    "MaterialPropertyResponse",
    "MaterialDetailResponse",
    "MaterialSearchRequest",
    # models
    "TrainModelRequest",
    "ModelVersionResponse",
    "ModelMetricResponse",
    "ModelTrainingRunResponse",
    "ModelEvaluationResponse",
    # predictions
    "PredictionRequest",
    "PredictionResponse",
    "PredictionBatchResponse",
    # rankings
    "RankingWeightsSchema",
    "CreateRankingRequest",
    "RankingItemResponse",
    "CandidateRankingResponse",
    "CandidateRankingDetailResponse",
    # descriptors
    "GenerateDescriptorsRequest",
    "DescriptorSetResponse",
    "DescriptorGenerationResult",
]
