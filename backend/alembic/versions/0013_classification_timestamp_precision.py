"""Change classified_at default from now() to clock_timestamp().

now() returns transaction start time, meaning two classifications created
within the same transaction get identical timestamps. clock_timestamp()
returns the actual wall-clock time at the moment of insertion.

Revision ID: 0013
Revises: 0012
Create Date: 2026-04-15
"""
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE system_classifications "
        "ALTER COLUMN classified_at SET DEFAULT clock_timestamp()"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE system_classifications "
        "ALTER COLUMN classified_at SET DEFAULT now()"
    )
