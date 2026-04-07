# HANDOVER — Systemregister

**Datum:** 2026-04-07
**Från:** privat utveckling (Hovhas/personlig homelab)
**Till:** jobbets Claude (claude.ai Team/Enterprise) + jobbets förvaltning

Detta dokument är en engångs-överlämning. Läs det, agera på TODO-listan, och radera filen när den är internaliserad.

---

## 1. Vad är detta repo?

Systemregister för Sundsvalls kommunkoncern — multi-org IT-systemregister med NIS2/GDPR/ISO 27001-stöd. Se `CLAUDE.md` för full projektkontext (tech stack, datamodell, konventioner, kommandon).

Repot ligger på `github.com/Hovhas/systemregister` (personlig GitHub). Jobbkontot är collaborator med full access. Repot **flyttas inte** — det stannar på Hovhas/.

---

## 2. Deploy-flöde (NY — Dokploy)

Sedan 2026-04-07 byggs och deployas appen via **Dokploy**:

- **Dokploy-app:** `hakans-systemregister-yuzjf3`
- **Trigger:** Push till `master` på GitHub → Dokploy webhook → Docker-build → live
- **Build:** Multi-stage Dockerfile i repo-roten (backend uv + frontend vite + production stage)
- **URL:** _**TBD**_ — slå upp i Dokploy-UI under appen → Domains. Skriv in här när du vet.
- **Verifiering:** Det finns ingen GitHub Actions CI. Verifieringen är att Dokploy-bygget går igenom + att appen startar (uvicorn-loggar `Application startup complete`).

**Konsekvens:** Tester (pytest, vitest) körs **inte** automatiskt. TS-fel och import-fel fångas av Docker-bygget; runtime-fel och regressioner gör det inte. Om du vill ha CI behöver du sätta upp GitHub Actions separat.

---

## 3. Gammal deploy (K8s/Flux) — TODO: rivs

Tidigare kördes appen även på `systemregister.intern.hovhas.se` via Flux CD i den privata K3s-homelaben. Detta ska **stängas ner** — bara Dokploy gäller framöver. Rivningen är **inte gjord** ännu.

### Filer att ta bort i `k3s-homelab`-repot

| Sökväg | Vad |
|--------|-----|
| `apps/base/systemregister/` | Hela mappen (configmap, deployment, namespace, networkpolicy, postgres-statefulset, service) |
| `apps/overlays/production/systemregister/` | Hela mappen (backup-cronjob, ingress, postgres-secrets, systemregister-secrets) |
| `apps/overlays/production/kustomization.yaml` rad 18 | Ta bort raden `- systemregister` |
| `clusters/homelab/image-policies.yaml` rad 130–134 | Ta bort `name: systemregister` block |
| `clusters/homelab/image-repositories.yaml` rad 91–94 | Ta bort `name: systemregister` block (`image: ghcr.io/hovhas/systemregister`) |

### Steg

1. `cd ~/projekt/k3s-homelab && git checkout -b chore/remove-systemregister`
2. Ta bort filerna ovan
3. `flux suspend kustomization apps -n flux-system` (förhindra reconcile under övergången)
4. Commit + push + PR
5. Efter merge: `flux resume kustomization apps -n flux-system` → Flux städar bort namespace systemregister
6. Verifiera: `kubectl get ns systemregister` ska returnera NotFound
7. Manuell cleanup om något hänger kvar: `kubectl delete ns systemregister --grace-period=0 --force`
8. Ta bort DNS-posten för `systemregister.intern.hovhas.se` (Cloudflare eller intern DNS)
9. TLS-cert (`intern-hovhas-wildcard-tls`) är delad och kan ligga kvar — rör inte

**Detta är en GitOps-operation som tar ner den privata homelab-instansen. Gör det när du är redo, inte panik.**

---

## 4. Secrets — TODO: kartläggs

Status: **blandat / okänt**. Måste kartläggas innan jobbet tar över ägarskap.

### Vad backend förväntar sig (`backend/app/core/config.py`)

| Variabel | Default | Kritiskt? |
|----------|---------|-----------|
| `DATABASE_URL` | localhost dev | **Ja** — måste sättas i Dokploy |
| `DATABASE_URL_SYNC` | localhost dev | **Ja** — Alembic-migrationer |
| `SECRET_KEY` | `"change-me-in-production"` | **JA — säkerhetshål om default kvar** |
| `ENVIRONMENT` | `"development"` | Bör vara `production` i Dokploy |
| `LOG_LEVEL` | `"INFO"` | OK med default |
| `ALLOWED_ORIGINS` | localhost | **Ja** — måste sättas till prod-URL |
| `TRUSTED_PROXY_HOSTS` | privata RFC1918 | Beror på Dokploys nätverk |

### Åtgärder

1. **Logga in i Dokploy-UI** → app `hakans-systemregister-yuzjf3` → Environment
2. **Verifiera att `SECRET_KEY` är satt till ett riktigt random-värde**, inte default. Om default: generera ny (`openssl rand -hex 32`) och rotera.
3. **Verifiera `DATABASE_URL` + `DATABASE_URL_SYNC`** pekar på Dokploys Postgres (eller extern), inte localhost.
4. **Sätt `ENVIRONMENT=production`**.
5. **Sätt `ALLOWED_ORIGINS`** till den faktiska prod-URL:en (när du vet den).
6. **Dokumentera secret-policy** för jobbet — vem roterar, hur ofta, var lagras backup.

