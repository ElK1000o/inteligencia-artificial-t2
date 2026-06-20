"""Descriptor set, descriptor and descriptor vector repositories."""
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.infrastructure.database.repositories.base_repository import BaseRepository
from app.infrastructure.database.models.descriptor_models import (
    DescriptorSet,
    Descriptor,
    DescriptorVector,
)


class DescriptorSetRepository(BaseRepository[DescriptorSet]):
    def __init__(self, db: Session):
        super().__init__(DescriptorSet, db)

    def get_by_name_version(
        self, name: str, version: str
    ) -> Optional[DescriptorSet]:
        stmt = select(DescriptorSet).where(
            DescriptorSet.name == name,
            DescriptorSet.version == version,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_type(self, descriptor_type: str) -> list[DescriptorSet]:
        stmt = select(DescriptorSet).where(
            DescriptorSet.descriptor_type == descriptor_type
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_user(self, user_id: uuid.UUID) -> list[DescriptorSet]:
        stmt = select(DescriptorSet).where(DescriptorSet.created_by == user_id)
        return list(self.db.execute(stmt).scalars().all())


class DescriptorRepository(BaseRepository[Descriptor]):
    def __init__(self, db: Session):
        super().__init__(Descriptor, db)

    def get_by_set(self, descriptor_set_id: uuid.UUID) -> list[Descriptor]:
        stmt = select(Descriptor).where(
            Descriptor.descriptor_set_id == descriptor_set_id
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_name(
        self, descriptor_set_id: uuid.UUID, name: str
    ) -> Optional[Descriptor]:
        stmt = select(Descriptor).where(
            Descriptor.descriptor_set_id == descriptor_set_id,
            Descriptor.name == name,
        )
        return self.db.execute(stmt).scalar_one_or_none()


class DescriptorVectorRepository(BaseRepository[DescriptorVector]):
    def __init__(self, db: Session):
        super().__init__(DescriptorVector, db)

    def get_for_material(
        self, material_id: uuid.UUID, descriptor_set_id: uuid.UUID
    ) -> Optional[DescriptorVector]:
        stmt = select(DescriptorVector).where(
            DescriptorVector.material_id == material_id,
            DescriptorVector.descriptor_set_id == descriptor_set_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_all_for_dataset(
        self, dataset_id: uuid.UUID, descriptor_set_id: uuid.UUID
    ) -> list[DescriptorVector]:
        from app.infrastructure.database.models.material_models import Material

        stmt = (
            select(DescriptorVector)
            .join(Material, Material.id == DescriptorVector.material_id)
            .where(
                Material.dataset_id == dataset_id,
                DescriptorVector.descriptor_set_id == descriptor_set_id,
            )
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_with_nan(self, descriptor_set_id: uuid.UUID) -> list[DescriptorVector]:
        """Return vectors that contain NaN features for the given descriptor set."""
        stmt = select(DescriptorVector).where(
            DescriptorVector.descriptor_set_id == descriptor_set_id,
            DescriptorVector.has_nan == True,  # noqa: E712
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_all_for_set(self, descriptor_set_id: uuid.UUID) -> list[DescriptorVector]:
        stmt = select(DescriptorVector).where(
            DescriptorVector.descriptor_set_id == descriptor_set_id
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_material_and_set(
        self, material_id: uuid.UUID, descriptor_set_id: uuid.UUID
    ) -> Optional[DescriptorVector]:
        return self.get_for_material(material_id, descriptor_set_id)

    def count_for_dataset(
        self, dataset_id: uuid.UUID, descriptor_set_id: uuid.UUID
    ) -> int:
        from sqlalchemy import func
        from app.infrastructure.database.models.material_models import Material

        stmt = (
            select(func.count())
            .select_from(DescriptorVector)
            .join(Material, Material.id == DescriptorVector.material_id)
            .where(
                Material.dataset_id == dataset_id,
                DescriptorVector.descriptor_set_id == descriptor_set_id,
            )
        )
        return self.db.execute(stmt).scalar_one()
