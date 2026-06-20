"""
GenerateDescriptorsUseCase
==========================
Computes descriptor vectors for every material in a dataset and
persists them to the database.

Pipeline
--------
1. Resolve or create a ``DescriptorSet`` row (name + version are the
   idempotency key).
2. Fetch all ``Material`` rows for the dataset.
3. Delegate batch computation to ``DescriptorPipelineOrchestrator``.
4. Persist ``DescriptorVector`` rows, skipping any that already exist
   (idempotent re-runs).

Caching
-------
Existing vectors are never overwritten.  If you need to regenerate
descriptors (e.g. after a library upgrade) delete the old
``DescriptorVector`` rows first.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.infrastructure.database.models.descriptor_models import (
    DescriptorSet,
    DescriptorVector,
)
from app.infrastructure.database.repositories import (
    DescriptorSetRepository,
    DescriptorVectorRepository,
    MaterialRepository,
)
from app.infrastructure.descriptors.descriptor_pipeline import (
    DescriptorPipelineOrchestrator,
)

logger = get_logger(__name__)


class GenerateDescriptorsUseCase:
    """
    Computes and stores descriptor vectors for a dataset.

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
        dataset_id: uuid.UUID,
        user_id: uuid.UUID,
        include_structural: bool = False,
        name: str = "default",
    ) -> dict:
        """
        Generate descriptors for all materials in *dataset_id*.

        Args:
            dataset_id:         Target dataset.
            user_id:            Requesting user — stored on the
                                ``DescriptorSet`` row if newly created.
            include_structural: Include structure-based features
                                (requires structure data in the DB).
            name:               Human-readable name for the descriptor
                                configuration (e.g. ``"compositional"``).

        Returns:
            {
                "descriptor_set_id": str,
                "n_success"        : int,   — vectors successfully computed
                "n_error"          : int,   — materials that failed
                "errors"           : list[dict],
                "feature_names"    : list[str],
                "saved"            : int,   — new rows persisted (excludes skips)
            }

        Raises:
            ValueError: No materials found for the given dataset.
        """
        orchestrator = DescriptorPipelineOrchestrator(
            include_structural=include_structural
        )
        meta = orchestrator.get_descriptor_set_metadata()

        # ---- Resolve / create DescriptorSet ------------------------------
        ds_repo = DescriptorSetRepository(self.db)
        existing_set = ds_repo.get_by_name_version(name, meta["version"])

        if existing_set is None:
            desc_set = DescriptorSet(
                id=uuid.uuid4(),
                name=name,
                version=meta["version"],
                descriptor_type=meta["descriptor_type"],
                library_versions=meta["library_versions"],
                feature_names=meta["feature_names"],
                n_features=meta["n_features"],
                created_by=user_id,
            )
            self.db.add(desc_set)
            self.db.flush()
            logger.info(
                "descriptor_set_created",
                name=name,
                version=meta["version"],
                n_features=meta["n_features"],
            )
        else:
            desc_set = existing_set
            logger.info(
                "descriptor_set_reused",
                descriptor_set_id=str(desc_set.id),
                name=name,
                version=meta["version"],
            )

        # ---- Fetch materials ----------------------------------------------
        mat_repo = MaterialRepository(self.db)
        materials = mat_repo.get_by_dataset(dataset_id, limit=100_000)

        if not materials:
            raise ValueError(
                f"No materials found for dataset {dataset_id}. "
                "Import the dataset first."
            )

        # ---- Batch computation -------------------------------------------
        batch_input = [
            {
                "formula": m.formula,
                "structure": None,  # structural pipeline falls back to zeros
                "material_id": m.id,
            }
            for m in materials
        ]

        batch_result = orchestrator.compute_batch(batch_input)

        # ---- Persist vectors (skip duplicates) ---------------------------
        vec_repo = DescriptorVectorRepository(self.db)
        saved = 0

        for v in batch_result["vectors"]:
            mat_id: uuid.UUID = v["material_id"]

            if vec_repo.get_for_material(mat_id, desc_set.id) is not None:
                continue  # already computed — idempotent

            vec = DescriptorVector(
                id=uuid.uuid4(),
                material_id=mat_id,
                descriptor_set_id=desc_set.id,
                vector=v["vector"],
                has_nan=bool(v["has_nan"]),
                nan_features=v["nan_features"] or None,
            )
            self.db.add(vec)
            saved += 1

        self.db.commit()

        logger.info(
            "descriptors_generated",
            dataset_id=str(dataset_id),
            descriptor_set_id=str(desc_set.id),
            n_materials=len(materials),
            n_success=batch_result["n_success"],
            n_error=batch_result["n_error"],
            saved=saved,
        )

        return {
            "descriptor_set_id": str(desc_set.id),
            "n_success": batch_result["n_success"],
            "n_error": batch_result["n_error"],
            "errors": batch_result["errors"],
            "feature_names": meta["feature_names"],
            "saved": saved,
        }
