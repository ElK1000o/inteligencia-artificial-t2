"""
VerifyModelArtifactUseCase
==========================
Re-computes the SHA-256 of a stored model artifact and compares it against
the hash recorded in the database.

Call this before loading any artifact to prevent serving tampered models.

    stored_hash != computed_hash  → raises ArtifactIntegrityError
    file missing                  → raises ArtifactIntegrityError
    match                         → returns verification summary
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ArtifactIntegrityError, NotFoundError
from app.core.logging_config import get_logger
from app.infrastructure.database.models.model_models import ModelArtifact

logger = get_logger(__name__)


class VerifyModelArtifactUseCase:
    """
    Verifies artifact file integrity before use.

    Args:
        db: Active SQLAlchemy Session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(self, model_version_id: uuid.UUID) -> dict:
        """
        Locate the artifact for *model_version_id* and verify its hash.

        Returns
        -------
        {
            "artifact_id"    : str,
            "model_version_id": str,
            "file_path"      : str,
            "stored_sha256"  : str,
            "computed_sha256": str,
            "integrity_ok"   : True,
        }

        Raises
        ------
        NotFoundError          – No artifact registered for this model version.
        ArtifactIntegrityError – File missing or hash mismatch detected.
        """
        stmt = (
            select(ModelArtifact)
            .where(ModelArtifact.model_version_id == model_version_id)
            .order_by(ModelArtifact.created_at.desc())
            .limit(1)
        )
        artifact: ModelArtifact | None = self.db.execute(stmt).scalar_one_or_none()

        if artifact is None:
            raise NotFoundError(
                code="ARTIFACT_NOT_FOUND",
                message=f"No se encontró un artefacto para la versión de modelo {model_version_id}",
                detail="The model may not have been trained yet",
                recommended_action="Entrene el modelo antes de intentar la verificación",
            )

        path = Path(artifact.file_path)

        if not path.exists():
            logger.error(
                "artifact_file_missing",
                artifact_id=str(artifact.id),
                file_path=str(path),
            )
            raise ArtifactIntegrityError(
                code="ARTIFACT_FILE_MISSING",
                message="El archivo del artefacto del modelo no se encuentra en el almacenamiento",
                detail=f"Expected: {path}",
                recommended_action="El artefacto pudo haber sido eliminado. Reentrene el modelo.",
            )

        computed = _compute_sha256(path)

        if computed != artifact.sha256_hash:
            logger.error(
                "artifact_hash_mismatch",
                artifact_id=str(artifact.id),
                stored=artifact.sha256_hash[:16],
                computed=computed[:16],
            )
            raise ArtifactIntegrityError(
                code="ARTIFACT_HASH_MISMATCH",
                message="La verificación de integridad del artefacto del modelo falló — el hash no coincide",
                detail=(
                    f"Stored: {artifact.sha256_hash[:16]}… "
                    f"Computed: {computed[:16]}…"
                ),
                recommended_action=(
                    "El archivo del artefacto pudo haber sido alterado o corrompido. "
                    "Reentrene el modelo para generar un artefacto confiable."
                ),
            )

        logger.info(
            "artifact_verified",
            artifact_id=str(artifact.id),
            model_version_id=str(model_version_id),
            sha256=computed[:16],
        )

        return {
            "artifact_id": str(artifact.id),
            "model_version_id": str(model_version_id),
            "file_path": str(path),
            "stored_sha256": artifact.sha256_hash,
            "computed_sha256": computed,
            "integrity_ok": True,
        }


def _compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
