# Backlog — framtida insatser

Objekt som identifierats men medvetet lagts utanför scope.

## 2C8 Extension Framework-plugin

`.bmt`-formatet kräver 2C8:s eget Java/OSGi-plugin-ramverk. Att skriva `.bmt` direkt från Python är inte realistiskt. Tills detta plugin är byggt använder vi den manuella Excel-import 2C8 redan stödjer (se `/api/v1/export/2c8/full-package.zip`).

**Åtgärd**: starta separat Java-projekt med 2C8 Extension Framework SDK. Pluginet ska anropa registrets API direkt via HTTP/JSON och bygga `.bmt`-objekt internt. Kräver:
- Java-utvecklingskompetens (förvaltningsnivå).
- Access till 2C8 Extension Framework dokumentation.
- Egen utvecklingscykel (~3 månaders insats inkl. förvaltning).

## Provisioneringsbrygga MIM/Entra ID

`/employment-templates/{id}/resolved-access` ger det åtkomstpaket som ska beställas. Idag exporteras det som CSV och en människa skapar order i MIM. En automatiserad brygga skulle:

- Lyssna på beställningsevent (kanske via webhook).
- Mappa registrets system-ID:n till MIM-systemnamn.
- Skicka konfigurationsorder via MIM:s eget API.

**Förutsättningar**: stabilt MIM-API-kontrakt + namespacing-strategi. Kräver också Fas 7 (auth/audit-spårbarhet) först.

## OIDC-fas (Fas 7)

Befintlig backlog-post. Tar bort X-Organization-Id-headern, ger korrekt `changed_by` i audit-logg, och möjliggör per-roll-RBAC som kan kopplas mot rollkatalogen i Paket C.

## Standardisera RLS-policy-namn

Befintliga tabeller använder `org_isolation`. Nya (Paket A+C) använder `tenant_isolation_<table>` enligt prompt-instruktion. Migration som standardiserar till en namnkonvention vore lämpligt under Fas 7.

## Bör-attribut för rollkatalog

Just nu: enkel (system, level, type). Möjliga utbyggnader (utan att starta nu):
- Tidsbegränsade åtkomster (`access_until`)
- Approvals-flöde för "villkorad"/"manuell" via befintliga `approvals`-tabellen
- Spårning av faktisk provisionering vs. planerad (drift-detektering)
