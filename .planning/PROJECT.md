# Systemregister — Sundsvalls kommunkoncern

**Skapad:** 2026-03-26
**Uppdaterad:** 2026-03-26

---

## Vision

Ett centralt, klassificerat och kontinuerligt underhållet IT-systemregister som ger Sundsvalls kommunkoncern fullständig kontroll över sina informationstillgangar — drivet av NIS2/CSL, ISO 27001, MSB/MCF och GDPR.

## Problem

Sundsvalls kommunkoncern saknar ett strukturerat, samlat register over samtliga informationssystem. Utan detta ar det omojligt att uppfylla Cyberssakerhetslagen (SFS 2025:1506) som tradde i kraft 15 januari 2026. Dokumentation ar utspridd, klassningar saknas eller ar foraldrade, och beroendekartor existerar inte i strukturerad form.

## Malgrupp

| Roll | Behov |
|------|-------|
| **DigIT** (gemensam IT-avdelning) | Tvarganende oversikt over 13+ organisationers systemlandskap |
| **Systemagare/informationsagare** | Registrera, klassificera och underhalla sina system |
| **CISO/sakerhetschef** | NIS2-compliance, riskbild, klassningsstatus |
| **Dataskyddsombud** | GDPR-koppling, PuB-avtal, tredjelandsoverforingar |
| **IT-chefer per organisation** | Portfoljoverblick, kostnader, livscykel |
| **Tillsynsmyndighet** (Lansstyrelsen Norrbotten) | Revisionsbarhet, audit trail |

## Karnfunktioner

1. **Multi-org systemregister** — Varje kommun/bolag/samverkansorgan har egen datadomän med RLS, medan DigIT ser tvars organisationer
2. **Informationsklassning (K/R/T/S)** — MSB-modellen (0-4) med historik, arlig uppfoljning och KLASSA-koppling
3. **Attributmodell (~70 falt, 12 kategorier)** — Alla Skall-attribut som fasta kolumner, Bor-attribut som JSONB
4. **Beroendekartor och integrationer** — Visualisering av systemrelationer (MSBFS 2020:7 krav)
5. **GDPR/ROPA-koppling** — Lankning till behandlingsregister, PuB-avtal, DPIA-status
6. **Audit trail** — Automatisk andringslogg med vem/vad/nar for NIS2 och ISO 27001
7. **Rapporter och dashboards** — KPI:er, compliance-gap, klassningsstatus, NIS2-tillsynsrapporter

## INTE (avgransningar)

- INTE ett behandlingsregister (ROPA) — systemregistret *lankar* till ROPA, ersatter det inte
- INTE ett ITSM-verktyg — inga incident/change/problem-processer
- INTE automatisk discovery — manuell registrering i forsta hand
- INTE ett riskregister — men lankar till riskbedommingar
- INTE sjalva informationsklassningen — KLASSA anvands som komplement, resultaten speglas in

## Regulatoriska drivkrafter

| Regelverk | Krav pa systemregistret |
|-----------|------------------------|
| **CSL/NIS2** (SFS 2025:1506) | Tillgangsforvaltning, klassificering, beroendekartor, livscykel (2 kap. 3 § p.9) |
| **MSBFS 2020:7** Kap 2 §4 | Hard/mjukvara, beroenden, utokat skyddsbehov, verksamhetskritikalitet |
| **MSBFS 2020:6** §6 | K/R/T-klassning med konsekvensniva, arlig uppfoljning |
| **ISO 27001:2022** | A.5.9 (tillgangsforteckning), A.5.12 (klassificering), A.5.14 (datafloden), A.5.30 (BCM) |
| **GDPR** Art. 30 | Koppling till behandlingsregister, PuB-avtal, tredjelandsoverforing |

## Tekniska val

