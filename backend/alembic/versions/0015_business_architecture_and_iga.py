"""Paket A + C: business architecture + IGA (rollkatalog).

Revision ID: 0015
Revises: 0014
Create Date: 2026-04-29

Lägger till:
  Paket A — verksamhetsskikt:
    - business_capabilities, business_processes, value_streams, org_units
    - länktabeller: capability_system_link, process_system_link,
      process_capability_link, process_information_link, unit_capability_link
  Paket C — rollkatalog/IGA:
    - business_roles, positions, role_system_access, employment_templates
    - länktabell: template_role_link

RLS-policies med NULL-bypass-semantik (matchar 0003) skapas på alla
tabeller med organization_id, samt på role_system_access via subquery
mot business_roles.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


# Tabeller med direkt organization_id som ska under RLS
_DIRECT_ORG_TABLES = [
    "business_capabilities",
    "business_processes",
    "value_streams",
    "org_units",
    "business_roles",
    "positions",
    "employment_templates",
]


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # Enums (idempotenta — DO-block hanterar duplicate_object)
    # ------------------------------------------------------------------
    conn.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE orgunittype AS ENUM "
        "('förvaltning','avdelning','enhet','sektion','bolag'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ))
    conn.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE accesslevel AS ENUM ('läs','skriv','administratör'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ))
    conn.execute(sa.text(
        "DO $$ BEGIN "
        "CREATE TYPE accesstype AS ENUM "
        "('grundbehörighet','villkorad','manuell'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    ))

    org_unit_type = postgresql.ENUM(
        "förvaltning", "avdelning", "enhet", "sektion", "bolag",
        name="orgunittype", create_type=False,
    )
    access_level = postgresql.ENUM(
        "läs", "skriv", "administratör",
        name="accesslevel", create_type=False,
    )
    access_type = postgresql.ENUM(
        "grundbehörighet", "villkorad", "manuell",
        name="accesstype", create_type=False,
    )
    criticality_enum = postgresql.ENUM(
        "låg", "medel", "hög", "kritisk",
        name="criticality", create_type=False,
    )

    # ------------------------------------------------------------------
    # business_capabilities
    # ------------------------------------------------------------------
    op.create_table(
        "business_capabilities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"), nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "parent_capability_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_capabilities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("capability_owner", sa.String(255), nullable=True),
        sa.Column("maturity_level", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "maturity_level IS NULL OR (maturity_level BETWEEN 0 AND 5)",
            name="ck_capability_maturity_range",
        ),
    )
    op.create_index(
        "ix_business_capabilities_organization_id",
        "business_capabilities", ["organization_id"],
    )
    op.create_index(
        "ix_business_capabilities_parent_capability_id",
        "business_capabilities", ["parent_capability_id"],
    )
    op.create_index(
        "ix_capabilities_org_name",
        "business_capabilities", ["organization_id", "name"],
    )

    # ------------------------------------------------------------------
    # business_processes
    # ------------------------------------------------------------------
    op.create_table(
        "business_processes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"), nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "parent_process_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_processes.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("process_owner", sa.String(255), nullable=True),
        sa.Column("criticality", criticality_enum, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_business_processes_organization_id",
        "business_processes", ["organization_id"],
    )
    op.create_index(
        "ix_business_processes_parent_process_id",
        "business_processes", ["parent_process_id"],
    )
    op.create_index(
        "ix_processes_org_name",
        "business_processes", ["organization_id", "name"],
    )

    # ------------------------------------------------------------------
    # value_streams
    # ------------------------------------------------------------------
    op.create_table(
        "value_streams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"), nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("stages", postgresql.JSONB(), server_default="[]", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_value_streams_organization_id",
        "value_streams", ["organization_id"],
    )
    op.create_index(
        "ix_value_streams_org_name",
        "value_streams", ["organization_id", "name"],
    )

    # ------------------------------------------------------------------
    # org_units
    # ------------------------------------------------------------------
    op.create_table(
        "org_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"), nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "parent_unit_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("org_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("unit_type", org_unit_type, nullable=False),
        sa.Column("manager_name", sa.String(255), nullable=True),
        sa.Column("cost_center", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_org_units_organization_id", "org_units", ["organization_id"])
    op.create_index("ix_org_units_parent_unit_id", "org_units", ["parent_unit_id"])
    op.create_index("ix_org_units_org_name", "org_units", ["organization_id", "name"])

    # ------------------------------------------------------------------
    # Paket A länktabeller
    # ------------------------------------------------------------------
    op.create_table(
        "capability_system_link",
        sa.Column(
            "capability_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_capabilities.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "system_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("systems.id", ondelete="CASCADE"), primary_key=True,
        ),
    )
    op.create_table(
        "process_system_link",
        sa.Column(
            "process_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_processes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "system_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("systems.id", ondelete="CASCADE"), primary_key=True,
        ),
    )
    op.create_table(
        "process_capability_link",
        sa.Column(
            "process_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_processes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "capability_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_capabilities.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "process_information_link",
        sa.Column(
            "process_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_processes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "information_asset_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("information_assets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "unit_capability_link",
        sa.Column(
            "unit_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("org_units.id", ondelete="CASCADE"), primary_key=True,
        ),
        sa.Column(
            "capability_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_capabilities.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    # ------------------------------------------------------------------
    # business_roles
    # ------------------------------------------------------------------
    op.create_table(
        "business_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"), nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("role_owner", sa.String(255), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_business_roles_organization_id",
        "business_roles", ["organization_id"],
    )
    op.create_index(
        "ix_business_roles_org_name",
        "business_roles", ["organization_id", "name"],
    )

    # ------------------------------------------------------------------
    # positions
    # ------------------------------------------------------------------
    op.create_table(
        "positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"), nullable=False,
        ),
        sa.Column(
            "org_unit_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("org_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("position_code", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_positions_organization_id",
        "positions", ["organization_id"],
    )
    op.create_index("ix_positions_org_unit_id", "positions", ["org_unit_id"])
    op.create_index("ix_positions_org_title", "positions", ["organization_id", "title"])

    # ------------------------------------------------------------------
    # role_system_access
    # ------------------------------------------------------------------
    op.create_table(
        "role_system_access",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "business_role_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "system_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("systems.id", ondelete="CASCADE"), nullable=False,
        ),
        sa.Column("access_level", access_level, nullable=False),
        sa.Column(
            "access_type", access_type,
            server_default="grundbehörighet", nullable=False,
        ),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("approver_name", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("business_role_id", "system_id", name="uq_role_system"),
    )
    op.create_index(
        "ix_role_system_access_business_role_id",
        "role_system_access", ["business_role_id"],
    )
    op.create_index(
        "ix_role_system_access_system_id",
        "role_system_access", ["system_id"],
    )

    # ------------------------------------------------------------------
    # employment_templates
    # ------------------------------------------------------------------
    op.create_table(
        "employment_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"), nullable=False,
        ),
        sa.Column(
            "position_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("positions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_employment_templates_organization_id",
        "employment_templates", ["organization_id"],
    )
    op.create_index(
        "ix_employment_templates_position_id",
        "employment_templates", ["position_id"],
    )
    op.create_index(
        "ix_employment_templates_org_name",
        "employment_templates", ["organization_id", "name"],
    )

    # ------------------------------------------------------------------
    # template_role_link
    # ------------------------------------------------------------------
    op.create_table(
        "template_role_link",
        sa.Column(
            "template_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("employment_templates.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "role_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("business_roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )

    # ------------------------------------------------------------------
    # RLS — direkt organization_id (NULL-bypass-semantik per 0003)
    # Policy-namn: tenant_isolation_<table>
    # ------------------------------------------------------------------
    for table in _DIRECT_ORG_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            AS PERMISSIVE
            FOR ALL
            TO PUBLIC
            USING (
                current_org_id() IS NULL
                OR organization_id = current_org_id()
            );
        """)

    # ------------------------------------------------------------------
    # RLS — role_system_access via business_roles.organization_id
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE role_system_access ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE role_system_access FORCE ROW LEVEL SECURITY;")
    op.execute("""
        CREATE POLICY tenant_isolation_role_system_access ON role_system_access
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (
            current_org_id() IS NULL
            OR EXISTS (
                SELECT 1 FROM business_roles br
                WHERE br.id = role_system_access.business_role_id
                  AND br.organization_id = current_org_id()
            )
        );
    """)


def downgrade() -> None:
    # RLS policies + RLS av
    for table in _DIRECT_ORG_TABLES + ["role_system_access"]:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    # Länktabeller (Paket C → A)
    op.drop_table("template_role_link")
    op.drop_table("employment_templates")
    op.drop_table("role_system_access")
    op.drop_table("positions")
    op.drop_table("business_roles")

    # Paket A länktabeller
    op.drop_table("unit_capability_link")
    op.drop_table("process_information_link")
    op.drop_table("process_capability_link")
    op.drop_table("process_system_link")
    op.drop_table("capability_system_link")

    # Paket A entiteter
    op.drop_table("org_units")
    op.drop_table("value_streams")
    op.drop_table("business_processes")
    op.drop_table("business_capabilities")

    # Enums
    sa.Enum(name="accesstype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="accesslevel").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="orgunittype").drop(op.get_bind(), checkfirst=True)
