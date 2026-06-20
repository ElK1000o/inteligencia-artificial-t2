"""
ImportMaterialDatasetUseCase
============================
Orchestrates the full dataset-ingestion pipeline:

    1. Resolve dataset record from DB.
    2. Read CSV bytes from disk.
    3. Parse + validate every row (csv_loader).
    4. Persist valid materials, compositions, properties and the
       validation report (material_importer).

The dataset record and the file on disk must already exist before this
use case is called.  Typically the upload endpoint creates the Dataset
row and writes the file; then it enqueues or calls this use case.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging_config import get_logger
from app.infrastructure.database.repositories import DatasetRepository
from app.infrastructure.materials.csv_loader import MaterialCSVLoader
from app.infrastructure.materials.material_importer import MaterialImporter

logger = get_logger(__name__)


class ImportMaterialDatasetUseCase:
    """
    Orchestrates file validation, CSV parsing, and DB persistence.

    Args:
        db: Active SQLAlchemy ``Session`` — caller is responsible for its
            lifecycle (open/close, transaction scope).
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.loader = MaterialCSVLoader(max_rows=settings.MAX_ROWS_PER_DATASET)
        self.importer = MaterialImporter()

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def execute(
        self,
        dataset_id: uuid.UUID,
        user_id: uuid.UUID,
        allow_partial: bool = False,
    ) -> dict:
        """
        Load, validate, and import the CSV file linked to *dataset_id*.

        Args:
            dataset_id:    UUID of the Dataset record that holds ``file_path``.
            user_id:       UUID of the requesting user (stored on the
                           validation report).
            allow_partial: When ``True``, import is accepted even if some rows
                           are invalid.  When ``False`` (default), any file with
                           zero valid rows raises ``DatasetValidationError``.

        Returns:
            {
                "dataset_id"          : str,
                "status"              : str,   — "valid" | "invalid"
                "imported"            : int,   — materials persisted
                "rejected"            : int,   — rows rejected during parsing
                "available_properties": list[str],
                "warnings"            : list[str],
                "import_errors"       : list[dict],  — per-formula DB errors
            }

        Raises:
            ValueError:           Dataset record not found.
            FileNotFoundError:    Dataset file does not exist on disk.
            DatasetValidationError: No valid rows and ``allow_partial=False``.
        """
        repo = DatasetRepository(self.db)
        dataset = repo.get_by_id(dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset {dataset_id} not found")

        file_path = Path(dataset.file_path) if dataset.file_path else None
        if file_path is None or not file_path.exists():
            raise FileNotFoundError(
                f"Dataset file not found on disk: {dataset.file_path!r}"
            )

        logger.info(
            "import_dataset_started",
            dataset_id=str(dataset_id),
            file=str(file_path),
            user_id=str(user_id),
        )

        # Mark as "in-progress" so concurrent callers can detect the run.
        dataset.status = "validating"
        self.db.flush()

        content: bytes = file_path.read_bytes()

        # ---- Parse & validate --------------------------------------------
        parsed = self.loader.parse_and_validate(content, allow_partial=allow_partial)

        # ---- Persist -----------------------------------------------------
        result = self.importer.import_from_validated(
            db=self.db,
            dataset=dataset,
            valid_rows=parsed["valid_rows"],
            rejected_rows=parsed["rejected_rows"],
            column_names=parsed["column_names"],
            available_properties=parsed["available_properties"],
            validation_errors=parsed["validation_errors"],
            warnings=parsed["warnings"],
            validated_by=user_id,
        )

        logger.info(
            "import_dataset_completed",
            dataset_id=str(dataset_id),
            status=dataset.status,
            imported=result["imported"],
            rejected=result["rejected"],
        )

        return {
            "dataset_id": str(dataset_id),
            "status": dataset.status,
            "imported": result["imported"],
            "rejected": result["rejected"],
            "available_properties": parsed["available_properties"],
            "warnings": parsed["warnings"],
            "import_errors": result["errors"],
        }
