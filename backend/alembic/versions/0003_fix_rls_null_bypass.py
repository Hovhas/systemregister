"""fix_rls_null_bypass

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-28

Åtgärdar RLS-policies som blockerade ALL data när org-context inte var satt.

Problem: Migration 0001 skapade policies med:
    USING (organization_id = current_org_id())
Om current_org_id() returnerar NULL (ingen context satt) evalueras
NULL = UUID → FALSE, vilket blockerar all data.

Lösning: Lägg till NULL-bypass i alla 6 org_isolation-policies:
    USING (current_org_id() IS NULL OR organization_id = current_org_id())
NULL-fallet låter icke-kontextuerade anrop passera igenom, medan
satta contexts fortfarande isolerar per organisation.

Matchar semantiken i conftest.py som redan använder NULL-bypass.
"""
from alembic import op

# revision identifiers
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# Tabeller som berörs
_DIRECT_ORG_TABLES = [
    "systems",
    "system_owners",
]

_SUBQUERY_TABLES = [
    "system_classifications",
    "system_integrations",
    "gdpr_treatments",
    "contracts",
]


def upgrade() -> None:
    # ------------------------------------------------------------------
    # DROP befintliga policies (skapade utan NULL-bypass i 0001)
    # ------------------------------------------------------------------
    for table in _DIRECT_ORG_TABLES + _SUBQUERY_TABLES:
        op.execute(f"DROP POLICY IF EXISTS org_isolation ON {table};")

    # ------------------------------------------------------------------
    # systems — direkt organization_id med NULL-bypass
    # ------------------------------------------------------------------
    op.execute("""
        CREATE POLICY org_isolation ON systems
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (current_org_id() IS NULL OR organization_id = current_org_id());
    """)

    # ------------------------------------------------------------------
    # system_owners — direkt organization_id med NULL-bypass
    # ------------------------------------------------------------------
    op.execute("""
        CREATE POLICY org_isolation ON system_owners
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (current_org_id() IS NULL OR organization_id = current_org_id());
    """)

    # ------------------------------------------------------------------
    # system_classifications — via systems.organization_id med NULL-bypass
    # ------------------------------------------------------------------
    op.execute("""
        CREATE POLICY org_isolation ON system_classifications
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (
            current_org_id() IS NULL
            OR EXISTS (
                SELECT 1 FROM systems s
                WHERE s.id = system_classifications.system_id
                  AND s.organization_id = current_org_id()
            )
        );
    """)

    # ------------------------------------------------------------------
    # system_integrations — source ELLER target med NULL-bypass
    # ------------------------------------------------------------------
    op.execute("""
        CREATE POLICY org_isolation ON system_integrations
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (
            current_org_id() IS NULL
            OR EXISTS (
                SELECT 1 FROM systems s
                WHERE s.organization_id = current_org_id()
                  AND (
                      s.id = system_integrations.source_system_id
                   OR s.id = system_integrations.target_system_id
                  )
            )
        );
    """)

    # ------------------------------------------------------------------
    # gdpr_treatments — via systems.organization_id med NULL-bypass
    # ------------------------------------------------------------------
    op.execute("""
        CREATE POLICY org_isolation ON gdpr_treatments
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (
            current_org_id() IS NULL
            OR EXISTS (
                SELECT 1 FROM systems s
                WHERE s.id = gdpr_treatments.system_id
                  AND s.organization_id = current_org_id()
            )
        );
    """)

    # ------------------------------------------------------------------
    # contracts — via systems.organization_id med NULL-bypass
    # ------------------------------------------------------------------
    op.execute("""
        CREATE POLICY org_isolation ON contracts
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (
            current_org_id() IS NULL
            OR EXISTS (
                SELECT 1 FROM systems s
                WHERE s.id = contracts.system_id
                  AND s.organization_id = current_org_id()
            )
        );
    """)


def downgrade() -> None:
    # ------------------------------------------------------------------
    # DROP NULL-bypass-policies
    # ------------------------------------------------------------------
    for table in _DIRECT_ORG_TABLES + _SUBQUERY_TABLES:
        op.execute(f"DROP POLICY IF EXISTS org_isolation ON {table};")

    # ------------------------------------------------------------------
    # Återskapa policies utan NULL-bypass (0001-semantik)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE POLICY org_isolation ON systems
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (organization_id = current_org_id());
    """)

    op.execute("""
        CREATE POLICY org_isolation ON system_owners
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (organization_id = current_org_id());
    """)

    op.execute("""
        CREATE POLICY org_isolation ON system_classifications
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (
            EXISTS (
                SELECT 1 FROM systems s
                WHERE s.id = system_classifications.system_id
                  AND s.organization_id = current_org_id()
            )
        );
    """)

    op.execute("""
        CREATE POLICY org_isolation ON system_integrations
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (
            EXISTS (
                SELECT 1 FROM systems s
                WHERE s.organization_id = current_org_id()
                  AND (
                      s.id = system_integrations.source_system_id
                   OR s.id = system_integrations.target_system_id
                  )
            )
        );
    """)

    op.execute("""
        CREATE POLICY org_isolation ON gdpr_treatments
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (
            EXISTS (
                SELECT 1 FROM systems s
                WHERE s.id = gdpr_treatments.system_id
                  AND s.organization_id = current_org_id()
            )
        );
    """)

    op.execute("""
        CREATE POLICY org_isolation ON contracts
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (
            EXISTS (
                SELECT 1 FROM systems s
                WHERE s.id = contracts.system_id
                  AND s.organization_id = current_org_id()
            )
        );
    """)
