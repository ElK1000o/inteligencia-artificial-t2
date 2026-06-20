"""Initial schema — all tables

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # 1. roles                                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------ #
    # 2. users                                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("username", sa.String(150), nullable=False, unique=True),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_superuser", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("failed_login_attempts", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])

    # ------------------------------------------------------------------ #
    # 3. user_roles                                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assigned_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "assigned_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    # ------------------------------------------------------------------ #
    # 4. refresh_tokens                                                    #
    # ------------------------------------------------------------------ #
    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("jti", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
    )
    op.create_index("ix_refresh_tokens_jti", "refresh_tokens", ["jti"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    # ------------------------------------------------------------------ #
    # 5. password_reset_tokens                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------ #
    # 6. data_sources                                                      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("base_url", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("requires_api_key", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------ #
    # 7. datasets                                                          #
    # ------------------------------------------------------------------ #
    op.create_table(
        "datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("data_sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("file_path", sa.Text, nullable=True),
        sa.Column("sha256_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("valid_row_count", sa.Integer, nullable=True),
        sa.Column("rejected_row_count", sa.Integer, nullable=True),
        sa.Column("column_names", postgresql.JSONB, nullable=True),
        sa.Column("available_properties", postgresql.JSONB, nullable=True),
        sa.Column(
            "imported_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
    )
    op.create_index("ix_datasets_sha256_hash", "datasets", ["sha256_hash"])
    op.create_index("ix_datasets_imported_by", "datasets", ["imported_by"])
    op.create_index("ix_datasets_status", "datasets", ["status"])

    # ------------------------------------------------------------------ #
    # 8. dataset_columns                                                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        "dataset_columns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("column_name", sa.String(255), nullable=False),
        sa.Column("data_type", sa.String(50), nullable=True),
        sa.Column("is_required", sa.Boolean, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("min_value", sa.Float, nullable=True),
        sa.Column("max_value", sa.Float, nullable=True),
        sa.Column("null_count", sa.Integer, nullable=True),
        sa.Column("unique_count", sa.Integer, nullable=True),
    )

    # ------------------------------------------------------------------ #
    # 9. dataset_validation_reports                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "dataset_validation_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("total_rows", sa.Integer, nullable=True),
        sa.Column("valid_rows", sa.Integer, nullable=True),
        sa.Column("rejected_rows", sa.Integer, nullable=True),
        sa.Column("validation_errors", postgresql.JSONB, nullable=True),
        sa.Column("warnings", postgresql.JSONB, nullable=True),
        sa.Column("validation_rules_applied", postgresql.JSONB, nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "validated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("duration_seconds", sa.Float, nullable=True),
    )

    # ------------------------------------------------------------------ #
    # 10. rejected_dataset_rows                                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "rejected_dataset_rows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("row_number", sa.Integer, nullable=False),
        sa.Column("raw_data", postgresql.JSONB, nullable=True),
        sa.Column("rejection_reasons", postgresql.JSONB, nullable=True),
        sa.Column(
            "rejected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------ #
    # 11. uploaded_files                                                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        "uploaded_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("original_filename", sa.Text, nullable=True),
        sa.Column("stored_filename", sa.Text, nullable=False, unique=True),
        sa.Column("stored_path", sa.Text, nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=True),
        sa.Column("mime_type", sa.String(127), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column(
            "uploaded_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_processed", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )

    # ------------------------------------------------------------------ #
    # 12. materials                                                        #
    # ------------------------------------------------------------------ #
    op.create_table(
        "materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("formula", sa.String(255), nullable=False),
        sa.Column("reduced_formula", sa.String(255), nullable=True),
        sa.Column("chemsys", sa.String(255), nullable=True),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_material_id", sa.String(255), nullable=True),
        sa.Column("nelements", sa.Integer, nullable=True),
        sa.Column("elements", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("formula", "dataset_id", name="uq_materials_formula_dataset"),
        sa.CheckConstraint("nelements >= 1", name="ck_materials_nelements_positive"),
    )
    op.create_index("ix_materials_formula", "materials", ["formula"])
    op.create_index("ix_materials_reduced_formula", "materials", ["reduced_formula"])
    op.create_index("ix_materials_chemsys", "materials", ["chemsys"])

    # ------------------------------------------------------------------ #
    # 13. material_compositions                                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "material_compositions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("materials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("element_symbol", sa.String(3), nullable=False),
        sa.Column("fraction", sa.Float, nullable=False),
        sa.UniqueConstraint(
            "material_id", "element_symbol",
            name="uq_material_compositions_material_element",
        ),
        sa.CheckConstraint(
            "fraction >= 0 AND fraction <= 1",
            name="ck_material_compositions_fraction_range",
        ),
    )

    # ------------------------------------------------------------------ #
    # 14. material_properties                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "material_properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("materials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("property_name", sa.String(255), nullable=False),
        sa.Column("value_float", sa.Float, nullable=True),
        sa.Column("value_str", sa.String(1024), nullable=True),
        sa.Column("value_bool", sa.Boolean, nullable=True),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("is_dft_computed", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("uncertainty", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "material_id", "property_name",
            name="uq_material_properties_material_property",
        ),
        sa.CheckConstraint(
            "value_float IS NOT NULL OR value_str IS NOT NULL OR value_bool IS NOT NULL",
            name="ck_material_properties_one_value_not_null",
        ),
    )
    op.create_index("ix_material_properties_material_id", "material_properties", ["material_id"])
    op.create_index("ix_material_properties_property_name", "material_properties", ["property_name"])

    # ------------------------------------------------------------------ #
    # 15. material_structures                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "material_structures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("materials.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("lattice_a", sa.Float, nullable=True),
        sa.Column("lattice_b", sa.Float, nullable=True),
        sa.Column("lattice_c", sa.Float, nullable=True),
        sa.Column("alpha", sa.Float, nullable=True),
        sa.Column("beta", sa.Float, nullable=True),
        sa.Column("gamma", sa.Float, nullable=True),
        sa.Column("volume", sa.Float, nullable=True),
        sa.Column("density", sa.Float, nullable=True),
        sa.Column("space_group_number", sa.Integer, nullable=True),
        sa.Column("space_group_symbol", sa.String(20), nullable=True),
        sa.Column("crystal_system", sa.String(50), nullable=True),
        sa.Column("structure_json", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------ #
    # 16. descriptor_sets                                                  #
    # ------------------------------------------------------------------ #
    op.create_table(
        "descriptor_sets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("descriptor_type", sa.String(50), nullable=True),
        sa.Column("library_versions", postgresql.JSONB, nullable=True),
        sa.Column("feature_names", postgresql.JSONB, nullable=True),
        sa.Column("n_features", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("name", "version", name="uq_descriptor_sets_name_version"),
    )

    # ------------------------------------------------------------------ #
    # 17. descriptors                                                      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "descriptors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "descriptor_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("descriptor_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("dtype", sa.String(50), nullable=True),
        sa.Column("is_compositional", sa.Boolean, nullable=True),
        sa.Column("is_structural", sa.Boolean, nullable=True),
        sa.UniqueConstraint(
            "descriptor_set_id", "name",
            name="uq_descriptors_set_name",
        ),
    )

    # ------------------------------------------------------------------ #
    # 18. descriptor_vectors                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "descriptor_vectors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("materials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "descriptor_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("descriptor_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("vector", postgresql.JSONB, nullable=False),
        sa.Column("has_nan", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("nan_features", postgresql.JSONB, nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "material_id", "descriptor_set_id",
            name="uq_descriptor_vectors_material_set",
        ),
    )

    # ------------------------------------------------------------------ #
    # 19. model_versions                                                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        "model_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("model_type", sa.String(100), nullable=False),
        sa.Column("task_type", sa.String(30), nullable=True),
        sa.Column("target_property", sa.String(255), nullable=False),
        sa.Column(
            "descriptor_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("descriptor_sets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("version_tag", sa.String(50), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_model_versions_type_property_active",
        "model_versions",
        ["model_type", "target_property", "is_active"],
    )

    # ------------------------------------------------------------------ #
    # 20. model_artifacts                                                  #
    # ------------------------------------------------------------------ #
    op.create_table(
        "model_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("artifact_type", sa.String(50), nullable=True),
        sa.Column("serialization_format", sa.String(50), nullable=True),
        sa.Column("python_version", sa.String(20), nullable=True),
        sa.Column("library_versions", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------ #
    # 21. model_training_runs                                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "model_training_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "descriptor_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("descriptor_sets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'running'")),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
        sa.Column("n_train_samples", sa.Integer, nullable=True),
        sa.Column("n_test_samples", sa.Integer, nullable=True),
        sa.Column("n_features", sa.Integer, nullable=True),
        sa.Column("random_seed", sa.Integer, nullable=True),
        sa.Column("hyperparameters", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "triggered_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ------------------------------------------------------------------ #
    # 22. model_metrics                                                    #
    # ------------------------------------------------------------------ #
    op.create_table(
        "model_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "training_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_training_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("split", sa.String(20), nullable=False),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("metric_value", sa.Float, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "training_run_id", "split", "metric_name",
            name="uq_model_metrics_run_split_metric",
        ),
    )

    # ------------------------------------------------------------------ #
    # 23. model_parameters                                                 #
    # ------------------------------------------------------------------ #
    op.create_table(
        "model_parameters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("parameter_name", sa.String(255), nullable=False),
        sa.Column("parameter_value", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------ #
    # 24. prediction_batches                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "prediction_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("n_materials", sa.Integer, nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ------------------------------------------------------------------ #
    # 25. predictions                                                      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("prediction_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("materials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("predicted_value", sa.Float, nullable=True),
        sa.Column("predicted_class", sa.String(255), nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("is_out_of_domain", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("out_of_domain_reason", sa.Text, nullable=True),
        sa.Column("is_calibrated", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "predicted_value IS NOT NULL OR predicted_class IS NOT NULL",
            name="ck_predictions_one_output_not_null",
        ),
    )
    op.create_index("ix_predictions_batch_id", "predictions", ["batch_id"])
    op.create_index("ix_predictions_material_id", "predictions", ["material_id"])

    # ------------------------------------------------------------------ #
    # 26. candidate_rankings                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "candidate_rankings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("application_target", sa.String(255), nullable=False),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "model_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("weights", postgresql.JSONB, nullable=True),
        sa.Column("n_candidates", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("description", sa.Text, nullable=True),
    )

    # ------------------------------------------------------------------ #
    # 27. candidate_ranking_items                                          #
    # ------------------------------------------------------------------ #
    op.create_table(
        "candidate_ranking_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ranking_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("candidate_rankings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "material_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("materials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rank_position", sa.Integer, nullable=False),
        sa.Column("candidate_score", sa.Float, nullable=False),
        sa.Column("priority_label", sa.String(50), nullable=False),
        sa.Column("stability_score", sa.Float, nullable=True),
        sa.Column("target_property_score", sa.Float, nullable=True),
        sa.Column("energy_relevance_score", sa.Float, nullable=True),
        sa.Column("abundance_score", sa.Float, nullable=True),
        sa.Column("toxicity_penalty", sa.Float, nullable=True),
        sa.Column("uncertainty_penalty", sa.Float, nullable=True),
        sa.Column("out_of_domain_penalty", sa.Float, nullable=True),
        sa.Column("reasoning_summary", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "ranking_id", "material_id",
            name="uq_candidate_ranking_items_ranking_material",
        ),
        sa.UniqueConstraint(
            "ranking_id", "rank_position",
            name="uq_candidate_ranking_items_ranking_position",
        ),
        sa.CheckConstraint(
            "candidate_score >= 0 AND candidate_score <= 1",
            name="ck_candidate_ranking_items_score_range",
        ),
    )
    op.create_index(
        "ix_candidate_ranking_items_ranking_id",
        "candidate_ranking_items",
        ["ranking_id"],
    )

    # ------------------------------------------------------------------ #
    # 28. audit_logs                                                       #
    # ------------------------------------------------------------------ #
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("request_method", sa.String(10), nullable=True),
        sa.Column("request_path", sa.Text, nullable=True),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("duration_ms", sa.Float, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_user_created", "audit_logs", ["user_id", "created_at"])
    op.create_index(
        "ix_audit_logs_resource_type_id",
        "audit_logs",
        ["resource_type", "resource_id"],
    )

    # ------------------------------------------------------------------ #
    # 29. security_events                                                  #
    # ------------------------------------------------------------------ #
    op.create_table(
        "security_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column("resolved", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_security_events_event_type", "security_events", ["event_type"])
    op.create_index("ix_security_events_created_at", "security_events", ["created_at"])

    # ------------------------------------------------------------------ #
    # 30. system_settings                                                  #
    # ------------------------------------------------------------------ #
    op.create_table(
        "system_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(255), nullable=False, unique=True),
        sa.Column("value", postgresql.JSONB, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ------------------------------------------------------------------ #
    # 31. api_usage_logs                                                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        "api_usage_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("endpoint", sa.String(512), nullable=True),
        sa.Column("method", sa.String(10), nullable=True),
        sa.Column("status_code", sa.Integer, nullable=True),
        sa.Column("duration_ms", sa.Float, nullable=True),
        sa.Column("request_size_bytes", sa.Integer, nullable=True),
        sa.Column("response_size_bytes", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_api_usage_logs_created_at", "api_usage_logs", ["created_at"])
    op.create_index("ix_api_usage_logs_user_created", "api_usage_logs", ["user_id", "created_at"])


def downgrade() -> None:
    # Drop in reverse creation order (deepest FK dependants first)
    op.drop_index("ix_api_usage_logs_user_created", table_name="api_usage_logs")
    op.drop_index("ix_api_usage_logs_created_at", table_name="api_usage_logs")
    op.drop_table("api_usage_logs")

    op.drop_table("system_settings")

    op.drop_index("ix_security_events_created_at", table_name="security_events")
    op.drop_index("ix_security_events_event_type", table_name="security_events")
    op.drop_table("security_events")

    op.drop_index("ix_audit_logs_resource_type_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index(
        "ix_candidate_ranking_items_ranking_id",
        table_name="candidate_ranking_items",
    )
    op.drop_table("candidate_ranking_items")
    op.drop_table("candidate_rankings")

    op.drop_index("ix_predictions_material_id", table_name="predictions")
    op.drop_index("ix_predictions_batch_id", table_name="predictions")
    op.drop_table("predictions")
    op.drop_table("prediction_batches")

    op.drop_table("model_parameters")
    op.drop_table("model_metrics")
    op.drop_table("model_training_runs")
    op.drop_table("model_artifacts")
    op.drop_index(
        "ix_model_versions_type_property_active",
        table_name="model_versions",
    )
    op.drop_table("model_versions")

    op.drop_table("descriptor_vectors")
    op.drop_table("descriptors")
    op.drop_table("descriptor_sets")

    op.drop_table("material_structures")
    op.drop_index("ix_material_properties_property_name", table_name="material_properties")
    op.drop_index("ix_material_properties_material_id", table_name="material_properties")
    op.drop_table("material_properties")
    op.drop_table("material_compositions")
    op.drop_index("ix_materials_chemsys", table_name="materials")
    op.drop_index("ix_materials_reduced_formula", table_name="materials")
    op.drop_index("ix_materials_formula", table_name="materials")
    op.drop_table("materials")

    op.drop_table("uploaded_files")
    op.drop_table("rejected_dataset_rows")
    op.drop_table("dataset_validation_reports")
    op.drop_table("dataset_columns")
    op.drop_index("ix_datasets_status", table_name="datasets")
    op.drop_index("ix_datasets_imported_by", table_name="datasets")
    op.drop_index("ix_datasets_sha256_hash", table_name="datasets")
    op.drop_table("datasets")
    op.drop_table("data_sources")

    op.drop_table("password_reset_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_jti", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("user_roles")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("roles")
