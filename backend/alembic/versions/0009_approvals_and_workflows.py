"""Add approvals/workflow table (FK-15).

Revision ID: 0009
Revises: 0008
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    approval_status = postgresql.ENUM(
        "väntande", "godkänd", "avvisad", "avbruten",
        name="approvalstatus", create_type=True,
    )
    approval_status.create(op.get_bind(), checkfirst=True)

    approval_type = postgresql.ENUM(
        "systemregistrering", "avveckling", "klassningsändring", "gdpr_behandling", "dataändring",
        name="approvaltype", create_type=True,
    )
    approval_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("approval_type", approval_type, nullable=False),
        sa.Column("status", approval_status, server_default="väntande", nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_table", sa.String(100), nullable=True),
        sa.Column("target_record_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("proposed_changes", postgresql.JSONB(), nullable=True),
        sa.Column("requested_by", sa.String(255), nullable=True),
        sa.Column("reviewed_by", sa.String(255), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_approvals_organization_id", "approvals", ["organization_id"])
    op.create_index("ix_approvals_status", "approvals", ["status"])
    op.create_index("ix_approvals_target", "approvals", ["target_table", "target_record_id"])


def downgrade() -> None:
    op.drop_table("approvals")
    sa.Enum(name="approvalstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="approvaltype").drop(op.get_bind(), checkfirst=True)
