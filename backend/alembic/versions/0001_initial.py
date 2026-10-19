"""Create CloudPulse core tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-19
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "monitors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("target_key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("source_kind", sa.String(length=16), nullable=False),
        sa.Column("expected_status", sa.Integer(), nullable=False),
        sa.Column("max_latency_ms", sa.Integer(), nullable=False),
        sa.Column("check_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("validation_profile", sa.String(length=64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_execution_id", sa.String(length=128), nullable=True),
        sa.Column("rate_limit_streak", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("check_interval_minutes BETWEEN 5 AND 10080", name="ck_monitors_interval"),
        sa.CheckConstraint("expected_status BETWEEN 100 AND 599", name="ck_monitors_expected_status"),
        sa.CheckConstraint("max_latency_ms BETWEEN 100 AND 30000", name="ck_monitors_max_latency"),
        sa.CheckConstraint("source_kind IN ('REAL', 'MOCK')", name="ck_monitors_source_kind"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target_key"),
    )
    op.create_index("ix_monitors_lease_expires_at", "monitors", ["lease_expires_at"])
    op.create_index("ix_monitors_next_check_at", "monitors", ["next_check_at"])
    op.create_table(
        "admin_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_admin_sessions_expires_at", "admin_sessions", ["expires_at"])
    op.create_table(
        "check_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("monitor_id", sa.Uuid(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("error_summary", sa.String(length=500), nullable=True),
        sa.Column("source_data_date", sa.Date(), nullable=True),
        sa.Column("data_warning", sa.String(length=64), nullable=True),
        sa.Column("execution_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('UP', 'DOWN', 'DEGRADED')", name="ck_check_results_status"),
        sa.ForeignKeyConstraint(["monitor_id"], ["monitors.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_id", "monitor_id", name="uq_check_results_execution_monitor"),
    )
    op.create_index("ix_check_results_monitor_checked", "check_results", ["monitor_id", "checked_at"])


def downgrade() -> None:
    op.drop_index("ix_check_results_monitor_checked", table_name="check_results")
    op.drop_table("check_results")
    op.drop_index("ix_admin_sessions_expires_at", table_name="admin_sessions")
    op.drop_table("admin_sessions")
    op.drop_index("ix_monitors_next_check_at", table_name="monitors")
    op.drop_index("ix_monitors_lease_expires_at", table_name="monitors")
    op.drop_table("monitors")
