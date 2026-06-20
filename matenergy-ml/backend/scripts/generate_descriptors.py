#!/usr/bin/env python3
"""
Generate descriptors for all valid datasets (or a specific one).
Usage: python scripts/generate_descriptors.py [dataset_uuid]
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import uuid
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.repositories import DatasetRepository, UserRepository
from app.application.use_cases.generate_descriptors_use_case import GenerateDescriptorsUseCase
from app.core.logging_config import configure_logging, get_logger

configure_logging()
logger = get_logger(__name__)


def main():
    dataset_id_str = sys.argv[1] if len(sys.argv) > 1 else None

    with SessionLocal() as db:
        user_repo = UserRepository(db)
        admin = user_repo.get_by_email(os.getenv("ADMIN_EMAIL", "admin@matenergy.local"))
        if not admin:
            print("Admin user not found. Run scripts/seed_db.py first.")
            sys.exit(1)

        ds_repo = DatasetRepository(db)
        if dataset_id_str:
            try:
                ds_uuid = uuid.UUID(dataset_id_str)
            except ValueError:
                print(f"ERROR: Invalid UUID: {dataset_id_str!r}")
                sys.exit(1)
            dataset = ds_repo.get_by_id(ds_uuid)
            datasets = [dataset] if dataset else []
            if not datasets:
                print(f"Dataset {dataset_id_str} not found.")
                sys.exit(1)
        else:
            datasets = ds_repo.get_by_status("valid")
            if not datasets:
                print(
                    "No valid datasets found. "
                    "Run import_demo_data.py first, or check that your dataset "
                    "status is 'valid'."
                )
                sys.exit(1)

        for ds in datasets:
            if not ds:
                continue
            print(f"\nGenerating descriptors for: {ds.name} ({ds.id})")
            try:
                use_case = GenerateDescriptorsUseCase(db)
                result = use_case.execute(ds.id, admin.id)
                print(
                    f"  descriptor_set_id : {result['descriptor_set_id']}\n"
                    f"  n_success         : {result['n_success']}\n"
                    f"  n_error           : {result['n_error']}\n"
                    f"  saved (new vectors): {result['saved']}\n"
                    f"  n_features        : {len(result['feature_names'])}"
                )
                if result["errors"]:
                    print(f"  Errors ({len(result['errors'])}):")
                    for err in result["errors"][:5]:
                        print(f"    - {err}")
            except ValueError as exc:
                print(f"  SKIPPED: {exc}")
            except Exception as exc:
                print(f"  FAILED: {exc}")
                logger.exception("descriptor_generation_failed", dataset_id=str(ds.id))


if __name__ == "__main__":
    main()
