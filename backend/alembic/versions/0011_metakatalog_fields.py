"""Add Metakatalog reference fields to systems.

Revision ID: 0011
Revises: 0010
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("systems", sa.Column("metakatalog_id", sa.String(255), nullable=True))
    op.add_column("systems", sa.Column("metakatalog_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint("uq_systems_metakatalog_id", "systems", ["metakatalog_id"])


def downgrade() -> None:
    op.drop_constraint("uq_systems_metakatalog_id", "systems", type_="unique")
    op.drop_column("systems", "metakatalog_synced_at")
    op.drop_column("systems", "metakatalog_id")
