"""
Secure CSV loader for MatEnergy-ML.
Validates structure, encoding, formula, properties.
Never executes CSV content.
"""
import csv
import io
from typing import Optional

from app.core.exceptions import (
    MissingRequiredColumnError, DatasetValidationError,
    InvalidChemicalFormulaError, InvalidTargetValueError
)
from app.core.constants import (
    ENERGY_ABOVE_HULL_MIN, ENERGY_ABOVE_HULL_MAX,
    FORMATION_ENERGY_MIN, FORMATION_ENERGY_MAX,
    BAND_GAP_MIN, BAND_GAP_MAX
)
from app.domain.services.material_validation_service import MaterialValidationService
from app.core.logging_config import get_logger

logger = get_logger(__name__)

SUPPORTED_TARGET_PROPERTIES: dict[str, Optional[tuple[float, float]]] = {
    "energy_above_hull": (ENERGY_ABOVE_HULL_MIN, ENERGY_ABOVE_HULL_MAX),
    "formation_energy_per_atom": (FORMATION_ENERGY_MIN, FORMATION_ENERGY_MAX),
    "band_gap": (BAND_GAP_MIN, BAND_GAP_MAX),
    "is_stable": None,  # binary — validated separately
}

REQUIRED_COLUMNS: set[str] = {"formula"}

# Values accepted as booleans for is_stable / binary columns
_BOOL_TRUTHY = {"True", "true", "1", "yes", "Yes", "YES"}
_BOOL_FALSY = {"False", "false", "0", "no", "No", "NO"}
_BOOL_VALUES = _BOOL_TRUTHY | _BOOL_FALSY


class MaterialCSVLoader:
    """
    Validates and loads material data from CSV content (bytes).
    Never trusts the file — validates every row.
    """

    def __init__(self, max_rows: int = 100_000) -> None:
        self.max_rows = max_rows
        self.validator = MaterialValidationService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse_and_validate(
        self,
        content: bytes,
        allow_partial: bool = False,
    ) -> dict:
        """
        Parse CSV bytes and validate all rows.

        Returns a dict with keys:
            valid_rows          : list[dict]   — rows that passed all checks
            rejected_rows       : list[dict]   — [{row_number, raw_data, rejection_reasons}]
            column_names        : list[str]    — raw header names
            available_properties: list[str]    — subset of SUPPORTED_TARGET_PROPERTIES found
            validation_errors   : list[str]    — file-level errors (non-fatal)
            warnings            : list[str]    — advisory messages
            total_rows          : int
            valid_count         : int
            rejected_count      : int
        """
        text = content.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(text))

        # ---- Header checks -----------------------------------------------
        if not reader.fieldnames:
            raise DatasetValidationError(
                code="EMPTY_CSV",
                message="El archivo CSV no tiene fila de encabezado",
                detail="No fieldnames detected",
                recommended_action=(
                    "Asegúrese de que la primera fila sea un encabezado con nombres de columnas"
                ),
            )

        columns: list[str] = [fn for fn in reader.fieldnames if fn is not None]
        stripped_columns = {c.strip() for c in columns}

        missing = REQUIRED_COLUMNS - stripped_columns
        if missing:
            raise MissingRequiredColumnError(
                code="MISSING_REQUIRED_COLUMNS",
                message=f"Faltan columnas obligatorias: {missing}",
                detail=f"Available: {columns}",
                recommended_action="Asegúrese de que la columna 'formula' esté presente",
            )

        available_properties: list[str] = [
            col.strip()
            for col in columns
            if col.strip() in SUPPORTED_TARGET_PROPERTIES
        ]

        # ---- Row-by-row validation ----------------------------------------
        valid_rows: list[dict] = []
        rejected_rows: list[dict] = []
        warnings: list[str] = []
        validation_errors: list[str] = []
        row_num = 0

        for row in reader:
            row_num += 1
            if row_num > self.max_rows:
                warnings.append(
                    f"Dataset truncado en {self.max_rows} filas — "
                    "las filas restantes no fueron importadas"
                )
                break

            reasons: list[str] = []

            # Normalise: strip key and value whitespace; keep None values as-is
            row_data: dict[str, str | None] = {
                (k.strip() if k else k): (v.strip() if v else v)
                for k, v in row.items()
            }

            # --- Formula validation ---
            formula = (row_data.get("formula") or "").strip()
            if not formula:
                reasons.append("Fórmula vacía")
            else:
                try:
                    self.validator.validate_formula_string(formula)
                except (InvalidChemicalFormulaError, Exception) as exc:
                    reasons.append(str(exc))
                else:
                    # Deep check via pymatgen
                    try:
                        from pymatgen.core import Composition  # lazy import
                        Composition(formula)
                    except Exception as exc:
                        reasons.append(
                            f"Fórmula química inválida '{formula}': {exc}"
                        )

            # --- Property value validation ---
            for prop_name, range_ in SUPPORTED_TARGET_PROPERTIES.items():
                raw = row_data.get(prop_name)
                if raw is None or raw == "":
                    continue  # column absent or empty — allowed

                if range_ is None:
                    # Binary property
                    if raw not in _BOOL_VALUES:
                        reasons.append(
                            f"Valor no booleano para '{prop_name}': {raw!r}"
                        )
                else:
                    try:
                        val = float(raw)
                        lo, hi = range_
                        if not (lo <= val <= hi):
                            reasons.append(
                                f"'{prop_name}'={val} está fuera del rango físico "
                                f"[{lo}, {hi}]"
                            )
                    except ValueError:
                        # Accept bool-like strings only for is_stable; reject for numeric props
                        if raw not in _BOOL_VALUES:
                            reasons.append(
                                f"Valor no numérico para '{prop_name}': {raw!r}"
                            )

            if reasons:
                rejected_rows.append(
                    {
                        "row_number": row_num,
                        "raw_data": row_data,
                        "rejection_reasons": reasons,
                    }
                )
            else:
                valid_rows.append(row_data)

        # ---- Final guard ---------------------------------------------------
        if not valid_rows and not allow_partial:
            raise DatasetValidationError(
                code="NO_VALID_ROWS",
                message="No se encontraron filas válidas en el dataset",
                detail=f"All {row_num} rows were rejected",
                recommended_action=(
                    "Verifique el formato del CSV, la columna 'formula' y los rangos de las propiedades"
                ),
            )

        logger.info(
            "csv_validated",
            total=row_num,
            valid=len(valid_rows),
            rejected=len(rejected_rows),
        )

        return {
            "valid_rows": valid_rows,
            "rejected_rows": rejected_rows,
            "column_names": columns,
            "available_properties": available_properties,
            "validation_errors": validation_errors,
            "warnings": warnings,
            "total_rows": row_num,
            "valid_count": len(valid_rows),
            "rejected_count": len(rejected_rows),
        }
