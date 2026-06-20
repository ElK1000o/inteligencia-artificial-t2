#!/usr/bin/env python3
"""
Script to import the demo dataset into MatEnergy-ML database.
Usage: python scripts/import_demo_data.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import uuid
import hashlib
from pathlib import Path
from datetime import datetime, timezone

from app.infrastructure.database.session import SessionLocal, engine
from app.infrastructure.database.models import Base
from app.infrastructure.database.models.dataset_models import Dataset, UploadedFile
from app.infrastructure.database.repositories import UserRepository, DatasetRepository
from app.application.use_cases.import_dataset_use_case import ImportMaterialDatasetUseCase
from app.core.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)

APP_ROOT = Path(__file__).parent.parent          # /app inside container
DEMO_CSV = APP_ROOT / "data" / "demo" / "demo_materials.csv"
DATA_DIR = APP_ROOT / "artifacts" / "uploads"   # writable named volume


def main():
    Base.metadata.create_all(bind=engine)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as db:
        user_repo = UserRepository(db)
        admin = user_repo.get_by_email(os.getenv("ADMIN_EMAIL", "admin@matenergy.local"))
        if not admin:
            print("ERROR: Admin user not found. Run scripts/seed_db.py first.")
            sys.exit(1)

        if not DEMO_CSV.exists():
            print(f"ERROR: Demo CSV not found at {DEMO_CSV}")
            sys.exit(1)

        content = DEMO_CSV.read_bytes()
        sha256 = hashlib.sha256(content).hexdigest()

        dataset_repo = DatasetRepository(db)
        existing = dataset_repo.get_by_hash(sha256)
        if existing:
            print(f"Demo dataset already imported: {existing.id}")
            return

        # Copy to uploads dir
        stored_name = f"{uuid.uuid4()}.csv"
        stored_path = DATA_DIR / stored_name
        stored_path.write_bytes(content)

        uf = UploadedFile(
            id=uuid.uuid4(),
            original_filename="demo_materials.csv",
            stored_filename=stored_name,
            stored_path=str(stored_path),
            sha256_hash=sha256,
            mime_type="text/csv",
            file_size_bytes=len(content),
            uploaded_by=admin.id,
        )
        db.add(uf)

        ds = Dataset(
            id=uuid.uuid4(),
            name="Demo Li-ion Battery Materials",
            description=(
                "Demonstration dataset with DFT-computed properties for energy storage "
                "materials from Materials Project"
            ),
            sha256_hash=sha256,
            file_path=str(stored_path),
            row_count=0,
            valid_row_count=0,
            rejected_row_count=0,
            column_names=[],
            available_properties=[],
            status="pending",
            imported_by=admin.id,
        )
        db.add(ds)
        db.commit()
        db.refresh(ds)
        print(f"Created dataset record: {ds.id}")

        use_case = ImportMaterialDatasetUseCase(db)
        result = use_case.execute(ds.id, admin.id, allow_partial=True)
        print(f"Import result: {result}")
        print(
            f"Imported {result['imported']} materials, "
            f"rejected {result['rejected']} rows."
        )
        print(f"Available properties: {result['available_properties']}")
        if result.get("warnings"):
            for w in result["warnings"]:
                print(f"  WARNING: {w}")


if __name__ == "__main__":
    main()
