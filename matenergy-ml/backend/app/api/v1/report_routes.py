"""
Report routes for MatEnergy-ML.

Endpoints:
  POST  /reports/generate              — trigger report generation
  GET   /reports                       — list generated report files
  GET   /reports/{filename}            — download a specific report
  DELETE /reports/{filename}           — delete a report file (ADMIN)

Report types accepted:
  - "ranking"          → CSV, requires resource_id = ranking UUID
  - "model_metrics"    → Markdown, requires resource_id = model_version UUID
  - "dataset_summary"  → Markdown, requires resource_id = dataset UUID
  - "platform_summary" → Markdown, no resource_id required

Security:
  - report filenames are UUIDs+timestamps — no user input reaches the FS path.
  - directory traversal blocked by restricting to reports_dir.
  - generated files are served via safe path resolution only.
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import UserRole
from app.core.logging_config import get_logger
from app.core.security import get_current_user_payload, require_roles
from app.application.use_cases.generate_report_use_case import GenerateReportUseCase
from app.infrastructure.database.session import get_db

router = APIRouter(prefix="/reports", tags=["reports"])
logger = get_logger(__name__)

_REPORTS_DIR = Path(settings.ARTIFACT_STORAGE_PATH) / "reports"
# Allowlist: only alphanumeric, underscores, hyphens and one dot for extension
_SAFE_FILENAME_RE = re.compile(r"^[\w\-]+\.(csv|md|json)$")


class GenerateReportRequest(BaseModel):
    report_type: str
    resource_id: Optional[str] = None


class ReportFileInfo(BaseModel):
    filename: str
    size_bytes: int
    content_type: str


# ---------------------------------------------------------------------------
# Routes — /generate must come before /{filename} to avoid FastAPI treating
# "generate" as a filename parameter.
# ---------------------------------------------------------------------------


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_report(
    body: GenerateReportRequest,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> dict:
    """
    Trigger report generation.

    Body fields:
      - report_type: "ranking" | "model_metrics" | "dataset_summary" | "platform_summary"
      - resource_id: UUID string of the related resource (required for all except platform_summary)
    """
    user_id = uuid.UUID(payload["sub"])
    resource_id: uuid.UUID | None = None
    if body.resource_id:
        try:
            resource_id = uuid.UUID(body.resource_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="resource_id debe ser un UUID válido",
            )

    use_case = GenerateReportUseCase(db)
    try:
        result = use_case.execute(
            report_type=body.report_type,  # type: ignore[arg-type]
            user_id=user_id,
            resource_id=resource_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    logger.info(
        "report_generated_via_api",
        report_type=body.report_type,
        filename=result["filename"],
        user_id=str(user_id),
    )
    return result


@router.get("", response_model=list[ReportFileInfo])
async def list_reports(
    payload: dict = Depends(get_current_user_payload),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> list[ReportFileInfo]:
    """List available report files, ordered by modification time (newest first)."""
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(
        [f for f in _REPORTS_DIR.iterdir() if f.is_file()],
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    result = []
    for f in files[skip: skip + limit]:
        ext = f.suffix.lstrip(".")
        ct = "text/csv" if ext == "csv" else "text/markdown"
        result.append(
            ReportFileInfo(filename=f.name, size_bytes=f.stat().st_size, content_type=ct)
        )
    return result


@router.get("/{filename}")
async def download_report(
    filename: str,
    payload: dict = Depends(get_current_user_payload),
) -> FileResponse:
    """
    Download a specific report file.

    Filename is validated against a strict allowlist pattern to prevent
    path traversal. Only .csv, .md, .json extensions are served.
    """
    if not _SAFE_FILENAME_RE.match(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nombre de archivo de reporte inválido",
        )

    file_path = (_REPORTS_DIR / filename).resolve()

    # Ensure the resolved path is still inside reports_dir
    try:
        file_path.relative_to(_REPORTS_DIR.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nombre de archivo de reporte inválido",
        )

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    ext = file_path.suffix.lstrip(".")
    media_type = "text/csv" if ext == "csv" else "text/markdown; charset=utf-8"
    return FileResponse(path=str(file_path), media_type=media_type, filename=filename)


@router.delete(
    "/{filename}",
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def delete_report(
    filename: str,
    payload: dict = Depends(get_current_user_payload),
) -> dict:
    """Delete a report file (ADMIN only)."""
    if not _SAFE_FILENAME_RE.match(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nombre de archivo de reporte inválido",
        )
    file_path = (_REPORTS_DIR / filename).resolve()
    try:
        file_path.relative_to(_REPORTS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Nombre de archivo de reporte inválido")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    file_path.unlink()
    logger.info("report_deleted", filename=filename, by=payload["sub"])
    return {"message": f"Reporte '{filename}' eliminado"}
