# Verksamhetsskikt + rollkatalog i systemregistret

Sammanfattning för Petronella (verksamhetsarkitekt) och Maria (HR/IT-samordning), 2026-04-30.

## Vad som har byggts

Systemregistret har fått tre nya lager utöver det befintliga system- och informationsskiktet. Allt är tillgängligt via API och frontend, isolerat per organisation (RLS), audit-loggat och multi-tenant.

### 1. Verksamhetsskikt (Paket A)

| Entitet | Vad det är | Hierarkisk |
|---|---|---|
| Förmåga (`capability`) | ArchiMate Capability — det organisationen *kan* göra | Ja (parent/child) |
| Process (`process`) | Operativa flöden — det organisationen *gör* | Ja (huvud-/delprocess) |
| Värdeström (`value_stream`) | Namngivna kund/medborgar-resor med ordnade etapper | Nej (etapper i JSONB) |
| Organisationsenhet (`org_unit`) | Förvaltning/avdelning/enhet | Ja |

Förmågor och processer kan kopplas mot **system** (vilket system stöder vad) och **informationsmängder** (vad processerna konsumerar/producerar).

UI: nya menygrupper "Verksamhet" med listvyer + detaljvyer per entitet. Trädvyn för organisationsenheter visar förvaltning → avdelning → enhet visuellt.

### 2. Diagramgenerering (Paket B)

- **Mermaid** — fem endpoints som returnerar `text/plain` Mermaid-källkod. Renderas live i en `/diagrams`-vy där du kan välja typ + entitet och få SVG direkt. Du kan klistra in koden i Obsidian eller GitHub-issues.
  - `capability-map.mmd` — förmågehierarki + N stödjande system per förmåga
  - `system-landscape.mmd` — alla system grupperade per kategori med integrationer
  - `process-flow/{id}.mmd` — process + delprocesser + system + informationsmängder
  - `value-stream/{id}.mmd` — etapper som horisontellt flöde
  - `context/{system_id}.mmd` — ett systems integrationer in/ut

- **ArchiMate Open Exchange** — `/export/archimate.xml?organization_id=...` ger XML enligt 3.0/3.1-schemat. Importerar i Archi, Sparx EA och 2C8 via plugin. Innehåller `ApplicationComponent` (system), `Capability`, `BusinessProcess`, `DataObject` (informationsmängd) och `BusinessActor` (org-enhet) plus `Realization`/`Serving`/`Access`/`Composition`-relationer.

- **2C8-export** — eftersom `.bmt`-formatet kräver 2C8:s eget Java/OSGi-plugin har vi byggt det "broadcast"-format 2C8 stödjer manuellt: ett zip-paket med `objects.xlsx` + `relationships.xlsx` + en `README.txt` med importinstruktioner. Du kan exportera ett uppdaterat paket från registret och köra om importen i 2C8 när datat förändras — registret är källan, 2C8 visualisationen.

### 3. Rollkatalog (Paket C — IGA)

| Entitet | Användning |
|---|---|
| Verksamhetsroll | Semantisk roll, t.ex. "Bygglovshandläggare". Kopplas till system med läs/skriv/admin + grundbehörighet/villkorad/manuell. |
| Befattning | HR-koppling — titel + befattningskod + organisationsenhet |
| Anställningsmall | Paket av roller per befattning. Versionerade. |
| Roll-åtkomst (`role-access`) | Specifik (roll, system, nivå, typ)-tripel |

**Hjärtat**: `GET /employment-templates/{id}/resolved-access` deduplicerar alla roller i mallen. Vid överlapp på samma system: högsta nivån vinner; vid blandade typer: birthright > conditional > manual. CSV-export via `/resolved-access.csv` ger IT-samordnaren det "beställningsdokument" som ska gå till MIM/Entra ID.

## Demo-data

Kör `docker compose exec backend python -m scripts.seed_sundsvall` för ett komplett, sammanhållet utsnitt av Sundsvalls verksamhet — 8 organisationer (kommun + bolag), 21 organisationsenheter under Sundsvall, 26 förmågor i två nivåer, 14 processer (varav 2 huvud-/delprocess-relationer), 3 värdeströmmar, 18 verkliga system, 15 integrationer, 8 informationsmängder med K/R/T-värden, 11 verksamhetsroller och 5 anställningsmallar med default-roller.

Efter seedning kan du:

1. Öppna `/diagrams` i webbappen, välja "Förmågekarta", välja "Sundsvalls kommun" och se alla toppförmågor + underförmågor live-renderade.
2. Öppna `/diagrams` igen, välja "Process-flöde" → "Bygglovshantering" och se ByggR + Public 360 + Bygglovsärenden i samma diagram.
3. Hämta `/employment-templates/<bygglovshandläggar-mallen>/resolved-access.csv` och få CSV-listan över system + nivåer.
4. Hämta `/export/2c8/full-package.zip?organization_id=<sundsvall>` och importera i 2C8 Modeling Tool för att rita egna vyer.

## Vad det löser

Petronella behöver inte längre underhålla Sparx EA-modellen separat. Datamodellen är nu i registret, och 2C8/Archi/Sparx EA är visualiseringslager som kan re-importera när datat ändras.

Maria/HR kan beställa "AID-handläggare på Socialförvaltningen" från en mall och få exakt det paket som ska konfigureras i MIM. Vi bygger inte en provisioneringsmotor — registret berättar *vad* som ska beställas, MIM/Entra ID utför *själva* provisioneringen.

## Nästa steg (utanför scope för denna leverans)

- 2C8 Extension Framework-plugin (Java/OSGi) som anropar registrets API direkt — eliminerar manuell importprocess. Kräver separat Java-utvecklingsinsats.
- OIDC-integration mot Authentik (Fas 7) — då försvinner X-Organization-Id-headern och vi kan logga `changed_by`/`ip_address` i audit_log korrekt.
- Provisioneringsbrygga från `resolved-access` direkt till MIM/Entra ID — kräver MIM-API-kontrakt.

## Frågor under arbetet

Eventuella frågor är dokumenterade i `QUESTIONS.md` på branchen `feature/business-architecture-iga`. Pull request öppnas så fort acceptanstesterna är gröna.

— Håkan Simonsson, DigIT
