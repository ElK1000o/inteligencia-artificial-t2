"""Add optional tables: background_jobs, user_dataset_access + performance indexes

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-01-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # background_jobs                                                      #
    # Tracks async/long-running operations (training, descriptor gen, etc.)
    # ------------------------------------------------------------------ #
    op.create_table(
        "background_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        # "descriptor_generation" | "model_training" | "prediction_batch" | "report_gen"
        sa.Column("job_type", sa.String(100), nullable=False),
        # pending | running | completed | failed | cancelled
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        # Input parameters serialized as JSON
        sa.Column("payload", postgresql.JSONB, nullable=True),
        # Result summary or error message
        sa.Column("result", postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("progress_pct", sa.Float, nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
    )
    op.create_index("ix_background_jobs_status", "background_jobs", ["status"])
    op.create_index("ix_background_jobs_created_at", "background_jobs", ["created_at"])
    op.create_index("ix_background_jobs_created_by", "background_jobs", ["created_by"])

    # ------------------------------------------------------------------ #
    # user_dataset_access                                                   #
    # Fine-grained per-user dataset permissions (for private datasets).    #
    # ------------------------------------------------------------------ #
    op.create_table(
        "user_dataset_access",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # "read" | "write" | "owner"
        sa.Column("permission_level", sa.String(20), nullable=False, server_default=sa.text("'read'")),
        sa.Column(
            "granted_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "dataset_id", name="uq_user_dataset_access"),
    )
    op.create_index("ix_user_dataset_access_user_id", "user_dataset_access", ["user_id"])
    op.create_index("ix_user_dataset_access_dataset_id", "user_dataset_access", ["dataset_id"])

    # ------------------------------------------------------------------ #
    # Performance indexes for high-traffic query patterns                  #
    # ------------------------------------------------------------------ #

    # audit_logs: recent activity queries
    op.create_index(
        "ix_audit_logs_created_at_desc",
        "audit_logs",
        [sa.text("created_at DESC")],
    )

    # predictions: time-series queries by batch
    op.create_index(
        "ix_predictions_created_at",
        "predictions",
        ["created_at"],
    )

    # model_metrics: finding best model for a property
    op.create_index(
        "ix_model_metrics_property_metric",
        "model_metrics",
        ["metric_name", "metric_value"],
    )

    # materials: element-based searches (partial index on chemsys)
    op.create_index(
        "ix_materials_dataset_created",
        "materials",
        ["dataset_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_materials_dataset_created", table_name="materials")
    op.drop_index("ix_model_metrics_property_metric", table_name="model_metrics")
    op.drop_index("ix_predictions_created_at", table_name="predictions")
    op.drop_index("ix_audit_logs_created_at_desc", table_name="audit_logs")
    op.drop_index("ix_user_dataset_access_dataset_id", table_name="user_dataset_access")
    op.drop_index("ix_user_dataset_access_user_id", table_name="user_dataset_access")
    op.drop_table("user_dataset_access")
    op.drop_index("ix_background_jobs_created_by", table_name="background_jobs")
    op.drop_index("ix_background_jobs_created_at", table_name="background_jobs")
    op.drop_index("ix_background_jobs_status", table_name="background_jobs")
    op.drop_table("background_jobs")
