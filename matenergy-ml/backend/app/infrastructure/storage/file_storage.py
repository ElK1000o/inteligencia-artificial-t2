"""
Secure file storage service for MatEnergy-ML.
Manages file paths, hashing, and cleanup.
NEVER uses original filenames as storage paths.
"""
import hashlib
import uuid
from pathlib import Path
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class FileStorageService:
    """
    Manages secure file storage for uploaded CSVs and ML artifacts.
    All files stored with UUID-based names, never original filenames.
    """

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.uploads_dir = self.base_path / "uploads"
        self.artifacts_dir = self.base_path / "artifacts" / "models"
        self.reports_dir = self.base_path / "artifacts" / "reports"
        self._init_dirs()

    def _init_dirs(self) -> None:
        for d in [self.uploads_dir, self.artifacts_dir, self.reports_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def store_upload(self, content: bytes, extension: str = ".csv") -> tuple[str, str, str]:
        """
        Store uploaded file content.
        Returns (stored_filename, stored_path, sha256_hash).
        """
        file_id = str(uuid.uuid4())
        filename = f"{file_id}{extension}"
        path = self.uploads_dir / filename
        path.write_bytes(content)
        sha256 = self._compute_sha256(path)
        logger.info("file_stored", filename=filename, size=len(content), sha256=sha256[:12])
        return filename, str(path), sha256

    def read_upload(self, stored_path: str) -> bytes:
        path = Path(stored_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {stored_path}")
        return path.read_bytes()

    def delete_file(self, stored_path: str) -> bool:
        path = Path(stored_path)
        if path.exists():
            path.unlink()
            return True
        return False

    @staticmethod
    def _compute_sha256(path: Path) -> str:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def compute_sha256_bytes(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()
