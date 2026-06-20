"""Candidate ranking, prediction batch and prediction repositories."""
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.infrastructure.database.repositories.base_repository import BaseRepository
from app.infrastructure.database.models.ranking_models import (
    CandidateRanking,
    CandidateRankingItem,
)
from app.infrastructure.database.models.prediction_models import (
    Prediction,
    PredictionBatch,
)


class CandidateRankingRepository(BaseRepository[CandidateRanking]):
    def __init__(self, db: Session):
        super().__init__(CandidateRanking, db)

    def get_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 20
    ) -> list[CandidateRanking]:
        stmt = (
            select(CandidateRanking)
            .where(CandidateRanking.created_by == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_dataset(self, dataset_id: uuid.UUID) -> list[CandidateRanking]:
        stmt = select(CandidateRanking).where(
            CandidateRanking.dataset_id == dataset_id
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_items(self, ranking_id: uuid.UUID) -> list[CandidateRankingItem]:
        stmt = (
            select(CandidateRankingItem)
            .where(CandidateRankingItem.ranking_id == ranking_id)
            .order_by(CandidateRankingItem.rank_position)
        )
        return list(self.db.execute(stmt).scalars().all())


class CandidateRankingItemRepository(BaseRepository[CandidateRankingItem]):
    def __init__(self, db: Session):
        super().__init__(CandidateRankingItem, db)

    def get_by_ranking(self, ranking_id: uuid.UUID) -> list[CandidateRankingItem]:
        stmt = (
            select(CandidateRankingItem)
            .where(CandidateRankingItem.ranking_id == ranking_id)
            .order_by(CandidateRankingItem.rank_position)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_material(
        self, ranking_id: uuid.UUID, material_id: uuid.UUID
    ) -> Optional[CandidateRankingItem]:
        stmt = select(CandidateRankingItem).where(
            CandidateRankingItem.ranking_id == ranking_id,
            CandidateRankingItem.material_id == material_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_top_n(
        self, ranking_id: uuid.UUID, n: int
    ) -> list[CandidateRankingItem]:
        stmt = (
            select(CandidateRankingItem)
            .where(CandidateRankingItem.ranking_id == ranking_id)
            .order_by(CandidateRankingItem.rank_position)
            .limit(n)
        )
        return list(self.db.execute(stmt).scalars().all())


class PredictionRepository(BaseRepository[Prediction]):
    def __init__(self, db: Session):
        super().__init__(Prediction, db)

    def get_by_batch(self, batch_id: uuid.UUID) -> list[Prediction]:
        stmt = select(Prediction).where(Prediction.batch_id == batch_id)
        return list(self.db.execute(stmt).scalars().all())

    def get_by_material(self, material_id: uuid.UUID) -> list[Prediction]:
        stmt = (
            select(Prediction)
            .where(Prediction.material_id == material_id)
            .order_by(Prediction.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_out_of_domain(self, batch_id: uuid.UUID) -> list[Prediction]:
        stmt = select(Prediction).where(
            Prediction.batch_id == batch_id,
            Prediction.is_out_of_domain == True,  # noqa: E712
        )
        return list(self.db.execute(stmt).scalars().all())


class PredictionBatchRepository(BaseRepository[PredictionBatch]):
    def __init__(self, db: Session):
        super().__init__(PredictionBatch, db)

    def get_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 20
    ) -> list[PredictionBatch]:
        stmt = (
            select(PredictionBatch)
            .where(PredictionBatch.created_by == user_id)
            .offset(skip)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def get_by_status(self, status: str) -> list[PredictionBatch]:
        stmt = select(PredictionBatch).where(PredictionBatch.status == status)
        return list(self.db.execute(stmt).scalars().all())

    def update_status(self, batch: PredictionBatch, status: str) -> None:
        batch.status = status
        self.db.flush()
