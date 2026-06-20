"""
GenerateReportUseCase
=====================
Orchestrates report generation using ReportGenerator and persists the
report file to the reports artifact directory.

Supported report types:
  - "ranking"          — CSV ranking of candidates
  - "model_metrics"    — Markdown table of model performance metrics
  - "dataset_summary"  — Markdown dataset summary with validation info
  - "platform_summary" — Full platform Markdown summary

The generated file is written to ./artifacts/reports/ and the path is
returned so API routes can stream it.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging_config import get_logger
from app.infrastructure.database.models.material_models import Material
from app.infrastructure.database.models.model_models import (
    ModelMetric,
    ModelTrainingRun,
    ModelVersion,
)
from app.infrastructure.database.models.ranking_models import (
    CandidateRanking,
    CandidateRankingItem,
)
from app.infrastructure.database.repositories import (
    DatasetRepository,
    ModelVersionRepository,
)
from app.infrastructure.reports.report_generator import ReportGenerator

logger = get_logger(__name__)

ReportType = Literal["ranking", "model_metrics", "dataset_summary", "platform_summary"]


class GenerateReportUseCase:
    """
    Generates and saves a report file.

    Args:
        db: Active SQLAlchemy Session.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.generator = ReportGenerator()
        self.reports_dir = Path(settings.ARTIFACT_STORAGE_PATH) / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def execute(
        self,
        report_type: ReportType,
        user_id: uuid.UUID,
        resource_id: uuid.UUID | None = None,
    ) -> dict:
        """
        Generate a report and persist it to disk.

        Args:
            report_type:  One of "ranking", "model_metrics",
                          "dataset_summary", "platform_summary".
            user_id:      Requesting user.
            resource_id:  UUID of the ranking, model version, or dataset
                          (required for type-specific reports).

        Returns
        -------
        {
            "report_type"    : str,
            "file_path"      : str,
            "filename"       : str,
            "content_type"   : str,   — "text/csv" or "text/markdown"
            "size_bytes"     : int,
        }
        """
        now_tag = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")

        if report_type == "ranking":
            content, filename, content_type = self._ranking_report(resource_id, now_tag)
        elif report_type == "model_metrics":
            content, filename, content_type = self._model_metrics_report(resource_id, now_tag)
        elif report_type == "dataset_summary":
            content, filename, content_type = self._dataset_summary_report(resource_id, now_tag)
        elif report_type == "platform_summary":
            content, filename, content_type = self._platform_summary_report(now_tag)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

        file_path = self.reports_dir / filename
        file_path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))

        logger.info(
            "report_generated",
            report_type=report_type,
            filename=filename,
            size_bytes=len(content),
            user_id=str(user_id),
        )

        return {
            "report_type": report_type,
            "file_path": str(file_path),
            "filename": filename,
            "content_type": content_type,
            "size_bytes": len(content),
        }

    # ------------------------------------------------------------------
    # Private builders
    # ------------------------------------------------------------------

    def _ranking_report(
        self, ranking_id: uuid.UUID | None, tag: str
    ) -> tuple[bytes, str, str]:
        if ranking_id is None:
            raise NotFoundError(
                code="RESOURCE_ID_REQUIRED",
                message="Se requiere resource_id (UUID del ranking) para los reportes de ranking",
            )
        ranking: CandidateRanking | None = self.db.get(CandidateRanking, ranking_id)
        if ranking is None:
            raise NotFoundError(
                code="RANKING_NOT_FOUND",
                message=f"No se encontró el ranking {ranking_id}",
            )
        items_stmt = (
            select(CandidateRankingItem)
            .where(CandidateRankingItem.ranking_id == ranking_id)
            .order_by(CandidateRankingItem.rank_position)
        )
        items = [
            {
                "rank_position": i.rank_position,
                "material_id": str(i.material_id),
                "candidate_score": i.candidate_score,
                "priority_label": i.priority_label,
                "reasoning_summary": i.reasoning_summary,
                "stability_score": i.stability_score,
                "uncertainty_penalty": i.uncertainty_penalty,
                "is_out_of_domain": i.is_out_of_domain,
            }
            for i in self.db.execute(items_stmt).scalars().all()
        ]
        # Build formula lookup
        mat_ids = [uuid.UUID(i["material_id"]) for i in items]
        formulas: dict[str, str] = {}
        for mid in mat_ids:
            mat: Material | None = self.db.get(Material, mid)
            if mat:
                formulas[str(mid)] = mat.formula

        content = self.generator.generate_ranking_csv(
            ranking_name=ranking.name,
            items=items,
            material_formulas=formulas,
        )
        filename = f"ranking_{str(ranking_id)[:8]}_{tag}.csv"
        return content, filename, "text/csv"

    def _model_metrics_report(
        self, model_version_id: uuid.UUID | None, tag: str
    ) -> tuple[str, str, str]:
        if model_version_id is None:
            raise NotFoundError(
                code="RESOURCE_ID_REQUIRED",
                message="Se requiere resource_id (UUID de la versión de modelo) para los reportes de métricas",
            )
        mv: ModelVersion | None = self.db.get(ModelVersion, model_version_id)
        if mv is None:
            raise NotFoundError(
                code="MODEL_VERSION_NOT_FOUND",
                message=f"No se encontró la versión de modelo {model_version_id}",
            )
        # Metrics are linked via training runs, not directly to model versions
        run_ids_stmt = select(ModelTrainingRun.id).where(
            ModelTrainingRun.model_version_id == model_version_id
        )
        run_ids = list(self.db.execute(run_ids_stmt).scalars().all())
        metrics: list[dict] = []
        if run_ids:
            metrics_stmt = select(ModelMetric).where(
                ModelMetric.training_run_id.in_(run_ids)
            )
            metrics = [
                {
                    "split": m.split,
                    "metric_name": m.metric_name,
                    "metric_value": m.metric_value,
                }
                for m in self.db.execute(metrics_stmt).scalars().all()
            ]
        content = self.generator.generate_model_metrics_report(mv.name, metrics)
        filename = f"model_metrics_{str(model_version_id)[:8]}_{tag}.md"
        return content, filename, "text/markdown"

    def _dataset_summary_report(
        self, dataset_id: uuid.UUID | None, tag: str
    ) -> tuple[str, str, str]:
        if dataset_id is None:
            raise NotFoundError(
                code="RESOURCE_ID_REQUIRED",
                message="Se requiere resource_id (UUID del dataset) para los reportes de resumen",
            )
        ds_repo = DatasetRepository(self.db)
        dataset = ds_repo.get_by_id(dataset_id)
        if dataset is None:
            raise NotFoundError(
                code="DATASET_NOT_FOUND",
                message=f"No se encontró el dataset {dataset_id}",
            )
        ds_dict = {
            "name": dataset.name,
            "sha256_hash": dataset.sha256_hash,
            "status": dataset.status,
            "row_count": dataset.row_count,
            "valid_row_count": dataset.valid_row_count,
            "rejected_row_count": dataset.rejected_row_count,
            "available_properties": dataset.available_properties or [],
        }
        content = self.generator.generate_dataset_summary(ds_dict)
        filename = f"dataset_summary_{str(dataset_id)[:8]}_{tag}.md"
        return content, filename, "text/markdown"

    def _platform_summary_report(self, tag: str) -> tuple[str, str, str]:
        from sqlalchemy import func
        from app.infrastructure.database.models.dataset_models import Dataset
        from app.infrastructure.database.models.material_models import Material as MatModel
        from app.infrastructure.database.models.model_models import ModelVersion as MV

        n_datasets = self.db.execute(
            select(func.count()).select_from(Dataset)
        ).scalar_one()
        n_materials = self.db.execute(
            select(func.count()).select_from(MatModel)
        ).scalar_one()
        n_models = self.db.execute(
            select(func.count()).select_from(MV)
        ).scalar_one()

        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        content = (
            f"# Resumen de la Plataforma MatEnergy-ML\n"
            f"Generado: {now}\n\n"
            f"| Métrica | Valor |\n"
            f"|---------|-------|\n"
            f"| Datasets | {n_datasets} |\n"
            f"| Materiales | {n_materials} |\n"
            f"| Versiones de modelo | {n_models} |\n\n"
            f"---\nMatEnergy-ML | Cribado de Materiales Energéticos Asistido por IA\n"
        )
        filename = f"platform_summary_{tag}.md"
        return content, filename, "text/markdown"
