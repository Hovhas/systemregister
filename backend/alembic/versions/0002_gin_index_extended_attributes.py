"""Add GIN index on systems.extended_attributes for JSONB search."""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX ix_systems_extended_gin ON systems USING GIN (extended_attributes)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_systems_extended_gin")
