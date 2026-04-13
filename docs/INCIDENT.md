# Incidenthantering — Systemregister

## Klassificering

| Prioritet | Beskrivning | Responstid | Exempel |
|-----------|-------------|------------|---------|
| P1 | Kritisk — tjänsten nere | < 1 timme | Databasen oåtkomlig, deployment kraschad |
| P2 | Hög — funktionalitet allvarligt påverkad | < 4 timmar | Kan inte skapa/uppdatera system, dataförlust |
| P3 | Medel — funktion degraderad | < 1 arbetsdag | Långsam responstid, enstaka fel |
| P4 | Låg — kosmetiskt eller planerat | Nästa sprint | UI-bugg, dokumentationsfel |

## Eskalationsväg

1. Upptäck problemet (monitoring, användarrapport, deploy-logg)
2. Klassificera (P1-P4)
3. P1/P2: Kontakta projektansvarig omedelbart
4. P3/P4: Skapa GitHub issue med rätt label

## Post-mortem-mall

Använd efter P1/P2-incidenter:

```markdown
# Post-mortem: [Kort beskrivning]

**Datum:** YYYY-MM-DD
**Varaktighet:** HH:MM — HH:MM
**Prioritet:** P1/P2
**Ansvarig:** [Namn]

## Sammanfattning
[1-2 meningar om vad som hände]

## Tidslinje
- HH:MM — Problemet upptäcktes
- HH:MM — Rotorsak identifierad
- HH:MM — Fix deployad
- HH:MM — Tjänsten återställd

## Rotorsak
[Teknisk beskrivning]

## Åtgärder
- [ ] Kortsiktig fix (redan gjord)
- [ ] Långsiktig fix (planerad)
- [ ] Förebyggande åtgärd

## Lärdomar
[Vad kan vi göra bättre nästa gång?]
```

## Vanliga issues

### Databaskoppling misslyckas

**Symptom:** `ConnectionRefusedError` eller `OperationalError` i loggar

**Checklista:**
1. Kontrollera att Postgres körs: Dokploy UI -> Database
2. Verifiera `DATABASE_URL` i Environment
3. Kontrollera att nätverket mellan app och DB är korrekt
4. Kör `alembic current` for att verifiera schema-status

### Deployment misslyckas

**Symptom:** Rött bygge i Dokploy

**Checklista:**
1. Läs build-loggar i Dokploy UI
2. Vanliga orsaker:
   - TypeScript-kompileringsfel (saknade importer, typfel)
   - Python-paket som inte går att installera
   - Dockerfile-syntax
3. Fixa lokalt, pusha, ny deploy triggas automatiskt

### Migrationsfel vid uppstart

**Symptom:** Container startar men kraschar direkt med Alembic-fel

**Checklista:**
1. Läs runtime-loggar i Dokploy
2. Kolla om migrationen kräver manuell åtgärd (enum-ändring, data migration)
3. Vid behov: rollback deployment i Dokploy, fixa migrationen, pusha igen
4. Se `docs/MIGRATIONS.md` for detaljer

### Frontend visar tomt / 404

**Symptom:** Webbsidan laddas men visar inget innehåll

**Checklista:**
1. Kontrollera att Nginx serverar `/index.html` (SPA-routing)
2. Verifiera `ALLOWED_ORIGINS` i backend (CORS)
3. Kolla browser console for CORS- eller nätverksfel
4. Testa API direkt: `curl /api/v1/health`
