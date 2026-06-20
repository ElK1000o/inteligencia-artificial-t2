"""
Imports validated material rows into the database.
Links formulas to pymatgen-parsed composition data.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from app.infrastructure.database.models.material_models import (
    Material,
    MaterialComposition,
    MaterialProperty,
)
from app.infrastructure.database.models.dataset_models import (
    Dataset,
    DatasetValidationReport,
    RejectedDatasetRow,
)
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Properties that may be stored per-material from a CSV row.
# Numeric-first: try float(value) → fallback to bool → fallback to str.
_PROP_FIELDS: tuple[str, ...] = (
    "energy_above_hull",
    "formation_energy_per_atom",
    "band_gap",
    "is_stable",
    "average_voltage",
    "theoretical_capacity",
)

_BOOL_TRUTHY = {"True", "true", "1", "yes", "Yes"}
_BOOL_FALSY = {"False", "false", "0", "no", "No"}


def _parse_property_value(
    raw: str,
) -> tuple[Optional[float], Optional[bool], Optional[str]]:
    """
    Attempt to parse *raw* as float, then bool, then str.
    Returns (value_float, value_bool, value_str).
    Exactly one of the three will be non-None.
    """
    try:
        return float(raw), None, None
    except (ValueError, TypeError):
        pass
    if raw in _BOOL_TRUTHY:
        return None, True, None
    if raw in _BOOL_FALSY:
        return None, False, None
    return None, None, str(raw)


class MaterialImporter:
    """Persists validated material rows to the database."""

    def import_from_validated(
        self,
        db: Session,
        dataset: Dataset,
        valid_rows: list[dict],
        rejected_rows: list[dict],
        column_names: list[str],
        available_properties: list[str],
        validation_errors: list[str],
        warnings: list[str],
        validated_by: Optional[uuid.UUID] = None,
    ) -> dict:
        """
        Persist materials, compositions, and properties to the DB.

        Also saves rejected-row records and a validation report, and
        updates the Dataset stats.

        Returns:
            {
                "imported": int,  — successfully persisted Material rows
                "rejected": int,  — rows that were already invalid (pre-validated)
                "errors":   list  — per-formula import errors
            }
        """
        from pymatgen.core import Composition  # lazy import — heavy dependency

        imported = 0
        errors: list[dict] = []

        for row in valid_rows:
            formula = (row.get("formula") or "").strip()
            if not formula:
                errors.append({"formula": formula, "error": "Empty formula after strip"})
                continue

            try:
                comp = Composition(formula)
            except Exception as exc:
                errors.append({"formula": formula, "error": str(exc)})
                continue

            # Use a SAVEPOINT so a per-row failure only rolls back that row's
            # objects while the outer transaction (and all previous rows)
            # remain intact.  ``begin_nested()`` is supported by SQLAlchemy 2.x
            # with any DBAPI that supports SAVEPOINTs (psycopg2, asyncpg, etc.).
            try:
                with db.begin_nested():
                    elements: list[str] = [str(el) for el in comp.elements]
                    chemsys: str = "-".join(sorted(elements))
                    nelements: int = len(elements)
                    reduced: str = str(comp.reduced_formula)

                    mat = Material(
                        id=uuid.uuid4(),
                        formula=formula,
                        reduced_formula=reduced,
                        chemsys=chemsys,
                        dataset_id=dataset.id,
                        nelements=nelements,
                        elements=elements,
                    )
                    db.add(mat)
                    db.flush()  # allocate PK inside the savepoint

                    # --- Compositions ---
                    for el in comp.elements:
                        frac = comp.get_atomic_fraction(el)
                        db.add(
                            MaterialComposition(
                                id=uuid.uuid4(),
                                material_id=mat.id,
                                element_symbol=str(el),
                                fraction=float(frac),
                            )
                        )

                    # --- Properties ---
                    for prop_name in _PROP_FIELDS:
                        raw_val = row.get(prop_name)
                        if raw_val is None or raw_val == "":
                            continue  # property absent for this row

                        value_float, value_bool, value_str = _parse_property_value(
                            raw_val
                        )
                        db.add(
                            MaterialProperty(
                                id=uuid.uuid4(),
                                material_id=mat.id,
                                property_name=prop_name,
                                value_float=value_float,
                                value_bool=value_bool,
                                value_str=value_str,
                                is_dft_computed=True,
                            )
                        )

                # Savepoint committed implicitly on __exit__ without exception
                imported += 1

            except Exception as exc:
                # Savepoint was rolled back automatically; outer tx is intact.
                errors.append({"formula": formula, "error": str(exc)})
                continue

        # --- Rejected rows ---
        for rej in rejected_rows:
            db.add(
                RejectedDatasetRow(
                    id=uuid.uuid4(),
                    dataset_id=dataset.id,
                    row_number=rej.get("row_number", 0),
                    raw_data=rej.get("raw_data"),
                    rejection_reasons=rej.get("rejection_reasons"),
                )
            )

        # --- Validation report ---
        db.add(
            DatasetValidationReport(
                id=uuid.uuid4(),
                dataset_id=dataset.id,
                total_rows=len(valid_rows) + len(rejected_rows),
                valid_rows=len(valid_rows),
                rejected_rows=len(rejected_rows),
                validation_errors={"errors": validation_errors},
                warnings=warnings,
                validation_rules_applied=[
                    "formula_parse",
                    "property_range",
                    "required_columns",
                ],
                validated_at=datetime.now(tz=timezone.utc),
                validated_by=validated_by,
            )
        )

        # --- Update dataset stats ---
        dataset.valid_row_count = imported
        dataset.rejected_row_count = len(rejected_rows)
        dataset.status = "valid" if imported > 0 else "invalid"
        dataset.available_properties = available_properties
        dataset.column_names = column_names

        db.commit()

        logger.info(
            "materials_imported",
            dataset_id=str(dataset.id),
            imported=imported,
            rejected=len(rejected_rows),
            errors=len(errors),
        )

        return {
            "imported": imported,
            "rejected": len(rejected_rows),
            "errors": errors,
        }