Inga secrets ska in i repot. `.env.example` är säker (bara dummy-värden), `.env` är gitignored.

---

## 5. Kända öppna issues

### "Nytt system"-bugg
Enligt anteckningar från 2026-03-27 fanns en bugg i flödet "Skapa nytt system" i frontend. Status oklar — kan vara fixad i en av de senare commitsen (`cf434ac` feat: entitetshierarki, AI-förordning, OWASP-härdning) eller fortfarande öppen. **Verifiera mot live efter att URL är känd.**

### FK-violations ger 500 istället för 422
Från `.planning/STATE.md`: ogiltigt `organization_id` (eller annan FK) returnerar HTTP 500 istället för 422. Bör fångas i exception handler.

### `classified_at` använder transaktionstid
Två klassningar i samma transaktion får identisk timestamp eftersom `func.now()` returnerar transaction start time. Bör bytas till `clock_timestamp()` eller sättas i Python.

### Ingen CI
Inga automatiserade tester körs på PRs. Allt verifieras via Dokploy-bygget (TS + import-validering) — runtime-buggar fångas först när appen startar. Övervägs som framtida förbättring.

---

## 6. Arbetsflöde för jobb-Claude (claude.ai Team)

Jobb-Claude har **inte** lokal terminal. Allt går via:

- **GitHub-connector** — läs/skriv kod, branches, PRs, commits
- **Dokploy-connector** — trigga deploys, läs build-loggar, hantera env-vars

### Vad jobb-Claude kan göra
- Läsa hela kodbasen
- Skapa branches och PRs
- Committa direkt till master (om du tillåter)
- Trigga rebuilds i Dokploy
- Läsa Dockerbygg- och runtime-loggar via Dokploy
- Hantera env-variabler i Dokploy

### Vad jobb-Claude **inte** kan göra
- Köra `pytest` eller `vitest` lokalt
- Köra `docker compose up` lokalt
- Köra `alembic upgrade head` mot lokal DB
- Använda kubectl mot något kluster
- Inspektera filer utanför systemregister-repot

### Praktiskt arbetsflöde

| Uppgift | Hur |
|---------|-----|
| Buggfix (känt rotorsak) | Branch → fix → PR → review → merge → Dokploy bygger → verifiera live |
| Buggfix (okänd) | Läs kod, läs Dokploy-loggar, hypotes, fix på branch, deploy till Dokploy preview om möjligt |
| Ny feature | Branch → kod → PR → merge → deploy. Skriv tester men förvänta dig inte att de körs automatiskt. |
| Migration (Alembic) | Skapa migration på branch, merge → Dokploy startar nya containern → migrationen körs vid startup (om så är konfigurerat — verifiera!) |
| Rollback | Dokploy → rollback to previous deployment |

**Migrations-varning:** Verifiera om Dokploy-deployen kör `alembic upgrade head` automatiskt vid start. Om inte: jobb-Claude måste köra det manuellt via Dokploy-terminal eller motsvarande, annars går schema och kod ur sync.

---

## 7. Kontextfiler i repot

| Fil | Innehåll | Status |
|-----|----------|--------|
| `CLAUDE.md` | Tech stack, arkitektur, UX, datamodell, konventioner | **Kanonisk — läs först** |
| `.planning/PROJECT.md` | Projektmål, omfattning | Historisk men relevant |
| `.planning/STATE.md` | Pågående/klart per fas | **Stale — uppdaterades 2026-03-26**, nyare commits inte reflekterade |
| `.planning/HANDOFF.md` | Tidigare handoff (mellan sessioner) | Historisk |
| `.planning/phases/` | Per-fas planer | Historiska |
| `HANDOVER.md` (denna fil) | Privat → jobb-överlämning | Engångs — radera när läst |

**Rekommendation:** När jobb-Claude har internaliserat denna fil, uppdatera `CLAUDE.md` (rad 12 + 112) som fortfarande nämner K8s/Flux och `intern.hovhas.se`. Byt till Dokploy-info.

---

## 8. Vad som *inte* följer med från privat sida

- **`~/projekt/dev-team1/`** — privat agent-orkestreringsrepo. Inget av det är relevant för systemregister-arbetet.
- **`~/projekt/k3s-homelab/`** — privat homelab. Bara relevant tills K8s/Flux-rivningen är gjord (sektion 3).
- **Lokal `~/projekt/systemregister/`** — arkiveras till `~/projekt/archive/systemregister/` på den privata Macen efter denna överlämning. Existerar inte längre som "aktiv kopia".
- **Privata Claude:s minnesanteckningar** — raderas (inkl. notering om "Nytt system"-bugg, som är dokumenterad här i sektion 5 istället).

---

## 9. TL;DR — vad jobb-Claude ska göra först

1. Läs `CLAUDE.md` (full projektkontext)
2. Läs denna fil (HANDOVER.md)
3. Slå upp prod-URL i Dokploy och skriv in den i sektion 2 ovan + i `CLAUDE.md`
4. Kartlägg secrets (sektion 4) — verifiera att `SECRET_KEY` inte är default
5. Verifiera "Nytt system"-bugg (sektion 5) mot live
6. Stäm av med ägaren när K8s/Flux-rivningen (sektion 3) ska köras
7. Uppdatera `CLAUDE.md` rad 12 + 112 (ersätt K8s/Flux/intern.hovhas.se med Dokploy)
8. Radera `HANDOVER.md` när allt ovan är gjort
