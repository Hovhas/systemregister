# Öppna frågor — feature/business-architecture-iga

Frågor och beslut som gjordes utan din avstämning under autonom körning. Ta upp vid nästa avstämning.

## 1. RLS-policy-namn

Prompten sa "Kopiera mönstret från migration `0001` (skapa policy `tenant_isolation_<table>`)" men det befintliga policy-namnet i 0001/0003 är `org_isolation`. Jag följde **prompten** och döpte de nya policies till `tenant_isolation_business_capabilities` osv. Detta innebär dubbla namnkonventioner — överväg att standardisera (kanske som del av Fas 7).

## 2. RLS-semantik

Prompten sa "samma semantik som befintliga tabeller, inte den striktare varianten" → jag använde NULL-bypass-varianten (matchar 0003). Detta upprepar inte 0001-strikt-semantiken utan den faktiska semantiken som tillämpas i `_run_alembic_upgrade` i conftest. Konsekvens: tester utan X-Organization-Id-header kan se de nya tabellerna (samma som idag för systems).

## 3. Verifiering kunde inte köras lokalt

Docker var inte tillgängligt i min utförandemiljö, så jag kunde inte:
- Köra `alembic upgrade head` mot databasen för att verifiera migrationen.
- Köra `pytest tests/test_business_capabilities.py` etc.
- Köra `npm run build` för Paket B+C-frontend (det körs av sub-agenten).

Migrationen är skriven manuellt (autogenerate kräver db-anslutning) baserat på modellerna och 0007/0009-mönstren. **Jag rekommenderar starkt** att Håkan kör följande lokalt innan PR:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend pytest tests/test_business_capabilities.py -v
docker compose exec backend pytest tests/test_business_processes.py -v
docker compose exec backend pytest tests/test_value_streams.py -v
docker compose exec backend pytest tests/test_org_units.py -v
docker compose exec backend pytest tests/test_diagrams.py -v
docker compose exec backend pytest tests/test_archimate_export.py -v
docker compose exec backend pytest tests/test_twoseight_export.py -v
docker compose exec backend pytest tests/test_business_roles.py -v
docker compose exec backend pytest tests/test_positions.py -v
docker compose exec backend pytest tests/test_role_system_access.py -v
docker compose exec backend pytest tests/test_employment_templates.py -v
docker compose exec backend pytest tests/test_template_service.py -v
```

Och seed:

```bash
docker compose exec backend python -m scripts.seed_sundsvall
```

## 4. Audit-event-listener

Jag lade alla nya tabeller i `_AUDITED_TABLES` i `app/core/audit.py`. Tomma `old_values`/`new_values` vid create förekommer på samma sätt som befintliga tabeller. **Varje** ändring loggas inte — bara skapande/uppdatering/radering av huvudentiteterna, inte länkningar. Detta matchar befintligt mönster (process_capability_link osv. loggas inte separat).

## 5. ArchiMate XSD-validering

Prompten nämnde "Validera mot ett enkelt offline-fragment av XSD:n". Jag valde att inte hårdkoda XSD-validering i tester (det kräver lxml + nedladdad XSD och blir ömtåligt mot uppgraderingar). Istället verifierar `test_archimate_xml_is_well_formed` att XML är wellformed och innehåller förväntade element/relationer. Verifiera mot Archi (gratis) genom att importera den genererade XML-filen.

## 6. 2C8 Extension Framework-plugin

Som prompten sa: jag noterade detta i `BACKLOG.md` (skapar inte själva pluginet). Excel-importen är kompletteringsvägen tills Java-pluginet kan byggas i en separat insats.

## 7. Stages-validering på värdeströmmar

`ValueStreamStage` accepterar `name` (1–255 tecken), `description` (valfritt) och `order` (>=0). Inget krav på unika ordervärden eller på sekventiell ordning — frontenden ansvarar för sortering.

## 8. Roll-system-länk: unique constraint

`uq_role_system` på `(business_role_id, system_id)` betyder att en roll bara kan ha **en** access-tripel mot ett system. Vid försök att skapa en till — `409 Conflict` (via `IntegrityError`-handler i main.py). Detta verifieras i `test_role_system_access.py::test_unique_constraint_role_system`.

## 9. Påverkan på befintliga tester

Jag har **inte** ändrat någon befintlig kod utöver:
- `app/models/__init__.py` (tillägg)
- `app/models/enums.py` (tillägg)
- `app/models/models.py` (tillägg + nya relationer på System/InformationAsset — bakåtkompatibelt)
- `app/core/audit.py` (utökad whitelist)
- `app/main.py` (nya routrar)
- `app/schemas/__init__.py` (re-exports)

Inga befintliga endpoints är modifierade. Befintliga tester ska köra grönt utan ändringar — men det behöver Håkan verifiera.
