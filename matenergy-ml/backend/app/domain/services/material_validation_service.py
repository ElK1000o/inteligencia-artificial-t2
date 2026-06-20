import re
from app.core.constants import (
    ENERGY_ABOVE_HULL_MIN,
    ENERGY_ABOVE_HULL_MAX,
    FORMATION_ENERGY_MIN,
    FORMATION_ENERGY_MAX,
    BAND_GAP_MIN,
    BAND_GAP_MAX,
)
from app.core.exceptions import (
    InvalidChemicalFormulaError,
    UnknownElementError,
    MissingRequiredColumnError,
    InvalidTargetValueError,
)

PROPERTY_RANGES = {
    "energy_above_hull": (ENERGY_ABOVE_HULL_MIN, ENERGY_ABOVE_HULL_MAX),
    "formation_energy_per_atom": (FORMATION_ENERGY_MIN, FORMATION_ENERGY_MAX),
    "band_gap": (BAND_GAP_MIN, BAND_GAP_MAX),
}

REQUIRED_COLUMNS = {"formula"}


class MaterialValidationService:
    """Pure domain service: validates material data without I/O."""

    def validate_formula_string(self, formula: str) -> None:
        if not formula or not formula.strip():
            raise InvalidChemicalFormulaError(
                code="EMPTY_FORMULA",
                message="La fórmula química no puede estar vacía",
                detail="Received empty formula",
                recommended_action="Proporcione una fórmula química válida (p. ej., LiFePO4)",
            )
        # Basic sanity: must start with uppercase letter
        if not re.match(r"^[A-Z]", formula.strip()):
            raise InvalidChemicalFormulaError(
                code="INVALID_FORMULA_FORMAT",
                message="La fórmula química tiene un formato inválido",
                detail=f"Formula '{formula}' does not start with an element symbol",
                recommended_action="Proporcione una fórmula química válida que comience con un símbolo de elemento",
            )

    def validate_property_value(self, property_name: str, value: float) -> None:
        if property_name not in PROPERTY_RANGES:
            return
        lo, hi = PROPERTY_RANGES[property_name]
        if not (lo <= value <= hi):
            raise InvalidTargetValueError(
                code="OUT_OF_RANGE_VALUE",
                message=f"El valor de {property_name} está fuera de los límites físicos",
                detail=f"{property_name}={value} not in [{lo}, {hi}]",
                recommended_action=(
                    f"Verifique las unidades y el valor. Rango esperado: [{lo}, {hi}] para {property_name}"
                ),
            )

    def validate_required_columns(self, available: set[str]) -> None:
        missing = REQUIRED_COLUMNS - available
        if missing:
            raise MissingRequiredColumnError(
                code="MISSING_REQUIRED_COLUMNS",
                message=f"Al dataset le faltan columnas obligatorias: {missing}",
                detail=f"Required: {REQUIRED_COLUMNS}, available: {available}",
                recommended_action="Asegúrese de que el CSV contenga al menos una columna 'formula'",
            )
