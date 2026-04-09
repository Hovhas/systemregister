"""Add SBOM fields (license, CPE, PURL) to systems and modules.

Revision ID: 0010
Revises: 0009
Create Date: 2026-04-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Systems
    op.add_column("systems", sa.Column("license_id", sa.String(100), nullable=True))
    op.add_column("systems", sa.Column("cpe", sa.String(500), nullable=True))
    op.add_column("systems", sa.Column("purl", sa.String(500), nullable=True))
    # Modules
    op.add_column("modules", sa.Column("license_id", sa.String(100), nullable=True))
    op.add_column("modules", sa.Column("cpe", sa.String(500), nullable=True))
    op.add_column("modules", sa.Column("purl", sa.String(500), nullable=True))
    op.add_column("modules", sa.Column("supplier", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("modules", "supplier")
    op.drop_column("modules", "purl")
    op.drop_column("modules", "cpe")
    op.drop_column("modules", "license_id")
    op.drop_column("systems", "purl")
    op.drop_column("systems", "cpe")
    op.drop_column("systems", "license_id")
