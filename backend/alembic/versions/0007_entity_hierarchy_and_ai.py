"""Add entity hierarchy (objekt, components, modules, information_assets) and AI regulation fields.

Revision ID: 0007
Revises: 0006
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- AI risk class & FRIA status enums ---
    ai_risk_class = postgresql.ENUM(
        "förbjuden", "hög_risk", "begränsad_risk", "minimal_risk", "ej_tillämplig",
        name="airiskclass", create_type=True,
    )
    ai_risk_class.create(op.get_bind(), checkfirst=True)

    fria_status = postgresql.ENUM(
        "ja", "nej", "ej_tillämplig",
        name="friastatus", create_type=True,
    )
    fria_status.create(op.get_bind(), checkfirst=True)

    # --- AI fields on systems ---
    op.add_column("systems", sa.Column("uses_ai", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("systems", sa.Column("ai_risk_class", ai_risk_class, nullable=True))
    op.add_column("systems", sa.Column("ai_usage_description", sa.Text(), nullable=True))
    op.add_column("systems", sa.Column("fria_status", fria_status, nullable=True))
    op.add_column("systems", sa.Column("fria_date", sa.Date(), nullable=True))
    op.add_column("systems", sa.Column("fria_link", sa.Text(), nullable=True))
    op.add_column("systems", sa.Column("ai_human_oversight", sa.String(255), nullable=True))
    op.add_column("systems", sa.Column("ai_supplier", sa.String(255), nullable=True))
    op.add_column("systems", sa.Column("ai_transparency_fulfilled", sa.Boolean(), server_default="false", nullable=False))
    op.add_column("systems", sa.Column("ai_model_version", sa.String(255), nullable=True))
    op.add_column("systems", sa.Column("ai_last_review_date", sa.Date(), nullable=True))

    # --- Objekt table ---
    op.create_table(
        "objekt",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("object_owner", sa.String(255), nullable=True),
        sa.Column("object_leader", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_objekt_organization_id", "objekt", ["organization_id"])

    # FK from systems → objekt
    op.add_column("systems", sa.Column("objekt_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_systems_objekt_id", "systems", "objekt", ["objekt_id"], ["id"], ondelete="SET NULL")

    # --- Components table ---
    op.create_table(
        "components",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("system_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("systems.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("component_type", sa.String(100), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("business_area", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_components_system_id", "components", ["system_id"])
    op.create_index("ix_components_organization_id", "components", ["organization_id"])

    # --- Modules table ---
    op.create_table(
        "modules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("lifecycle_status", sa.Enum(
            "planerad", "under_inforande", "i_drift", "under_avveckling", "avvecklad",
            name="lifecyclestatus", create_type=False,
        ), nullable=True),
        sa.Column("hosting_model", sa.String(50), nullable=True),
        sa.Column("product_name", sa.String(255), nullable=True),
        sa.Column("product_version", sa.String(100), nullable=True),
        sa.Column("uses_ai", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("ai_risk_class", ai_risk_class, nullable=True),
        sa.Column("ai_usage_description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_modules_organization_id", "modules", ["organization_id"])

    # --- Module ↔ System junction ---
    op.create_table(
        "module_system_link",
        sa.Column("module_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("system_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("systems.id", ondelete="CASCADE"), primary_key=True),
    )

    # --- Information Assets table ---
    op.create_table(
        "information_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("information_owner", sa.String(255), nullable=True),
        sa.Column("confidentiality", sa.Integer(), nullable=True),
        sa.Column("integrity", sa.Integer(), nullable=True),
        sa.Column("availability", sa.Integer(), nullable=True),
        sa.Column("traceability", sa.Integer(), nullable=True),
        sa.Column("contains_personal_data", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("personal_data_type", sa.String(100), nullable=True),
        sa.Column("contains_public_records", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("ropa_reference_id", sa.String(100), nullable=True),
        sa.Column("ihp_reference", sa.Text(), nullable=True),
        sa.Column("preservation_class", sa.String(100), nullable=True),
        sa.Column("retention_period", sa.String(255), nullable=True),
        sa.Column("archive_responsible", sa.String(255), nullable=True),
        sa.Column("e_archive_delivery", sa.String(100), nullable=True),
        sa.Column("long_term_format", sa.String(255), nullable=True),
        sa.Column("last_ihp_review", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_information_assets_organization_id", "information_assets", ["organization_id"])

    # --- InformationAsset ↔ System junction ---
    op.create_table(
        "information_asset_system_link",
        sa.Column("information_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("information_assets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("system_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("systems.id", ondelete="CASCADE"), primary_key=True),
    )


def downgrade() -> None:
    op.drop_table("information_asset_system_link")
    op.drop_table("information_assets")
    op.drop_table("module_system_link")
    op.drop_table("modules")
    op.drop_table("components")
    op.drop_constraint("fk_systems_objekt_id", "systems", type_="foreignkey")
    op.drop_column("systems", "objekt_id")
    op.drop_table("objekt")
    # AI fields
    op.drop_column("systems", "ai_last_review_date")
    op.drop_column("systems", "ai_model_version")
    op.drop_column("systems", "ai_transparency_fulfilled")
    op.drop_column("systems", "ai_supplier")
    op.drop_column("systems", "ai_human_oversight")
    op.drop_column("systems", "fria_link")
    op.drop_column("systems", "fria_date")
    op.drop_column("systems", "fria_status")
    op.drop_column("systems", "ai_usage_description")
    op.drop_column("systems", "ai_risk_class")
    op.drop_column("systems", "uses_ai")
    # Enums
    sa.Enum(name="friastatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="airiskclass").drop(op.get_bind(), checkfirst=True)
