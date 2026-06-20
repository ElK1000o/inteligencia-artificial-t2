"""
ExportDatasetUseCase
====================
Reconstructs a safe, sanitised CSV from materials stored in the database.

Security notes
--------------
- CSV formula injection is prevented by quoting every cell with csv.QUOTE_ALL
  and prefixing any cell starting with = + - @ with a single quote (Excel/
  LibreOffice injection defence).
- The exported file is generated in-memory; no temporary files are written.
- The caller receives raw bytes ready to stream as an HTTP response.
"""
from __future__ import annotations

import csv
import io
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging_config import get_logger
from app.infrastructure.database.repositories import (
    DatasetRepository,
    MaterialRepository,
)
from app.infrastructure.database.repositories.material_repository import (
    MaterialPropertyRepository,
)

logger = get_logger(__name__)

# Properties exported by default (in this column order)
_DEFAULT_PROPERTIES = [
    "energy_above_hull",
    "formation_energy_per_atom",
    "band_gap",
    "is_stable",
]

# Characters that can trigger formula injection in spreadsheet apps
_INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _sanitise_cell(value: str) -> str:
    """Prefix potentially dangerous cell values with a single quote."""
    if value and value[0] in _INJECTION_PREFIXES:
        return "'" + value
    return value


class ExportDatasetUseCase:
    """
    Exports dataset materials as a safe, sanitised CSV.

    Args:
        db: Active SQLAlchemy Session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def execute(
        self,
        dataset_id: uuid.UUID,
        properties: list[str] | None = None,
        include_chemsys: bool = True,
    ) -> tuple[bytes, str]:
        """
        Generate a CSV export for *dataset_id*.

        Args:
            dataset_id:     Dataset to export.
            properties:     Property columns to include (default: all standard ones).
            include_chemsys: Whether to include chemsys and nelements columns.

        Returns
        -------
        (csv_bytes, suggested_filename)
        """
        ds_repo = DatasetRepository(self.db)
        dataset = ds_repo.get_by_id(dataset_id)
        if dataset is None:
            raise NotFoundError(
                code="DATASET_NOT_FOUND",
                message=f"No se encontró el dataset {dataset_id}",
                recommended_action="Verifique el dataset_id",
            )

        props_to_export = properties or _DEFAULT_PROPERTIES

        mat_repo = MaterialRepository(self.db)
        prop_repo = MaterialPropertyRepository(self.db)

        materials = mat_repo.get_by_dataset(dataset_id, skip=0, limit=200_000)

        output = io.StringIO()
        header = ["formula"]
        if include_chemsys:
            header += ["chemsys", "nelements"]
        header += props_to_export

        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow(header)

        for mat in materials:
            row: list[str] = [_sanitise_cell(mat.formula or "")]
            if include_chemsys:
                row.append(_sanitise_cell(mat.chemsys or ""))
                row.append(str(mat.nelements or ""))

            for prop_name in props_to_export:
                prop = prop_repo.get_by_material_and_property(mat.id, prop_name)
                if prop is None:
                    row.append("")
                elif prop.value_bool is not None:
                    row.append(str(prop.value_bool))
                elif prop.value_float is not None:
                    row.append(f"{prop.value_float:.6f}")
                elif prop.value_str is not None:
                    row.append(_sanitise_cell(prop.value_str))
                else:
                    row.append("")

            writer.writerow(row)

        content = output.getvalue().encode("utf-8")
        safe_name = f"matenergy_export_{str(dataset_id)[:8]}.csv"

        logger.info(
            "dataset_exported",
            dataset_id=str(dataset_id),
            n_materials=len(materials),
            size_bytes=len(content),
        )

        return content, safe_name
