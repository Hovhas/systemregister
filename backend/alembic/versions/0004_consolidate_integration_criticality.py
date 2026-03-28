"""Konsolidera integration_criticality till befintlig criticality-typ.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-28

Ändrar system_integrations.criticality att återanvända den gemensamma
PostgreSQL enum-typen "criticality" istället för den separata typen
"integration_criticality", och droppar den onödiga typen.
"""

from alembic import op

# revision identifiers, used by Alembic
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ändra kolumnen till att använda den gemensamma criticality-typen
    op.execute(
        "ALTER TABLE system_integrations "
        "ALTER COLUMN criticality TYPE criticality "
        "USING criticality::text::criticality"
    )
    # Droppa den onödiga separata enum-typen
    op.execute("DROP TYPE IF EXISTS integration_criticality")


def downgrade() -> None:
    # Återskapa den separata typen och konvertera tillbaka
    op.execute(
        "CREATE TYPE integration_criticality AS ENUM "
        "('lag', 'medel', 'hog', 'kritisk')"
    )
    op.execute(
        "ALTER TABLE system_integrations "
        "ALTER COLUMN criticality TYPE integration_criticality "
        "USING criticality::text::integration_criticality"
    )
