# Lessons learned — Paket A+B+C-leverans, 2026-04-29

Sammanställning efter en stor leverans (verksamhetsskikt, diagram + export, IGA/rollkatalog, Sundsvall-seed) som fungerade i grunden men hade flera ojämna passager mot produktion. Tio konkreta lärdomar med förebyggande åtgärder.

## Sammanfattning

| Vad | Status |
|---|---|
| Backend (52 nya endpoints, 11 nya tabeller, RLS-policies) | Live |
| Frontend (12 nya sidor + DiagramsPage med Mermaid + 2C8/ArchiMate-export) | Live |
| Sundsvall-seed (8 org, 21 enheter, 26 förmågor, 14 processer, 22 system, 22 roll-åtkomster …) | Körd, DB fylld |
| Tre prod-incidenter under leveransen | Alla åtgärdade samma dag |

**Tre P1-incidenter under leveransen** — alla orsakade av brister jag som AI-assistent skapade och som förebyggande åtgärder hade kunnat fånga uppströms.

## Tidslinje

| Tid | Händelse |
|---|---|
| 09:38 | PR #3 mergad till master → Dokploy auto-deploy |
| ~09:55 | Bad Gateway upptäckt på live-appen |
| 10:00 | Rotorsak (alembic dubbel-revision 0010) hittad via runtime-loggar |
| 10:02 | Fix `0010 → 0015` deployad → tjänsten uppe igen |
| 11:00 | Användare upptäcker SelectValue-regression i nya sidor |
| ~11:20 | Konvention dokumenterad i CLAUDE.md + 17 ställen fixade |
| ~12:00 | Seed-körning misslyckas i Dokploy: `ModuleNotFoundError: No module named 'scripts'` |
| ~12:15 | `scripts/__init__.py` + Dockerfile-fix deployad |
| ~12:30 | Seed körd, DB fylld |
| ~12:45 | Tredje regression: rollnamnen i mall-detaljen visade UUID. Fix deployad. |

---

## Lärdomar

### 1. Pre-flight: lista **hela** `alembic/versions/`, inte bara början

**Vad gick fel.** Min PR fick `revision = "0010"` eftersom jag bara såg de nio första migrationerna i pre-flight-listingen (jag truncade output med `head`). Master hade redan 0010–0014 (sbom, metakatalog, index, classification timestamp, pg_trgm). Resultat: alembic fick två head-revisioner och vägrade köra → Bad Gateway P1 i produktion.

**Förebyggande.** Vid varje pre-flight: `ls backend/alembic/versions/ | sort -V | tail -3` eller `alembic heads`. Använd `tail` för senaste, inte `head` för första.

### 2. CI-failure ≠ Dokploy-failure (de är frikopplade)

**Vad gick fel.** Jag antog initialt att Bad Gateway berodde på CI som var röd (pip-audit CVE-2026-3219). Men Dokploy bygger imagen oberoende från git, inte från ghcr.io. CI är en separat verifieringsväg som kan vara röd utan att produktionsimagen påverkas — och tvärtom kan Dokploy deploya kod som CI inte hunnit verifiera.

**Förebyggande.** Två separata frågor vid prod-fel:
1. Bygger Dokploys docker-build framgångsrikt? (Build logs)
2. Startar containern utan att krascha? (Application/Runtime logs)

CI-status är en sekundär signal, inte primär.

### 3. `scripts/` är inte i prod-imagen — bara `entrypoint.sh`

**Vad gick fel.** Dockerfilen kopierar `backend/` och separat `scripts/entrypoint.sh` — men inte hela `scripts/`-mappen. Det betyder att:
- `scripts/seed.py` och `scripts/seed_sundsvall.py` finns inte i containern
- README:ns uppmaning att köra `docker compose exec backend python -m scripts.seed` har **aldrig** fungerat i prod (och förmodligen inte heller lokalt eftersom docker-compose mountar bara `./backend:/app`)

**Förebyggande.** Lade till `COPY scripts/{__init__.py,seed.py,seed_sundsvall.py}` + `scripts/__init__.py` i commit `febb53f`. Verifiera vid varje ny script-fil att den faktiskt finns i runtime-imagen (`docker exec <id> ls /app/scripts/`).

### 4. SelectValue-bug: dokumentera konventioner som upprepats

**Vad gick fel.** Base UI:s `<SelectValue placeholder="..." />` (self-closing) visar råvärdet i triggern istället för det visade namnet. Bug fixad i commits `589f719` (2026-04-12) och `2953ea4` (2026-04-14). När jag och sub-agenten skapade nya Select-komponenter återintroducerades buggen på 17 ställen. Konventionen var **inte** dokumenterad i CLAUDE.md eller CONTRIBUTING.md.

**Förebyggande.** Konventionen står nu under "shadcn/ui Select-komponenter" i CLAUDE.md (rad 78–90). Efter varje 2:a fix av samma bug → skriv konventionen i CLAUDE.md eller CONTRIBUTING.md.

### 5. Working directory i Dokploy-terminalen är `/`, inte `/app`