| Komponent | Val | Motivering |
|-----------|-----|------------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (async) | Mogen stack, bra for API-first |
| Databas | PostgreSQL 16 med RLS | Multi-org dataisolering pa databasniva |
| Migrationer | Alembic | Standard for SQLAlchemy |
| Frontend | React 18, TypeScript, Vite, shadcn/ui | Modern, tillganglig (WCAG 2.1 AA) |
| Auth | OIDC (Authentik/Keycloak) | SSO-krav, RBAC |
| Deploy | k3s, Flux CD, Kustomize, SOPS/age | Befintlig infrastruktur |
| API-format | REST, OpenAPI 3.x | Integrationskrav, Metakatalogen-kompatibel |

## Attributmodell — 12 kategorier

| # | Kategori | Antal attribut | Prioritet |
|---|----------|---------------|-----------|
| 1 | Grundlaggande identifiering | 8 | Fas 1 |
| 2 | Agarskap och ansvar | 7 | Fas 1 |
| 3 | Informationsklassning och sakerhet | 12 | Fas 1 |
| 4 | Personuppgiftsbehandling/GDPR | 11 | Fas 2 |
| 5 | Driftmiljo och teknisk plattform | 7 | Fas 3 |
| 6 | Livscykel och status | 6 | Fas 1 |
| 7 | Integrationer och beroenden | 5 | Fas 2 |
| 8 | Avtal och leverantorer | 7 | Fas 2 |
| 9 | Backup, kontinuitet och DR | 6 | Fas 3 |
| 10 | Kostnader och ekonomi | 4 | Fas 3 |
| 11 | Dokumentation och sparbarhet | 4 | Fas 3 |
| 12 | Regelefterlevnad och risk | 5 | Fas 1 |

## Fas-plan

### Fas 1 — Datamodell + API (PAGAENDE)
Kategori 1-3, 6, 12. Svarar pa: "Vilka system har vi, vem ager dem, hur kritiska ar de?"
- SQLAlchemy-modeller, Alembic, CRUD, Docker Compose
- Sok/filter, audit trail, grundlaggande tester

### Fas 2 — GDPR, beroenden och avtal
Kategori 4, 7, 8. Skapar ROPA-koppling och leveranskedjespårbarhet.
- Informationsklassning med historik
- Agarskapshantering (roller)
- Multi-org RLS
- Import/export (Excel, CSV, JSON)
- Systemintegrationer/beroenden

### Fas 3 — Frontend
React-app med systemlista, detaljvy, dashboard och beroendekarta.

### Fas 4 — GDPR + compliance-fordjupning
Kategori 9-11. ROPA-koppling, PuB-tracking, NIS2-rapporter, PDF/Excel-export.

### Fas 5 — K8s deploy
Dockerfile, Kustomize, Flux, Traefik, SOPS, CronJob backup.

## Framgangskriterier

- [ ] Alla system i kommunkoncernen registrerade med karnattribut (fas 1-attribut)
- [ ] K/R/T-klassning genomford for samtliga system
- [ ] Beroendekartor tillgangliga for alla kritiska system
- [ ] Multi-org RLS verifierad — varje organisation ser enbart sina system
- [ ] GDPR-koppling pa plats (varje system lankat till ROPA-poster)
- [ ] Audit trail uppfyller NIS2-krav pa revisionsbarhet
- [ ] WCAG 2.1 AA-godkant granssnitt pa svenska
- [ ] Integrerat med befintlig API-infrastruktur (Metakatalogen)
- [ ] Klarar 500-1000 systemregisterposter med god prestanda

## Sundsvallsspecifika forutsattningar

- **DigIT** betjanar 13+ politiskt styrda organisationer — multi-org ar kritiskt
- **Metakatalogen** (sedan 2007) — masterdata-register med REST/WCF-API:er
- **182+ open source-repos pa GitHub** — "oppna som standard"
- **Servicecenter IT** — ca 75-80 medarbetare, ~7 500 anvandare
- **Samverkan** med Hudiksvall, Ange, Nordanstig, Ljusdal
- **KLASSA v5** (mars 2025) — obligatoriskt komplement, referens-ID i systemregistret
- **Sanktionsavgift**: upp till 10 MSEK vid bristande NIS2-efterlevnad
