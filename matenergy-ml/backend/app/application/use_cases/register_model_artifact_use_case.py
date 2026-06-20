"""
RegisterModelArtifactUseCase
============================
Records a trained model artifact in the database after the artifact file
has already been written to disk by ModelTrainer.save_artifact().

This use case is the explicit DB-registration step so that:
  - artifact path, SHA-256, size and metadata are persisted atomically,
  - the artifact can later be verified by VerifyModelArtifactUseCase,
  - the artifact registry is the single source of truth for which models
    are safe to load.
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import ArtifactIntegrityError, ModelPersistenceError, NotFoundError
from app.core.logging_config import get_logger
from app.infrastructure.database.models.model_models import ModelArtifact
from app.infrastructure.database.repositories import ModelVersionRepository

logger = get_logger(__name__)


class RegisterModelArtifactUseCase:
    """
    Registers a model artifact file in the database.

    Args:
        db: Active SQLAlchemy Session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(
        self,
        model_version_id: uuid.UUID,
        file_path: str,
        artifact_type: str = "sklearn_joblib",
        serialization_format: str = "joblib",
        python_version: str = "3.12",
        library_versions: dict | None = None,
    ) -> dict:
        """
        Compute SHA-256 of the artifact on disk and persist the record.

        Args:
            model_version_id:      UUID of the parent ModelVersion.
            file_path:             Absolute path to the artifact file on disk.
            artifact_type:         Human-readable artifact type label.
            serialization_format:  Serialization library used (e.g. "joblib").
            python_version:        Python version that created the artifact.
            library_versions:      Dict of key library versions at training time.

        Returns
        -------
        {
            "artifact_id"   : str,
            "model_version_id": str,
            "sha256"        : str,
            "file_path"     : str,
            "file_size_bytes": int,
        }

        Raises
        ------
        NotFoundError          – ModelVersion does not exist.
        ModelPersistenceError  – Artifact file not found on disk.
        """
        # Verify model version exists
        mv_repo = ModelVersionRepository(self.db)
        mv = mv_repo.get_by_id(model_version_id)
        if mv is None:
            raise NotFoundError(
                code="MODEL_VERSION_NOT_FOUND",
                message=f"No se encontró la versión de modelo {model_version_id}",
                detail="Cannot register artifact for a non-existent model version",
                recommended_action="Entrene el modelo primero",
            )

        path = Path(file_path)
        if not path.exists():
            raise ModelPersistenceError(
                code="ARTIFACT_FILE_NOT_FOUND",
                message="El archivo del artefacto no existe en el almacenamiento",
                detail=f"Path: {file_path}",
                recommended_action="Verifique que el archivo se haya guardado correctamente antes de registrarlo",
            )

        # Compute SHA-256
        sha256 = _compute_sha256(path)
        file_size = path.stat().st_size

        artifact = ModelArtifact(
            id=uuid.uuid4(),
            model_version_id=model_version_id,
            file_path=str(path),
            sha256_hash=sha256,
            file_size_bytes=file_size,
            artifact_type=artifact_type,
            serialization_format=serialization_format,
            python_version=python_version,
            library_versions=library_versions or {},
        )
        self.db.add(artifact)
        self.db.commit()

        logger.info(
            "artifact_registered",
            artifact_id=str(artifact.id),
            model_version_id=str(model_version_id),
            sha256=sha256[:16],
            file_size_bytes=file_size,
        )

        return {
            "artifact_id": str(artifact.id),
            "model_version_id": str(model_version_id),
            "sha256": sha256,
            "file_path": str(path),
            "file_size_bytes": file_size,
        }


def _compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