**Vad gick fel.** Användaren körde `python -m scripts.seed_sundsvall` direkt och fick ModuleNotFoundError trots att modulerna fanns i `/app/scripts/`. Default-cwd när man öppnar terminal i Dokploy är `/` — inte WORKDIR från Dockerfilen.

**Förebyggande.** Ge alltid `cd /app && <kommando>` i terminalanvisningar. Eller dokumentera att terminalen behöver `cd /app` först.

### 6. DB-setup-snippet borde vara dedikerad doc, inte migration-kommentar

**Vad gick fel.** Krav på `BYPASSRLS` på `systemregister_admin` och PostgreSQL-extensions (`uuid-ossp`, `pg_trgm`) stod **bara** som kommentar inuti migration `0001_enable_rls_multi_org.py`. Kravet var osynligt för någon som inte läst migrationskoden.

**Förebyggande.** `docs/DATABASE_SETUP.md` skapad med snippet, verifieringsfrågor och felsökning. Länkad från README under "Produktion — engångs-setup av databasen".

### 7. Sub-agent-genererad kod hade dead imports som blockerade CI

**Vad gick fel.** Sub-agenten lämnade kvar 4 oanvända imports (`selectinload`, `InformationAsset`, `RoleSystemAccess`, `typing.Any`). Ruff-check-stegget i CI fallerade. Lokalt kompilerade allt eftersom Python-importer inte behöver vara använda för att lyckas — men ruff är striktare.

**Förebyggande.** Innan commit, kör `cd backend && ruff check .` lokalt. Eller lägg till samma kontroll i pre-commit-hook. När sub-agent används till backend-implementation, instruera den explicit: "Kör ruff check innan du rapporterar klar."

### 8. TanStack Query `enabled`-flagga kan dölja data permanent

**Vad gick fel.** I `EmploymentTemplateDetailPage` hade rolllistan en query med `enabled: addRoleOpen`. Det betyder att rollerna bara hämtades när "Lägg till"-dialogen var öppen — men `roleNameMap` (som bygger på samma data) användes på den alltid synliga listan ovanför. Resultat: UUID visades vid första laddning, namn dök bara upp efter att man öppnat dialogen.

**Förebyggande.** `enabled`-flaggor ska matcha **alla** ställen där datat används, inte bara det till synes självklara. När en query har en lookup-table-roll, sätt `enabled: !!parentData` istället för dialog-styrt.

### 9. Loggning i seed-script: tom sektion ≠ tom data

**Vad gick fel.** Min seed loggar `+ <Klass>: <namn>` via `_get_or_create`. För direkta `db.add(...)` (integrationer, roll-åtkomster) och `db.execute(table.insert())` (länktabeller) finns ingen loggning. När användaren såg `Integrationer:` följt av tomma rader trodde de att inget skapats — det var en presentations-bugg, inte data-bugg. 21 integrationer och 22 roll-åtkomster fanns faktiskt i DB:n.

**Förebyggande.** Logga konsekvent vid varje skapande, inte bara via helpers. Eller skriv en kort räknesammanfattning per sektion vid slutet ("Skapade 15 integrationer, 0 hoppade över").

### 10. Begränsad utförandemiljö → produktion blir testmiljö

**Vad gick fel.** Min utförandemiljö saknar Docker. Jag kunde inte:
- Köra `alembic upgrade head` mot en testdatabas
- Köra `pytest` för att verifiera nya tester
- Verifiera att seed-skriptet fungerar end-to-end

Resultatet: tre P1-incidenter som alla hade fångats av en lokal körning. Användaren fick agera testmiljö i stället.

**Förebyggande.** När utförandemiljön saknar verifieringsmöjligheter:
- Dokumentera bristerna explicit i `QUESTIONS.md` (gjordes)
- Inspektera djupare före push (åtminstone listing av hela versions/, hela Dockerfilen, hela docker-compose.yml)
- Skriv "stage 0"-tester som körs i konsten av en agent som har Docker (t.ex. ultrareview eller QA-agent)

---

## Föreslagna långsiktiga åtgärder

| Åtgärd | Prioritet | Insats |
|---|---|---|
| Pre-commit hook: `ruff check` + `tsc -b` (frontend) | Hög | Liten |
| Migration `0016_standardize_rls_policy_names` (rensa upp `org_isolation` vs `tenant_isolation_*`) | Medel | Medel |
| Flytta hela `scripts/`-mappen till `backend/scripts/` så docker-compose lokalt automatiskt får dem | Medel | Liten |
| Lägg till en GitHub Actions-job som testar `python -m scripts.seed_sundsvall` mot tom DB | Låg | Medel |
| Lägg till `pip-audit --ignore-vuln CVE-2026-3219` med kommentar i CI:s build.yaml så CI blir grön igen | Låg | Liten |
| Skriv `CONTRIBUTING.md`-checklista för "ny migration" som inkluderar `alembic heads`-kontroll | Hög | Liten |
| `useEffect`-styrd query för data som används utanför dialog (`enabled: !!parentData`-policy) som lint-rule eller code review-checklista | Låg | Medel |

---

*Skriven av Claude Opus 4.7 efter leveransen. Användaren agerade snabbt och tålmodigt vid varje incident — utan det hade leveransen krävt rollback.*
