# Databas-setup — Systemregister

Engångskonfiguration som måste göras **manuellt** mot produktionsdatabasen.
Lokal Docker-Compose-utveckling sköter detta automatiskt via
`scripts/init-db.sql` och Postgres-bilden.

## När gäller detta?

Kör snippeten nedan **en gång** efter att Postgres-instansen i Dokploy
skapats för första gången, **eller** om en ny Postgres-instans tas i bruk.
Den är idempotent — säker att köra om.

## Snippet (kör som Postgres-superuser)

```sql
-- 1. Extensions som applikationen kräver
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- 2. Superadmin-roll med BYPASSRLS för administrativa endpoints
--    (DigIT-personal som ser alla organisationer)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'systemregister_admin') THEN
        CREATE ROLE systemregister_admin;
    END IF;
END $$;
ALTER ROLE systemregister_admin BYPASSRLS;
```

## Hur kör jag den?

### Via Dokploy-terminal

1. Öppna Dokploy → **Database** → välj systemregister-Postgres
2. Klicka på **Console** / **Terminal** för att få en `psql`-session som
   superuser (vanligtvis rollen `postgres`)
3. Klistra in snippeten ovan

### Via `psql` lokalt mot Dokploys Postgres

Om du har `DATABASE_URL` med en superuser-roll till hands:

```bash
psql "$DATABASE_URL_SUPERUSER" -f scripts/init-db.sql
psql "$DATABASE_URL_SUPERUSER" <<'SQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'systemregister_admin') THEN
        CREATE ROLE systemregister_admin;
    END IF;
END $$;
ALTER ROLE systemregister_admin BYPASSRLS;
SQL
```

## Varför Alembic inte gör detta automatiskt

`ALTER ROLE ... BYPASSRLS` kräver superuser-behörighet. Alembic-migrationerna
körs i produktion som applikationsrollen (oftast `systemregister`), som
**inte** är superuser. Migration `0001_enable_rls_multi_org.py` försöker
göra detta i ett `EXCEPTION WHEN insufficient_privilege`-block och loggar
en `NOTICE` om det inte lyckas — appen kraschar inte, men RLS-bypass för
admin-rollen fungerar inte förrän snippeten körs manuellt.

## Verifiering

```sql
-- Extensions
SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'pg_trgm');
-- Förväntat: båda två returneras

-- Roll med BYPASSRLS
SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname = 'systemregister_admin';
-- Förväntat: rolbypassrls = true
```

## Felsökning

| Symptom | Trolig orsak | Åtgärd |
|---|---|---|
| `function uuid_generate_v4() does not exist` vid INSERT i nya tabeller | uuid-ossp saknas | Kör `CREATE EXTENSION` ovan |
| ILIKE-sökningar långsamma | pg_trgm saknas | Kör `CREATE EXTENSION` ovan |
| DigIT-superadminvy returnerar 0 rader trots data | `systemregister_admin` saknar BYPASSRLS | Kör `ALTER ROLE ...` ovan |
| `permission denied for table xxx` vid migration | Applikationsrollen saknar `GRANT ALL ON SCHEMA public` | `GRANT ALL ON SCHEMA public TO <approll>` |
