"""Sätt NOT NULL på systems.criticality och systems.lifecycle_status.

Revision ID: 0005
Revises: 0004
Create Date: 2026-03-29

systems.criticality och systems.lifecycle_status definieras som NOT NULL
i SQLAlchemy-modellen men skapades som nullable=True i migration 0000.
Denna migration synkroniserar databasen med modellen:
  1. Fyller eventuella NULL-rader med DEFAULT-värden (medel / i_drift).
  2. Sätter NOT NULL-constraint.
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fyll befintliga NULL-rader med default-värden innan NOT NULL sätts
    op.execute(
        "UPDATE systems SET criticality = 'medel' WHERE criticality IS NULL"
    )
    op.execute(
        "UPDATE systems SET lifecycle_status = 'i_drift' WHERE lifecycle_status IS NULL"
    )

    # Sätt NOT NULL — alter_column hanterar detta utan att tappa enum-typen
    op.alter_column("systems", "criticality", nullable=False)
    op.alter_column("systems", "lifecycle_status", nullable=False)


def downgrade() -> None:
    # Återgå till nullable (tar bort NOT NULL-constraintet)
    op.alter_column("systems", "criticality", nullable=True)
    op.alter_column("systems", "lifecycle_status", nullable=True)
