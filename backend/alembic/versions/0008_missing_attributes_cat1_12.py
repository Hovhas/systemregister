"""Add missing attributes from kravspec categories 1-12.

Revision ID: 0008
Revises: 0007
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Kategori 1: Grundläggande identifiering
    op.add_column("systems", sa.Column("business_processes", sa.Text(), nullable=True))

    # Kategori 3: Klassning & säkerhet
    op.add_column("systems", sa.Column("encryption_at_rest", sa.String(255), nullable=True))
    op.add_column("systems", sa.Column("encryption_in_transit", sa.String(255), nullable=True))
    op.add_column("systems", sa.Column("access_control_model", sa.String(255), nullable=True))

    # Kategori 4: GDPR utökat
    op.add_column("systems", sa.Column("retention_rules", sa.Text(), nullable=True))

    # Kategori 5: Driftmiljö utökat
    op.add_column("systems", sa.Column("architecture_type", sa.String(100), nullable=True))
    op.add_column("systems", sa.Column("environments", sa.String(255), nullable=True))

    # Kategori 6: Livscykel utökat
    op.add_column("systems", sa.Column("last_major_upgrade", sa.String(255), nullable=True))
    op.add_column("systems", sa.Column("next_planned_review", sa.Date(), nullable=True))

    # Kategori 9: Backup/DR utökat
    op.add_column("systems", sa.Column("backup_storage_location", sa.String(255), nullable=True))
    op.add_column("systems", sa.Column("last_restore_test", sa.String(255), nullable=True))

    # Kategori 10: Kostnader utökat
    op.add_column("systems", sa.Column("cost_center", sa.String(255), nullable=True))
    op.add_column("systems", sa.Column("total_cost_of_ownership", sa.Integer(), nullable=True))

    # Kategori 11: Dokumentation utökat
    op.add_column("systems", sa.Column("documentation_links", postgresql.JSONB(), nullable=True))

    # Kategori 12: Compliance utökat
    op.add_column("systems", sa.Column("linked_risks", sa.Text(), nullable=True))
    op.add_column("systems", sa.Column("incident_history", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("systems", "incident_history")
    op.drop_column("systems", "linked_risks")
    op.drop_column("systems", "documentation_links")
    op.drop_column("systems", "total_cost_of_ownership")
    op.drop_column("systems", "cost_center")
    op.drop_column("systems", "last_restore_test")
    op.drop_column("systems", "backup_storage_location")
    op.drop_column("systems", "next_planned_review")
    op.drop_column("systems", "last_major_upgrade")
    op.drop_column("systems", "environments")
    op.drop_column("systems", "architecture_type")
    op.drop_column("systems", "retention_rules")
    op.drop_column("systems", "access_control_model")
    op.drop_column("systems", "encryption_in_transit")
    op.drop_column("systems", "encryption_at_rest")
    op.drop_column("systems", "business_processes")
