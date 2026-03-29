"""Lagg till ON DELETE SET NULL pa organizations.parent_org_id.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-29

Forhindrar dangling references nar en parent-organisation raderas.
"""

from alembic import op

# revision identifiers, used by Alembic
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Droppa befintlig FK utan ondelete och aterrskapa med SET NULL
    op.drop_constraint(
        "organizations_parent_org_id_fkey", "organizations", type_="foreignkey"
    )
    op.create_foreign_key(
        "organizations_parent_org_id_fkey",
        "organizations",
        "organizations",
        ["parent_org_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "organizations_parent_org_id_fkey", "organizations", type_="foreignkey"
    )
    op.create_foreign_key(
        "organizations_parent_org_id_fkey",
        "organizations",
        "organizations",
        ["parent_org_id"],
        ["id"],
    )
