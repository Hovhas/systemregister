"""Add missing indexes for performance.

Revision ID: 0012
Revises: 0011
Create Date: 2026-04-13
"""
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Index on systems.objekt_id (FK column, improves objekt->systems count queries)
    op.create_index("ix_systems_objekt_id", "systems", ["objekt_id"])

    # Index on audit_log.changed_by for user-based queries
    op.create_index("ix_audit_log_changed_by", "audit_log", ["changed_by"])

    # Note: ix_objekt_organization_id, ix_modules_organization_id,
    # ix_components_organization_id, ix_information_assets_organization_id
    # already created in migration 0007_entity_hierarchy_and_ai.py


def downgrade() -> None:
    op.drop_index("ix_audit_log_changed_by", "audit_log")
    op.drop_index("ix_systems_objekt_id", "systems")
