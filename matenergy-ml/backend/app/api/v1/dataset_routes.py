"""
Dataset routes for MatEnergy-ML.

Endpoints:
  POST   /datasets/upload                         — upload a CSV file and create Dataset record
  GET    /datasets                                — list all datasets (paginated)
  GET    /datasets/{dataset_id}                   — retrieve a single dataset
  GET    /datasets/{dataset_id}/validation-report — retrieve the validation report
  GET    /datasets/{dataset_id}/rejected-rows     — retrieve rejected rows (paginated)
  DELETE /datasets/{dataset_id}                   — delete dataset (owner or ADMIN)

File validation enforces:
  - Extension: .csv only
  - Content: must decode as valid UTF-8
  - Size: <= settings.MAX_UPLOAD_SIZE_MB
  - MIME content-type: text/csv, text/plain, application/csv, application/octet-stream
  - No empty files
  - Stored path uses UUID-based name — original filename is NEVER used as a path.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
import uuid
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import UserRole
from app.core.logging_config import get_logger
from app.core.security import get_current_user_payload
from app.infrastructure.database.models.dataset_models import (
    Dataset,
    UploadedFile as UploadedFileModel,
)
from app.infrastructure.database.repositories.dataset_repository import (
    DatasetRepository,
    DatasetValidationReportRepository,
    RejectedRowRepository,
)
from app.infrastructure.database.session import get_db
from app.schemas.common import MessageResponse
from app.schemas.dataset_schemas import (
    DatasetResponse,
    DatasetValidationReportResponse,
    RejectedRowResponse,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])
logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {".csv"}
_ALLOWED_MIME_TYPES = frozenset(
    {"text/csv", "application/csv", "text/plain", "application/octet-stream"}
)


def _max_size_bytes() -> int:
    return settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_display_name(original: str) -> str:
    """Sanitize filename for display only — NEVER use as a filesystem path."""
    name = re.sub(r"[^\w\-_. ]", "", original)
    return name[:128] or "upload"


def _compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _validate_upload(file: UploadFile, content: bytes) -> None:
    """Raise HTTPException for any validation failure."""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Solo se aceptan archivos CSV. Extensión recibida: '{suffix}'",
        )

    if len(content) > _max_size_bytes():
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo excede el límite de tamaño de {settings.MAX_UPLOAD_SIZE_MB} MB",
        )

    ct = (file.content_type or "").lower().split(";")[0].strip()
    if ct and ct not in _ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Tipo de contenido del archivo no soportado",
        )

    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser texto/CSV codificado en UTF-8",
        )

    if len(content.strip()) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo subido está vacío",
        )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/upload", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    allow_partial_import: bool = Form(False),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> DatasetResponse:
    """
    Upload a CSV dataset.

    The uploaded file is stored under a UUID-based filename.
    The original filename is recorded for display purposes only and is never
    used to construct filesystem paths.
    """
    content = await file.read()
    _validate_upload(file, content)

    sha256 = _compute_sha256(content)
    dataset_repo = DatasetRepository(db)

    # Reject duplicate content
    existing = dataset_repo.get_by_hash(sha256)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un dataset con contenido idéntico",
        )

    # Build storage path using UUID — never use original filename
    file_uuid = uuid.uuid4()
    stored_name = f"{file_uuid}.csv"
    storage_dir = Path(settings.DATA_STORAGE_PATH) / "uploads"
    storage_dir.mkdir(parents=True, exist_ok=True)
    stored_path = storage_dir / stored_name
    stored_path.write_bytes(content)

    user_id = uuid.UUID(payload["sub"])

    # Count data rows (subtract header)
    decoded = content.decode("utf-8")
    reader = csv.reader(io.StringIO(decoded))
    rows = list(reader)
    header = rows[0] if rows else []
    row_count = max(0, len(rows) - 1)

    # Persist UploadedFile record
    uf = UploadedFileModel(
        id=uuid.uuid4(),
        original_filename=_safe_display_name(file.filename or "upload.csv"),
        stored_filename=stored_name,
        stored_path=str(stored_path),
        sha256_hash=sha256,
        mime_type="text/csv",
        file_size_bytes=len(content),
        uploaded_by=user_id,
    )
    db.add(uf)

    # Persist Dataset record
    ds = Dataset(
        id=uuid.uuid4(),
        name=name,
        description=description,
        sha256_hash=sha256,
        file_path=str(stored_path),
        row_count=row_count,
        valid_row_count=0,
        rejected_row_count=0,
        column_names=header,
        available_properties=[],
        status="pending",
        imported_by=user_id,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

    logger.info(
        "dataset_uploaded",
        dataset_id=str(ds.id),
        sha256_prefix=sha256[:12],
        rows=row_count,
        user_id=str(user_id),
    )
    return DatasetResponse.model_validate(ds)


@router.get("", response_model=list[DatasetResponse])
async def list_datasets(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> list[DatasetResponse]:
    """List all datasets ordered by creation time (newest first)."""
    repo = DatasetRepository(db)
    items = repo.get_all(skip=skip, limit=limit)
    return [DatasetResponse.model_validate(d) for d in items]


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> DatasetResponse:
    """Retrieve a single dataset by ID."""
    repo = DatasetRepository(db)
    ds = repo.get_by_id(dataset_id)
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset no encontrado")
    return DatasetResponse.model_validate(ds)


@router.get("/{dataset_id}/validation-report", response_model=DatasetValidationReportResponse)
async def get_validation_report(
    dataset_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> DatasetValidationReportResponse:
    """Retrieve the validation report for a dataset."""
    # Ensure dataset exists
    dataset_repo = DatasetRepository(db)
    if not dataset_repo.get_by_id(dataset_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset no encontrado")

    report_repo = DatasetValidationReportRepository(db)
    report = report_repo.get_by_dataset(dataset_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El reporte de validación aún no está disponible para este dataset",
        )
    return DatasetValidationReportResponse.model_validate(report)


@router.get("/{dataset_id}/rejected-rows", response_model=list[RejectedRowResponse])
async def get_rejected_rows(
    dataset_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> list[RejectedRowResponse]:
    """List rows that were rejected during validation (paginated)."""
    dataset_repo = DatasetRepository(db)
    if not dataset_repo.get_by_id(dataset_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset no encontrado")

    row_repo = RejectedRowRepository(db)
    rows = row_repo.get_by_dataset(dataset_id, skip=skip, limit=limit)
    return [RejectedRowResponse.model_validate(r) for r in rows]


@router.delete("/{dataset_id}", response_model=MessageResponse)
async def delete_dataset(
    dataset_id: uuid.UUID,
    payload: dict = Depends(get_current_user_payload),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """
    Delete a dataset record.

    Only the dataset owner or an ADMIN-role user may delete a dataset.
    """
    repo = DatasetRepository(db)
    ds = repo.get_by_id(dataset_id)
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset no encontrado")

    caller_id = payload.get("sub")
    caller_role = payload.get("role", "")
    is_owner = ds.imported_by and str(ds.imported_by) == caller_id
    is_admin = caller_role == UserRole.ADMIN.value

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para eliminar este dataset",
        )

    # Remove stored file if it exists
    if ds.file_path:
        stored = Path(ds.file_path)
        if stored.exists():
            stored.unlink(missing_ok=True)

    repo.delete(ds)
    db.commit()

    logger.info("dataset_deleted", dataset_id=str(dataset_id), deleted_by=caller_id)
    return MessageResponse(message="Dataset eliminado correctamente")
