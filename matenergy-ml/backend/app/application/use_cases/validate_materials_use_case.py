"""
ValidateMaterialsUseCase
========================
Runs the full CSV-validation pipeline on a dataset that has already been
uploaded and whose file_path is recorded in the DB.

Steps
-----
1. Load the dataset record from DB.
2. Read raw CSV bytes from disk.
3. Run MaterialCSVLoader.parse_and_validate().
4. Upsert DatasetValidationReport.
5. Persist any newly-found rejected rows.
6. Update dataset status to 'valid' or 'invalid'.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.exceptions import DatasetValidationError, NotFoundError
from app.core.logging_config import get_logger
from app.infrastructure.database.models.dataset_models import (
    Dataset,
    DatasetValidationReport,
    RejectedDatasetRow,
)
from app.infrastructure.database.repositories import DatasetRepository
from app.infrastructure.materials.csv_loader import MaterialCSVLoader

logger = get_logger(__name__)


class ValidateMaterialsUseCase:
    """
    Validates a previously-uploaded CSV dataset.

    Args:
        db: Active SQLAlchemy Session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.loader = MaterialCSVLoader()

    def execute(
        self,
        dataset_id: uuid.UUID,
        user_id: uuid.UUID,
        allow_partial: bool = False,
    ) -> dict:
        """
        Validate the CSV for *dataset_id*.

        Returns
        -------
        {
            "dataset_id"         : str,
            "status"             : "valid" | "invalid" | "partial",
            "total_rows"         : int,
            "valid_rows"         : int,
            "rejected_rows"      : int,
            "validation_errors"  : list[str],
            "warnings"           : list[str],
        }
        """
        t_start = datetime.now(tz=timezone.utc)

        ds_repo = DatasetRepository(self.db)
        dataset: Dataset | None = ds_repo.get_by_id(dataset_id)
        if dataset is None:
            raise NotFoundError(
                code="DATASET_NOT_FOUND",
                message=f"No se encontró el dataset {dataset_id}",
                detail="No dataset record with that UUID",
                recommended_action="Verifique el dataset_id e intente nuevamente",
            )

        if not dataset.file_path or not Path(dataset.file_path).exists():
            raise DatasetValidationError(
                code="FILE_NOT_FOUND",
                message="El archivo CSV de este dataset no se encuentra en el almacenamiento",
                detail=f"Expected path: {dataset.file_path}",
                recommended_action="Vuelva a subir el dataset",
            )

        content = Path(dataset.file_path).read_bytes()
        result = self.loader.parse_and_validate(content, allow_partial=allow_partial)

        # Determine final status
        rejected = result["rejected_count"]
        valid = result["valid_count"]
        total = result["total_rows"]

        if valid == 0:
            new_status = "invalid"
        elif rejected > 0 and allow_partial:
            new_status = "partial"
        elif rejected > 0:
            new_status = "invalid"
        else:
            new_status = "valid"

        # Upsert validation report
        existing_report = (
            self.db.query(DatasetValidationReport)
            .filter(DatasetValidationReport.dataset_id == dataset_id)
            .first()
        )
        t_end = datetime.now(tz=timezone.utc)
        duration = (t_end - t_start).total_seconds()

        if existing_report is None:
            report = DatasetValidationReport(
                id=uuid.uuid4(),
                dataset_id=dataset_id,
                total_rows=total,
                valid_rows=valid,
                rejected_rows=rejected,
                validation_errors={"errors": result["validation_errors"]},
                warnings=result["warnings"],
                validation_rules_applied=[
                    "formula_parseable",
                    "required_columns_present",
                    "physical_range_checks",
                    "duplicate_check",
                    "encoding_valid",
                ],
                validated_at=t_end,
                validated_by=user_id,
                duration_seconds=duration,
            )
            self.db.add(report)
        else:
            existing_report.total_rows = total
            existing_report.valid_rows = valid
            existing_report.rejected_rows = rejected
            existing_report.validation_errors = {"errors": result["validation_errors"]}
            existing_report.warnings = result["warnings"]
            existing_report.validated_at = t_end
            existing_report.validated_by = user_id
            existing_report.duration_seconds = duration

        # Persist rejected rows (append only — no duplicates by row_number)
        existing_row_numbers: set[int] = {
            r.row_number
            for r in self.db.query(RejectedDatasetRow)
            .filter(RejectedDatasetRow.dataset_id == dataset_id)
            .all()
        }

        new_rejected = 0
        for rr in result["rejected_rows"]:
            row_num = rr.get("row_number", 0)
            if row_num not in existing_row_numbers:
                self.db.add(
                    RejectedDatasetRow(
                        id=uuid.uuid4(),
                        dataset_id=dataset_id,
                        row_number=row_num,
                        raw_data=rr.get("raw_data"),
                        rejection_reasons=rr.get("rejection_reasons"),
                    )
                )
                new_rejected += 1

        # Update dataset counts and status
        dataset.row_count = total
        dataset.valid_row_count = valid
        dataset.rejected_row_count = rejected
        dataset.status = new_status

        self.db.commit()

        logger.info(
            "validate_materials_complete",
            dataset_id=str(dataset_id),
            status=new_status,
            total=total,
            valid=valid,
            rejected=rejected,
            duration_s=duration,
        )

        return {
            "dataset_id": str(dataset_id),
            "status": new_status,
            "total_rows": total,
            "valid_rows": valid,
            "rejected_rows": rejected,
            "validation_errors": result["validation_errors"],
            "warnings": result["warnings"],
        }
