"""Material, composition, property and structure repositories."""
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.infrastructure.database.repositories.base_repository import BaseRepository
from app.infrastructure.database.models.material_models import (
    Material,
    MaterialComposition,
    MaterialProperty,
    MaterialStructure,
)


class MaterialRepository(BaseRepository[Material]):
    def __init__(self, db: Session):
        super().__init__(Material, db)

    def get_by_formula_and_dataset(
        self, formula: str, dataset_id: uuid.UUID
    ) -> Optional[Material]:
        stmt = select(Material).where(
            Material.formula == formula,
            Material.dataset_id == dataset_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_dataset(
        self, dataset_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> list[Material]:
        stmt = (
            select(Material)
            .where(Material.dataset_id == dataset_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_chemsys(
        self, chemsys: str, skip: int = 0, limit: int = 100
    ) -> list[Material]:
        stmt = (
            select(Material)
            .where(Material.chemsys == chemsys)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def search_by_formula(
        self, query: str, skip: int = 0, limit: int = 50
    ) -> list[Material]:
        stmt = (
            select(Material)
            .where(Material.formula.ilike(f"%{query}%"))
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_by_dataset(self, dataset_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Material)
            .where(Material.dataset_id == dataset_id)
        )
        return self.db.execute(stmt).scalar_one()

    def get_element_distribution(self, dataset_id: uuid.UUID) -> list[dict]:
        """Return count of materials containing each element, sorted descending."""
        stmt = (
            select(
                MaterialComposition.element_symbol,
                func.count().label("count"),
            )
            .join(Material, Material.id == MaterialComposition.material_id)
            .where(Material.dataset_id == dataset_id)
            .group_by(MaterialComposition.element_symbol)
            .order_by(func.count().desc())
        )
        rows = self.db.execute(stmt).all()
        return [{"element": r[0], "count": r[1]} for r in rows]


class MaterialCompositionRepository(BaseRepository[MaterialComposition]):
    def __init__(self, db: Session):
        super().__init__(MaterialComposition, db)

    def get_by_material(self, material_id: uuid.UUID) -> list[MaterialComposition]:
        stmt = select(MaterialComposition).where(
            MaterialComposition.material_id == material_id
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_element(
        self, element_symbol: str, skip: int = 0, limit: int = 100
    ) -> list[MaterialComposition]:
        stmt = (
            select(MaterialComposition)
            .where(MaterialComposition.element_symbol == element_symbol)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())


class MaterialPropertyRepository(BaseRepository[MaterialProperty]):
    def __init__(self, db: Session):
        super().__init__(MaterialProperty, db)

    def get_by_material_and_property(
        self, material_id: uuid.UUID, prop_name: str
    ) -> Optional[MaterialProperty]:
        stmt = select(MaterialProperty).where(
            MaterialProperty.material_id == material_id,
            MaterialProperty.property_name == prop_name,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_material(self, material_id: uuid.UUID) -> list[MaterialProperty]:
        stmt = select(MaterialProperty).where(
            MaterialProperty.material_id == material_id
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_property_stats(self, dataset_id: uuid.UUID, prop_name: str) -> dict:
        """Aggregate statistics (mean/min/max/std/count) for a numeric property."""
        stmt = (
            select(
                func.avg(MaterialProperty.value_float).label("mean"),
                func.min(MaterialProperty.value_float).label("min"),
                func.max(MaterialProperty.value_float).label("max"),
                func.stddev(MaterialProperty.value_float).label("std"),
                func.count().label("count"),
            )
            .join(Material, Material.id == MaterialProperty.material_id)
            .where(
                Material.dataset_id == dataset_id,
                MaterialProperty.property_name == prop_name,
                MaterialProperty.value_float.isnot(None),
            )
        )
        row = self.db.execute(stmt).one()
        return {
            "mean": row.mean,
            "min": row.min,
            "max": row.max,
            "std": row.std,
            "count": row.count,
        }


class MaterialStructureRepository(BaseRepository[MaterialStructure]):
    def __init__(self, db: Session):
        super().__init__(MaterialStructure, db)

    def get_by_material(self, material_id: uuid.UUID) -> Optional[MaterialStructure]:
        stmt = select(MaterialStructure).where(
            MaterialStructure.material_id == material_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_crystal_system(
        self, crystal_system: str, skip: int = 0, limit: int = 100
    ) -> list[MaterialStructure]:
        stmt = (
            select(MaterialStructure)
            .where(MaterialStructure.crystal_system == crystal_system)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_space_group(
        self, space_group_number: int, skip: int = 0, limit: int = 100
    ) -> list[MaterialStructure]:
        stmt = (
            select(MaterialStructure)
            .where(MaterialStructure.space_group_number == space_group_number)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
