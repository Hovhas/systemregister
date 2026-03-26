"""enable_rls_multi_org

Revision ID: 0001
Revises:
Create Date: 2026-03-26

Aktiverar Row-Level Security (RLS) för multi-org isolering.
Varje organisation ser bara sina egna system och relaterad data.
DigIT-superadmin-rollen (systemregister_admin) bypasses RLS.

Tabeller som skyddas:
  - systems                  (direkt organization_id)
  - system_owners            (direkt organization_id)
  - system_classifications   (via systems.organization_id)
  - system_integrations      (via source eller target system)
  - gdpr_treatments          (via systems.organization_id)
  - contracts                (via systems.organization_id)
"""
from alembic import op

# revision identifiers
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Hjälpfunktion: set_org_context(org_id)
    #    Anropas av applikationskoden för att sätta context per request.
    #    Använder SET LOCAL så värdet nollställs automatiskt vid
    #    transaktionsslut.
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION set_org_context(p_org_id UUID)
        RETURNS void
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        BEGIN
            PERFORM set_config('app.current_org_id', p_org_id::text, true);
        END;
        $$;
    """)

    # ------------------------------------------------------------------
    # 2. Hjälpfunktion: current_org_id()
    #    Returnerar NULL (inte ett ogiltigt UUID) om inget context är satt.
    #    Policies jämför mot denna — NULL matchar aldrig, dvs default deny.
    # ------------------------------------------------------------------
    op.execute("""
        CREATE OR REPLACE FUNCTION current_org_id()
        RETURNS UUID
        LANGUAGE plpgsql
        STABLE
        AS $$
        DECLARE
            v_setting text;
        BEGIN
            v_setting := current_setting('app.current_org_id', true);
            IF v_setting IS NULL OR v_setting = '' THEN
                RETURN NULL;
            END IF;
            RETURN v_setting::UUID;
        EXCEPTION WHEN others THEN
            RETURN NULL;
        END;
        $$;
    """)

    # ------------------------------------------------------------------
    # 3. systems — direkt organization_id
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE systems ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE systems FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY org_isolation ON systems
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (organization_id = current_org_id());
    """)

    # ------------------------------------------------------------------
    # 4. system_owners — har direkt organization_id
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE system_owners ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE system_owners FORCE ROW LEVEL SECURITY;")

    op.execute("""
        CREATE POLICY org_isolation ON system_owners
        AS PERMISSIVE
        FOR ALL
        TO PUBLIC
        USING (organization_id = current_org_id());
    """)

    # ------------------------------------------------------------------
    # 5. system_classifications — via systems.organization_id
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE system_classifications ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE system_classifications FORCE ROW LEVEL SECURITY;")

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

    # ------------------------------------------------------------------
    # 6. system_integrations — matcha source ELLER target
    #    En integration är synlig om den berör ett system som tillhör org.
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE system_integrations ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE system_integrations FORCE ROW LEVEL SECURITY;")

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

    # ------------------------------------------------------------------
    # 7. gdpr_treatments — via systems.organization_id
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE gdpr_treatments ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE gdpr_treatments FORCE ROW LEVEL SECURITY;")

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

    # ------------------------------------------------------------------
    # 8. contracts — via systems.organization_id
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE contracts ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE contracts FORCE ROW LEVEL SECURITY;")

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

    # ------------------------------------------------------------------
    # 9. Superadmin-roll: BYPASSRLS
    #    Rollen systemregister_admin existerar sedan init-db.sql (den
    #    databas-användare applikationen kör som i produktion).
    #    I Docker Compose-dev är rollen "systemregister" — vi ger BYPASS
    #    på den rollen också så att dev-miljön fungerar utan context.
    #
    #    OBS: ALTER ROLE kräver superuser i PostgreSQL. I Docker-compose
    #    kör init-db.sql redan som superuser, men Alembic körs som
    #    systemregister. Vi hanterar detta med DO-block + exception catch
    #    så att migrationen inte kraschar i dev men lyckas i prod.
    # ------------------------------------------------------------------
    op.execute("""
        DO $$
        BEGIN
            -- Skapa admin-rollen om den inte finns (produktion)
            IF NOT EXISTS (
                SELECT 1 FROM pg_roles WHERE rolname = 'systemregister_admin'
            ) THEN
                CREATE ROLE systemregister_admin;
            END IF;

            ALTER ROLE systemregister_admin BYPASSRLS;
        EXCEPTION WHEN insufficient_privilege THEN
            RAISE NOTICE
                'Kunde inte sätta BYPASSRLS på systemregister_admin — '
                'kräver superuser. Kör manuellt i produktion.';
        END;
        $$;
    """)


def downgrade() -> None:
    # Policies och RLS
    for table in [
        "contracts",
        "gdpr_treatments",
        "system_integrations",
        "system_classifications",
        "system_owners",
        "systems",
    ]:
        op.execute(f"DROP POLICY IF EXISTS org_isolation ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    # Hjälpfunktioner
    op.execute("DROP FUNCTION IF EXISTS set_org_context(UUID);")
    op.execute("DROP FUNCTION IF EXISTS current_org_id();")
