"""
Candidate ranking routes for MatEnergy-ML.

Endpoints:
  POST  /rankings                     — create a new candidate ranking
  GET   /rankings                     — list rankings
  GET   /rankings/{ranking_id}        — ranking detail with ordered items
  GET   /rankings/{ranking_id}/export — download ranking as CSV
"""
from __future__ import annotations

import csv
import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.security import get_current_user_payload
from app.infrastructure.database.models.ranking_models import (
    CandidateRanking,
    CandidateRankingItem,
)
from app.infrastructure.database.session import get_db
from app.schemas.ranking_schemas import (
    CandidateRankingDetailResponse,
    CandidateRankingResponse,
    CreateRankingRequest,
    RankingItemResponse,
)

router = APIRouter(prefix="/rankings", tags=["rankings"])
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_ranking_or_404(db: Session, ranking_id: uuid.UUID) -> CandidateRanking:
    stmt = select(CandidateRanking).where(CandidateRanking.id == ranking_id)
    ranking = db.execute(stmt).scalar_one_or_none()
    if not ranking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ranking no encontrado"
        )
    return ranking


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=CandidateRankingResponse, status_code=status.HTTP_201_CREATED)
async def create_ranking(
    body: CreateRankingRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> CandidateRankingResponse:
    """
    Create a new candidate ranking.

    The ranking record is persisted with the supplied weights. Actual item
    scoring is handled by a downstream service/worker; this endpoint registers
    the intent and returns the ranking ID for polling.
    """
    user_id = uuid.UUID(payload["sub"])

    weights_dict = body.weights.model_dump()

    ranking = CandidateRanking(
        id=uuid.uuid4(),
        name=body.name,
        application_target=body.application_target,
        dataset_id=body.dataset_id,
        model_version_id=body.model_version_id,
        weights=weights_dict,
        n_candidates=None,
        description=body.description,
        created_by=user_id,
    )
    db.add(ranking)
    db.commit()
    db.refresh(ranking)

    logger.info(
        "ranking_created",
        ranking_id=str(ranking.id),
        application_target=body.application_target,
        user_id=str(user_id),
    )
    return CandidateRankingResponse.model_validate(ranking)


@router.get("", response_model=list[CandidateRankingResponse])
async def list_rankings(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> list[CandidateRankingResponse]:
    """List all candidate rankings, newest first."""
    stmt = (
        select(CandidateRanking)
        .order_by(CandidateRanking.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rankings = list(db.execute(stmt).scalars().all())
    return [CandidateRankingResponse.model_validate(r) for r in rankings]


@router.get("/{ranking_id}", response_model=CandidateRankingDetailResponse)
async def get_ranking(
    ranking_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> CandidateRankingDetailResponse:
    """Retrieve a ranking with its items ordered by rank position."""
    ranking = _get_ranking_or_404(db, ranking_id)

    stmt = (
        select(CandidateRankingItem)
        .where(CandidateRankingItem.ranking_id == ranking_id)
        .order_by(CandidateRankingItem.rank_position)
    )
    items_orm = list(db.execute(stmt).scalars().all())

    items = []
    for item in items_orm:
        items.append(
            RankingItemResponse(
                material_id=item.material_id,
                rank_position=item.rank_position,
                candidate_score=item.candidate_score,
                priority_label=item.priority_label,
                reasoning_summary=item.reasoning_summary,
                stability_score=item.stability_score,
                uncertainty_penalty=item.uncertainty_penalty,
                is_out_of_domain=(item.out_of_domain_penalty is not None and item.out_of_domain_penalty > 0),
            )
        )

    detail = CandidateRankingDetailResponse(
        id=ranking.id,
        name=ranking.name,
        application_target=ranking.application_target,
        n_candidates=ranking.n_candidates,
        created_at=ranking.created_at,
        items=items,
        weights=ranking.weights or {},
    )
    return detail


@router.get("/{ranking_id}/export")
async def export_ranking_csv(
    ranking_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> Response:
    """
    Download the ranking as a CSV file.

    Returns a streaming CSV with columns:
    rank_position, material_id, candidate_score, priority_label, reasoning_summary,
    stability_score, uncertainty_penalty, is_out_of_domain
    """
    ranking = _get_ranking_or_404(db, ranking_id)

    stmt = (
        select(CandidateRankingItem)
        .where(CandidateRankingItem.ranking_id == ranking_id)
        .order_by(CandidateRankingItem.rank_position)
    )
    items = list(db.execute(stmt).scalars().all())

    _INJECTION_CHARS = frozenset("=+-@\t\r")

    def _safe_cell(value: object) -> str:
        """Prefix cells that start with formula-injection characters."""
        s = str(value) if value is not None else ""
        if s and s[0] in _INJECTION_CHARS:
            return "'" + s
        return s

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(
        [
            "rank_position",
            "material_id",
            "candidate_score",
            "priority_label",
            "reasoning_summary",
            "stability_score",
            "uncertainty_penalty",
            "is_out_of_domain",
        ]
    )
    for item in items:
        ood = (item.out_of_domain_penalty is not None and item.out_of_domain_penalty > 0)
        writer.writerow(
            [
                item.rank_position,
                str(item.material_id),
                item.candidate_score,
                _safe_cell(item.priority_label),
                _safe_cell(item.reasoning_summary),
                item.stability_score,
                item.uncertainty_penalty,
                ood,
            ]
        )

    csv_bytes = output.getvalue().encode("utf-8")
    # Sanitize filename: only alphanumeric, underscore, hyphen — no header injection chars
    import re as _re
    safe_name = _re.sub(r"[^\w\-]", "_", ranking.name)[:40]
    filename = f"ranking_{safe_name}_{str(ranking_id)[:8]}.csv"

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""},
    )
