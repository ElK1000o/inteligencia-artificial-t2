"""
Typed exception hierarchy for MatEnergy-ML.

Every exception carries:
  - code             : machine-readable snake_UPPER string, safe to expose to clients
  - message          : human-readable, safe for end-user display (no stack traces / internal paths)
  - detail           : richer internal description intended for logs only
  - recommended_action: plain-English hint that helps clients / operators recover
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class MatEnergyBaseError(Exception):
    """Root exception for all MatEnergy-ML domain errors."""

    def __init__(
        self,
        code: str,
        message: str,
        detail: str = "",
        recommended_action: str = "",
    ) -> None:
        self.code = code
        self.message = message
        self.detail = detail
        self.recommended_action = recommended_action
        super().__init__(message)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"{self.__class__.__name__}("
            f"code={self.code!r}, message={self.message!r}, detail={self.detail!r})"
        )


# ---------------------------------------------------------------------------
# Authentication & authorisation
# ---------------------------------------------------------------------------

class AuthenticationError(MatEnergyBaseError):
    """Base class for all authentication failures."""


class TokenExpiredError(AuthenticationError):
    """JWT token has passed its expiration time."""


class TokenInvalidError(AuthenticationError):
    """JWT token is malformed, has a bad signature, or fails claim validation."""


class TokenRevokedError(AuthenticationError):
    """JWT token jti has been added to the deny-list (e.g. after logout)."""


class TokenTypeMismatchError(AuthenticationError):
    """Token type (access vs. refresh) does not match the expected type for the operation."""


class InvalidCredentialsError(AuthenticationError):
    """Username or password is incorrect."""


class AccountLockedError(AuthenticationError):
    """Account has been temporarily locked due to too many failed login attempts."""


class InsufficientPermissionsError(MatEnergyBaseError):
    """Authenticated user does not hold the required role or permission."""


# ---------------------------------------------------------------------------
# Data / upload exceptions
# ---------------------------------------------------------------------------

class InvalidChemicalFormulaError(MatEnergyBaseError):
    """A chemical formula string could not be parsed or is chemically invalid."""


class UnknownElementError(MatEnergyBaseError):
    """Formula contains an element symbol not present in the periodic table."""


class MissingRequiredColumnError(MatEnergyBaseError):
    """A required column is absent from the uploaded dataset."""


class InvalidTargetValueError(MatEnergyBaseError):
    """A target property value is outside physically plausible bounds."""


class InvalidUnitError(MatEnergyBaseError):
    """A physical unit is unrecognised or incompatible with the target property."""


class DuplicateMaterialError(MatEnergyBaseError):
    """The dataset contains duplicate material entries that violate uniqueness constraints."""


class DatasetHashMismatchError(MatEnergyBaseError):
    """The dataset's computed hash does not match its stored integrity checksum."""


class DatasetValidationError(MatEnergyBaseError):
    """General dataset schema / content validation failure."""


class FileUploadError(MatEnergyBaseError):
    """Base class for file-upload related failures."""


class FileSizeLimitError(FileUploadError):
    """Uploaded file exceeds the configured size limit."""


class InvalidFileExtensionError(FileUploadError):
    """Uploaded file has an extension that is not permitted."""


class PathTraversalError(FileUploadError):
    """Uploaded filename contains path-traversal sequences (e.g. '../')."""


# ---------------------------------------------------------------------------
# Descriptor generation exceptions
# ---------------------------------------------------------------------------

class DescriptorGenerationError(MatEnergyBaseError):
    """Base class for failures during feature/descriptor computation."""


class MissingCompositionError(DescriptorGenerationError):
    """Composition-based descriptors were requested but no composition is available."""


class MissingStructureError(DescriptorGenerationError):
    """Structure-based descriptors were requested but no crystal structure is available."""


class UnsupportedDescriptorError(DescriptorGenerationError):
    """The requested descriptor type is not implemented or not available."""


class DescriptorNaNError(DescriptorGenerationError):
    """Descriptor computation produced NaN values that cannot be handled downstream."""


class DescriptorVersionMismatchError(DescriptorGenerationError):
    """Stored descriptors were generated with a different library version; re-computation required."""


# ---------------------------------------------------------------------------
# Machine-learning pipeline exceptions
# ---------------------------------------------------------------------------

class InsufficientDataError(MatEnergyBaseError):
    """Dataset has fewer samples than the minimum required to train a model."""


class TargetLeakageError(MatEnergyBaseError):
    """A feature in the training set is a direct proxy for the target (data leakage detected)."""


class FeatureMatrixError(MatEnergyBaseError):
    """Feature matrix shape, dtype, or content is incompatible with the selected model."""


class ModelTrainingError(MatEnergyBaseError):
    """An error occurred during model fitting (e.g. convergence failure, NaN loss)."""


class ModelEvaluationError(MatEnergyBaseError):
    """An error occurred while computing evaluation metrics for a trained model."""


class ModelPersistenceError(MatEnergyBaseError):
    """Failed to serialise, write, read, or deserialise a model artifact."""


class ArtifactIntegrityError(MatEnergyBaseError):
    """A stored model artifact's hash does not match its recorded checksum."""


class UnsupportedModelTypeError(MatEnergyBaseError):
    """The requested model type is not implemented in the current pipeline."""


# ---------------------------------------------------------------------------
# Soft warnings — not hard errors but tracked in the same hierarchy
# ---------------------------------------------------------------------------

class OutOfDomainPredictionWarning(MatEnergyBaseError):
    """Prediction was requested for a material outside the training domain (applicability domain check failed)."""


class UncalibratedModelWarning(MatEnergyBaseError):
    """Model confidence scores have not been calibrated; uncertainty estimates may be unreliable."""


# ---------------------------------------------------------------------------
# Resource exceptions
# ---------------------------------------------------------------------------

class NotFoundError(MatEnergyBaseError):
    """Requested resource does not exist in the system."""


class ResourceConflictError(MatEnergyBaseError):
    """Operation conflicts with an existing resource (e.g. duplicate name, concurrent write)."""
