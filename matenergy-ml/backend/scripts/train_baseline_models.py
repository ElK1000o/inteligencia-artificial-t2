#!/usr/bin/env python3
"""
Train baseline ML models on the demo dataset.
Usage: python scripts/train_baseline_models.py [dataset_uuid]
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import uuid
from app.infrastructure.database.session import SessionLocal
from app.infrastructure.database.repositories import (
    DatasetRepository,
    DescriptorSetRepository,
    UserRepository,
)
from app.application.use_cases.train_model_use_case import TrainModelUseCase
from app.core.constants import ModelType, TaskType
from app.core.logging_config import configure_logging

configure_logging()

# ---- Models to train ---------------------------------------------------------
# Each tuple: (ModelType, TaskType, target_property)
MODELS_TO_TRAIN = [
    (ModelType.RIDGE_REGRESSION,              TaskType.REGRESSION,      "energy_above_hull"),
    (ModelType.RANDOM_FOREST_REGRESSOR,       TaskType.REGRESSION,      "energy_above_hull"),
    (ModelType.GRADIENT_BOOSTING_REGRESSOR,   TaskType.REGRESSION,      "energy_above_hull"),
    (ModelType.RANDOM_FOREST_REGRESSOR,       TaskType.REGRESSION,      "formation_energy_per_atom"),
    (ModelType.GRADIENT_BOOSTING_REGRESSOR,   TaskType.REGRESSION,      "formation_energy_per_atom"),
    (ModelType.RANDOM_FOREST_CLASSIFIER,      TaskType.CLASSIFICATION,  "is_stable"),
]


def main():
    dataset_id_str = sys.argv[1] if len(sys.argv) > 1 else None

    with SessionLocal() as db:
        # ---- Resolve admin user ------------------------------------------
        user_repo = UserRepository(db)
        admin = user_repo.get_by_email(os.getenv("ADMIN_EMAIL", "admin@matenergy.local"))
        if not admin:
            print("Admin user not found. Run scripts/seed_db.py first.")
            sys.exit(1)

        # ---- Resolve dataset ----------------------------------------------
        ds_repo = DatasetRepository(db)
        if dataset_id_str:
            try:
                dataset = ds_repo.get_by_id(uuid.UUID(dataset_id_str))
            except ValueError:
                print(f"ERROR: Invalid UUID: {dataset_id_str!r}")
                sys.exit(1)
            if not dataset:
                print(f"Dataset {dataset_id_str} not found.")
                sys.exit(1)
        else:
            datasets = ds_repo.get_by_status("valid")
            if not datasets:
                print(
                    "No valid datasets found. "
                    "Run import_demo_data.py first."
                )
                sys.exit(1)
            dataset = datasets[0]

        print(f"Using dataset: {dataset.name} ({dataset.id})")

        # ---- Resolve descriptor set --------------------------------------
        desc_repo = DescriptorSetRepository(db)
        desc_sets = desc_repo.get_all(limit=1)
        if not desc_sets:
            print(
                "No descriptor sets found. "
                "Run generate_descriptors.py first."
            )
            sys.exit(1)
        desc_set = desc_sets[0]
        print(f"Using descriptor set: {desc_set.name} v{desc_set.version} ({desc_set.id})")
        print(f"  n_features: {desc_set.n_features}\n")

        # ---- Train each model --------------------------------------------
        for model_type, task_type, target in MODELS_TO_TRAIN:
            model_name = f"{model_type.value}__{target}"
            print(f"Training: {model_name}")
            try:
                use_case = TrainModelUseCase(db)
                result = use_case.execute(
                    model_type=model_type,
                    task_type=task_type,
                    target_property=target,
                    dataset_id=dataset.id,
                    descriptor_set_id=desc_set.id,
                    user_id=admin.id,
                    name=model_name,
                    description=f"Baseline {model_type.value} for {target} (demo dataset)",
                )
                print(f"  Status       : {result['status']}")
                print(f"  model_version: {result['model_version_id']}")
                print(f"  n_train/test : {result['n_train_samples']} / {result['n_test_samples']}")
                # Print top test metrics
                test_metrics = [m for m in result["metrics"] if m["split"] == "test"]
                for m in test_metrics[:4]:
                    print(f"  {m['metric_name']:20s}: {m['metric_value']:.4f}")
                print()
            except Exception as exc:
                print(f"  FAILED: {exc}\n")


if __name__ == "__main__":
    main()
