from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import Optional


@dataclass
class MaterialCompositionItem:
    element_symbol: str
    fraction: float  # 0.0 - 1.0


@dataclass
class MaterialProperty:
    property_name: str
    value_float: Optional[float] = None
    value_str: Optional[str] = None
    value_bool: Optional[bool] = None
    unit: Optional[str] = None
    is_dft_computed: bool = True
    uncertainty: Optional[float] = None


@dataclass
class Material:
    id: UUID
    formula: str
    reduced_formula: str
    chemsys: str  # sorted elements, e.g. "Fe-Li-O"
    dataset_id: UUID
    nelements: int
    elements: list[str]
    composition: list[MaterialCompositionItem] = field(default_factory=list)
    properties: list[MaterialProperty] = field(default_factory=list)
    source_material_id: Optional[str] = None
    created_at: Optional[datetime] = None

    def get_property(self, name: str) -> Optional[MaterialProperty]:
        return next((p for p in self.properties if p.property_name == name), None)

    def has_element(self, symbol: str) -> bool:
        return symbol in self.elements

    def fraction_of(self, symbol: str) -> float:
        item = next((c for c in self.composition if c.element_symbol == symbol), None)
        return item.fraction if item else 0.0
