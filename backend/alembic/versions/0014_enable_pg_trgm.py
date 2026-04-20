"""Enable pg_trgm extension.

Systems-endpointens dubbletthantering använder func.similarity() från
pg_trgm. Utan extensionen misslyckas POST /systems/ med ProgrammingError,
vilket i CI-miljö (ephemeral postgres utan init-db.sql) rullar tillbaka
testets transaktion och orsakar FK-fel på efterföljande insert.

Revision ID: 0014
Revises: 0013
Create Date: 2026-04-20
"""
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
