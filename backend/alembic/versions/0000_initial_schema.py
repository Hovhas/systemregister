"""initial_schema

Revision ID: 0000
Revises:
Create Date: 2026-03-27

Skapar alla tabeller för systemregistret.
Måste köras före 0001_enable_rls_multi_org.
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers
revision = "0000"
down_revision = None
branch_labels = None
depends_on = None


def _enum(name: str, *values: str) -> postgresql.ENUM:
    """Returnerar en postgresql.ENUM som INTE skapar/droppar typen automatiskt."""
    return postgresql.ENUM(*values, name=name, create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    # Skapa alla enum-typer explicit med rå SQL (säkraste sättet)
    enums = {
        "organizationtype": ("kommun", "bolag", "samverkan", "digit"),
        "systemcategory": ("verksamhetssystem", "stödsystem", "infrastruktur", "plattform", "iot"),
        "lifecyclestatus": ("planerad", "under_inforande", "i_drift", "under_avveckling", "avvecklad"),
        "criticality": ("låg", "medel", "hög", "kritisk"),
        "nis2classification": ("väsentlig", "viktig", "ej_tillämplig"),
        "ownerrole": ("systemägare", "informationsägare", "systemförvaltare",
                      "teknisk_förvaltare", "it_kontakt", "dataskyddsombud"),
        "integrationtype": ("api", "filöverföring", "databasreplikering", "event", "manuell"),
        "processoragreementstatus": ("ja", "nej", "under_framtagande", "ej_tillämpligt"),
        "auditaction": ("create", "update", "delete"),
        "integration_criticality": ("låg", "medel", "hög", "kritisk"),
    }
    for name, values in enums.items():
        vals = ", ".join(f"'{v}'" for v in values)
        op.execute(f"CREATE TYPE {name} AS ENUM ({vals})")

    # ------------------------------------------------------------------
    # organizations
    # ------------------------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("org_number", sa.String(20), nullable=True),
        sa.Column("org_type", _enum("organizationtype", "kommun", "bolag", "samverkan", "digit"), nullable=False),
        sa.Column("parent_org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_number"),
        sa.ForeignKeyConstraint(["parent_org_id"], ["organizations.id"]),
    )

    # ------------------------------------------------------------------
    # systems
    # ------------------------------------------------------------------
    op.create_table(
        "systems",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("aliases", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("system_category", _enum("systemcategory",
            "verksamhetssystem", "stödsystem", "infrastruktur", "plattform", "iot"), nullable=False),
        sa.Column("business_area", sa.String(255), nullable=True),
        # Klassning & säkerhet
        sa.Column("criticality", _enum("criticality", "låg", "medel", "hög", "kritisk"), nullable=True),
        sa.Column("has_elevated_protection", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("security_protection", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("nis2_applicable", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("nis2_classification", _enum("nis2classification",
            "väsentlig", "viktig", "ej_tillämplig"), nullable=True),
        # GDPR
        sa.Column("treats_personal_data", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("treats_sensitive_data", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("third_country_transfer", sa.Boolean, nullable=False, server_default="false"),
        # Driftmiljö
        sa.Column("hosting_model", sa.String(50), nullable=True),
        sa.Column("cloud_provider", sa.String(255), nullable=True),
        sa.Column("data_location_country", sa.String(100), nullable=True, server_default="'Sverige'"),
        sa.Column("product_name", sa.String(255), nullable=True),
        sa.Column("product_version", sa.String(100), nullable=True),
        # Livscykel
        sa.Column("lifecycle_status", _enum("lifecyclestatus",
            "planerad", "under_inforande", "i_drift", "under_avveckling", "avvecklad"), nullable=True),
        sa.Column("deployment_date", sa.Date, nullable=True),
        sa.Column("planned_decommission_date", sa.Date, nullable=True),
        sa.Column("end_of_support_date", sa.Date, nullable=True),
        # Backup/DR
        sa.Column("backup_frequency", sa.String(100), nullable=True),
        sa.Column("rpo", sa.String(100), nullable=True),
        sa.Column("rto", sa.String(100), nullable=True),
        sa.Column("dr_plan_exists", sa.Boolean, nullable=False, server_default="false"),
        # Compliance
        sa.Column("last_risk_assessment_date", sa.Date, nullable=True),
        sa.Column("klassa_reference_id", sa.String(100), nullable=True),
        # Flexibla attribut
        sa.Column("extended_attributes", postgresql.JSONB, nullable=True),
        # Meta
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reviewed_by", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
    )
    op.create_index("ix_systems_organization_id", "systems", ["organization_id"])
    op.create_index("ix_systems_org_name", "systems", ["organization_id", "name"])
    op.create_index("ix_systems_lifecycle", "systems", ["lifecycle_status"])
    op.create_index("ix_systems_criticality", "systems", ["criticality"])

    # ------------------------------------------------------------------
    # system_classifications
    # ------------------------------------------------------------------
    op.create_table(
        "system_classifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("system_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("confidentiality", sa.Integer, nullable=False),
        sa.Column("integrity", sa.Integer, nullable=False),
        sa.Column("availability", sa.Integer, nullable=False),
        sa.Column("traceability", sa.Integer, nullable=True),
        sa.Column("classified_by", sa.String(255), nullable=False),
        sa.Column("classified_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("valid_until", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["system_id"], ["systems.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_system_classifications_system_id", "system_classifications", ["system_id"])

    # ------------------------------------------------------------------
    # system_owners
    # ------------------------------------------------------------------
    op.create_table(
        "system_owners",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("system_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", _enum("ownerrole",
            "systemägare", "informationsägare", "systemförvaltare",
            "teknisk_förvaltare", "it_kontakt", "dataskyddsombud"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["system_id"], ["systems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.UniqueConstraint("system_id", "role", "name", name="uq_system_owner_role"),
    )
    op.create_index("ix_system_owners_system_id", "system_owners", ["system_id"])

    # ------------------------------------------------------------------
    # system_integrations
    # ------------------------------------------------------------------
    op.create_table(
        "system_integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_system_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_system_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("integration_type", _enum("integrationtype",
            "api", "filöverföring", "databasreplikering", "event", "manuell"), nullable=False),
        sa.Column("data_types", sa.Text, nullable=True),
        sa.Column("frequency", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("criticality", _enum("integration_criticality",
            "låg", "medel", "hög", "kritisk"), nullable=True),
        sa.Column("is_external", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("external_party", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_system_id"], ["systems.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_system_id"], ["systems.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_system_integrations_source_system_id", "system_integrations", ["source_system_id"])
    op.create_index("ix_system_integrations_target_system_id", "system_integrations", ["target_system_id"])

    # ------------------------------------------------------------------
    # gdpr_treatments
    # ------------------------------------------------------------------
    op.create_table(
        "gdpr_treatments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("system_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ropa_reference_id", sa.String(100), nullable=True),
        sa.Column("data_categories", postgresql.JSONB, nullable=True),
        sa.Column("categories_of_data_subjects", sa.Text, nullable=True),
        sa.Column("legal_basis", sa.String(255), nullable=True),
        sa.Column("data_processor", sa.String(255), nullable=True),
        sa.Column("processor_agreement_status", _enum("processoragreementstatus",
            "ja", "nej", "under_framtagande", "ej_tillämpligt"), nullable=True),
        sa.Column("sub_processors", postgresql.JSONB, nullable=True),
        sa.Column("third_country_transfer_details", sa.Text, nullable=True),
        sa.Column("retention_policy", sa.Text, nullable=True),
        sa.Column("dpia_conducted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("dpia_date", sa.Date, nullable=True),
        sa.Column("dpia_link", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["system_id"], ["systems.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_gdpr_treatments_system_id", "gdpr_treatments", ["system_id"])

    # ------------------------------------------------------------------
    # contracts
    # ------------------------------------------------------------------
    op.create_table(
        "contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("system_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_name", sa.String(255), nullable=False),
        sa.Column("supplier_org_number", sa.String(20), nullable=True),
        sa.Column("contract_id_external", sa.String(100), nullable=True),
        sa.Column("contract_start", sa.Date, nullable=True),
        sa.Column("contract_end", sa.Date, nullable=True),
        sa.Column("auto_renewal", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("notice_period_months", sa.Integer, nullable=True),
        sa.Column("sla_description", sa.Text, nullable=True),
        sa.Column("license_model", sa.String(100), nullable=True),
        sa.Column("annual_license_cost", sa.Integer, nullable=True),
        sa.Column("annual_operations_cost", sa.Integer, nullable=True),
        sa.Column("procurement_type", sa.String(100), nullable=True),
        sa.Column("support_level", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["system_id"], ["systems.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_contracts_system_id", "contracts", ["system_id"])

    # ------------------------------------------------------------------
    # audit_log
    # ------------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", _enum("auditaction", "create", "update", "delete"), nullable=False),
        sa.Column("changed_by", sa.String(255), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("old_values", postgresql.JSONB, nullable=True),
        sa.Column("new_values", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_table_name", "audit_log", ["table_name"])
    op.create_index("ix_audit_log_record_id", "audit_log", ["record_id"])
    op.create_index("ix_audit_log_table_record", "audit_log", ["table_name", "record_id"])
    op.create_index("ix_audit_log_changed_at", "audit_log", ["changed_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("contracts")
    op.drop_table("gdpr_treatments")
    op.drop_table("system_integrations")
    op.drop_table("system_owners")
    op.drop_table("system_classifications")
    op.drop_table("systems")
    op.drop_table("organizations")

    for name in [
        "auditaction", "processoragreementstatus", "integrationtype",
        "ownerrole", "nis2classification", "integration_criticality",
        "criticality", "lifecyclestatus", "systemcategory", "organizationtype",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {name}")
