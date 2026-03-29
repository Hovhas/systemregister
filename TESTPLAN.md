# Testplan: Systemregister Sundsvalls Kommunkoncern

**Version:** 1.0
**Datum:** 2026-03-28
**Totalt antal testfall:** 2430 (2003 backend + 427 frontend, per 2026-03-29)
**Regulatorisk grund:** NIS2/CSL, ISO 27001:2022, MSBFS 2020:6/7, GDPR

---

## Testteam (Agenter)

| Roll | Ansvarsområde | Testfiler |
|------|--------------|-----------|
| **Backend QA 1** | Kravspec kat 1-6 (identifiering, ägarskap, klassning, GDPR, drift, livscykel) | `test_kravspec_category1_6.py` |
| **Backend QA 2** | Kravspec kat 7-12 (integrationer, avtal, backup, kostnader, doku, compliance) | `test_kravspec_category7_12.py` |
| **Säkerhetstestare** | Multi-org isolation, RLS, autentisering | `test_multiorg_security.py` |
| **E2E-testare** | Arbetsflöden, livscykelflöden, import/export roundtrip | `test_workflows_e2e.py` |
| **Penetrationstestare** | Gränsfall, injection, fuzzing | `test_edge_cases_security.py` |
| **Frontend QA** | React-komponenter, sidor, formulär, API-klient | `frontend/src/__tests__/` |
| **Compliance-testare** | NIS2, GDPR, ISO 27001, MSBFS datakvalitet | `test_data_quality_compliance.py` |
| **Prestandatestare** | Skalbarhet 500-1000 system, svarstider, concurrent | `test_performance_stress.py` |

---

## Testfall per kategori

### TC-0001 till TC-0300: Kravspec Kategori 1-6 (Attributvalidering)

#### Kat 1: Grundläggande identifiering (TC-0001 till TC-0060)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0001 | Skapa system med alla obligatoriska fält | Skall | P1 |
| TC-0002 | System-ID genereras som unikt UUID | Skall (ITIL) | P1 |
| TC-0003 | Systemnamn sparas korrekt | Skall (ISO 27001 A.5.9) | P1 |
| TC-0004 | Systemnamn med svenska tecken (åäöÅÄÖ) | Skall | P1 |
| TC-0005 | Alternativa namn/alias sparas och söks | Bör | P2 |
| TC-0006 | Beskrivning/syfte sparas (max längd) | Skall (ISO 27001 A.5.9) | P1 |
| TC-0007 | Systemkategori: verksamhetssystem | Skall (ITIL) | P1 |
| TC-0008 | Systemkategori: stödsystem | Skall | P1 |
| TC-0009 | Systemkategori: infrastruktur | Skall | P1 |
| TC-0010 | Systemkategori: plattform | Skall | P1 |
| TC-0011 | Systemkategori: iot | Skall | P1 |
| TC-0012 | Ogiltig systemkategori avvisas (422) | Skall | P1 |
| TC-0013 | Verksamhetsprocess koppling sparas | Bör | P3 |
| TC-0014 | Organisation/ägande organ (organization_id) krävs | Skall (NIS2) | P1 |
| TC-0015 | Ogiltigt organization_id ger 400/422 | Skall | P1 |
| TC-0016 | Verksamhetsområde/sektor sparas | Bör | P2 |
| TC-0017 | business_area med lång sträng | Bör | P3 |
| TC-0018 | Sök system på namn (q-parameter) | Skall | P1 |
| TC-0019 | Sök system på beskrivning | Skall | P1 |
| TC-0020 | Sök system - case insensitive | Skall | P1 |
| TC-0021 | Sök med svenska tecken i sökterm | Skall | P1 |
| TC-0022 | Filtrera på systemkategori | Skall | P1 |
| TC-0023 | Filtrera på organisation | Skall | P1 |
| TC-0024 | Kombinera sök + filter | Skall | P1 |
| TC-0025 | Tom sökning returnerar alla | Skall | P2 |
| TC-0026 | Uppdatera systemnamn (PATCH) | Skall | P1 |
| TC-0027 | Uppdatera beskrivning (PATCH) | Skall | P1 |
| TC-0028 | Uppdatera systemkategori (PATCH) | Skall | P1 |
| TC-0029 | Radera system utan relationer | Skall | P1 |
| TC-0030 | Radera system med kaskad (klassificeringar, ägare) | Skall | P1 |
| TC-0031 | GET system med alla relationer (detail) | Skall | P1 |
| TC-0032 | System med tomt namn avvisas | Skall | P1 |
| TC-0033 | System med null-beskrivning avvisas | Skall | P1 |
| TC-0034 | System med extremt långt namn (>255 tecken) | Skall | P2 |
| TC-0035 | System med emoji i namn | Bör | P3 |
| TC-0036 | System-ID persistent efter uppdatering | Skall | P1 |
| TC-0037 | created_at sätts automatiskt | Skall | P2 |
| TC-0038 | updated_at uppdateras vid PATCH | Skall | P2 |
| TC-0039 | Flera system i samma organisation | Skall | P1 |
| TC-0040 | System i olika organisationer isolerade | Skall | P1 |
| TC-0041 | Lista system med paginering (limit/offset) | Skall | P1 |
| TC-0042 | Paginering: total count korrekt | Skall | P1 |
| TC-0043 | Paginering: sista sidan | Skall | P2 |
| TC-0044 | Paginering: offset > total | Skall | P2 |
| TC-0045 | System med alla fält null (optional) | Bör | P2 |
| TC-0046 | System med alla fält ifyllda | Bör | P2 |
| TC-0047 | Dubblettnamn i samma organisation | Bör | P2 |
| TC-0048 | Samma namn i olika organisationer | Skall | P1 |
| TC-0049 | GET icke-existerande system (404) | Skall | P1 |
| TC-0050 | DELETE icke-existerande system (404) | Skall | P1 |
| TC-0051 | PATCH icke-existerande system (404) | Skall | P1 |
| TC-0052 | Systemnamn med bara whitespace avvisas | Skall | P2 |
| TC-0053 | Systemnamn med null bytes avvisas | Skall (säkerhet) | P1 |
| TC-0054 | Extended attributes (JSONB) sparas | Bör | P2 |
| TC-0055 | Extended attributes: nested objekt | Bör | P3 |
| TC-0056 | Extended attributes: array-värden | Bör | P3 |
| TC-0057 | Extended attributes: null-värden | Bör | P3 |
| TC-0058 | Extended attributes: tomt objekt | Bör | P3 |
| TC-0059 | System returnerar organization_id i response | Skall | P1 |
| TC-0060 | System: aliases-fält sparas som lista/sträng | Bör | P2 |

#### Kat 2: Ägarskap och ansvar (TC-0061 till TC-0110)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0061 | Tilldela systemägare | Skall (ISO 27001) | P1 |
| TC-0062 | Tilldela informationsägare | Skall (MSBFS 2020:6) | P1 |
| TC-0063 | Tilldela systemförvaltare | Skall (PM3) | P1 |
| TC-0064 | Tilldela teknisk_förvaltare | Bör (ITIL) | P2 |
| TC-0065 | Tilldela it_kontakt | Bör (ITIL) | P2 |
| TC-0066 | Tilldela dataskyddsombud | Bör (GDPR) | P2 |
| TC-0067 | Ägare med namn + email + telefon | Skall | P1 |
| TC-0068 | Ägare med bara namn (email/telefon optional) | Skall | P1 |
| TC-0069 | Ägare utan namn avvisas | Skall | P1 |
| TC-0070 | Ogiltig ägarroll avvisas (422) | Skall | P1 |
| TC-0071 | Samma person, olika roller på samma system | Skall | P1 |
| TC-0072 | Samma person, samma roll = unik constraint | Skall | P1 |
| TC-0073 | Lista ägare per system | Skall | P1 |
| TC-0074 | Uppdatera ägare (PATCH) | Skall | P1 |
| TC-0075 | Radera ägare | Skall | P1 |
| TC-0076 | Ägare med organisation_id | Skall | P1 |
| TC-0077 | Ägare till icke-existerande system (404) | Skall | P1 |
| TC-0078 | Radera icke-existerande ägare (404) | Skall | P1 |
| TC-0079 | Email-format validering | Bör | P2 |
| TC-0080 | Telefon-format validering | Bör | P3 |
| TC-0081 | Ägare med svenska tecken i namn | Skall | P1 |
| TC-0082 | System med 10+ ägare | Bör | P2 |
| TC-0083 | Driftleverantör (extern part) via owner role | Skall (NIS2) | P1 |
| TC-0084 | Ägare kaskadraderas med system | Skall | P1 |
| TC-0085 | Ägare: created_at sätts automatiskt | Skall | P2 |
| TC-0086-TC-0110 | Parametriserade kombinationer av alla 6 roller x validering | Skall | P1 |

#### Kat 3: Informationsklassning och säkerhet (TC-0111 till TC-0180)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0111 | Skapa klassificering med K=0, R=0, T=0 | Skall (MSBFS 2020:6) | P1 |
| TC-0112 | Skapa klassificering med K=4, R=4, T=4 | Skall | P1 |
| TC-0113 | K-värde -1 avvisas | Skall | P1 |
| TC-0114 | K-värde 5 avvisas | Skall | P1 |
| TC-0115 | R-värde -1 avvisas | Skall | P1 |
| TC-0116 | R-värde 5 avvisas | Skall | P1 |
| TC-0117 | T-värde -1 avvisas | Skall | P1 |
| TC-0118 | T-värde 5 avvisas | Skall | P1 |
| TC-0119 | Spårbarhet (S) 0-4 sparas | Bör | P2 |
| TC-0120 | Spårbarhet null (valfritt) | Bör | P2 |
| TC-0121-TC-0145 | Alla K/R/T kombinationer (0-4 x 0-4 x 0-4) - parametriserade | Skall | P1 |
| TC-0146 | classified_by krävs | Skall | P1 |
| TC-0147 | classified_at sätts automatiskt | Skall | P2 |
| TC-0148 | valid_until datum (optional) | Bör | P2 |
| TC-0149 | notes-fält med text | Bör | P3 |
| TC-0150 | Historiska klassificeringar (flera per system) | Skall (audit) | P1 |
| TC-0151 | GET /latest returnerar senaste | Skall | P1 |
| TC-0152 | Klassificeringar sorterade nyast först | Skall | P2 |
| TC-0153 | Klassificering till icke-existerande system (404) | Skall | P1 |
| TC-0154 | Verksamhetskritikalitet: låg | Skall (MSBFS) | P1 |
| TC-0155 | Verksamhetskritikalitet: medel | Skall | P1 |
| TC-0156 | Verksamhetskritikalitet: hög | Skall | P1 |
| TC-0157 | Verksamhetskritikalitet: kritisk | Skall | P1 |
| TC-0158 | has_elevated_protection: true/false | Skall (MSBFS 2020:7 §4 p.3) | P1 |
| TC-0159 | has_elevated_protection auto vid K/R/T >= 3 | Skall | P1 |
| TC-0160 | security_protection (säkerhetsskydd): true/false | Skall (SFS 2018:585) | P1 |
| TC-0161 | Kryptering dokumenteras | Bör (NIS2) | P2 |
| TC-0162 | Åtkomstkontroll/behörighetsmodell | Bör (ISO 27001 A.5.15) | P2 |
| TC-0163 | KLASSA-referens-ID sparas | Bör (SKR) | P2 |
| TC-0164 | Datum för senaste klassning sparas | Skall (MSBFS 2020:6 §14) | P1 |
| TC-0165 | Klassificering äldre än 12 mån flaggas | Skall | P1 |
| TC-0166 | NIS2-applicable: true/false | Skall (CSL 2025:1506) | P1 |
| TC-0167 | NIS2-klassificering: väsentlig | Bör | P2 |
| TC-0168 | NIS2-klassificering: viktig | Bör | P2 |
| TC-0169 | NIS2-klassificering: ej_tillämplig | Bör | P2 |
| TC-0170 | Filtrera system på kritikalitet | Skall | P1 |
| TC-0171 | Filtrera system på NIS2 | Skall | P1 |
| TC-0172 | Klassificering kaskadraderas med system | Skall | P1 |
| TC-0173-TC-0180 | Gränsfall: float-värden, strängar i K/R/T | Skall | P1 |

#### Kat 4: Personuppgifter och GDPR (TC-0181 till TC-0230)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0181 | treats_personal_data: true/false | Skall (GDPR Art. 30) | P1 |
| TC-0182 | treats_sensitive_data: true/false (Art. 9) | Skall | P1 |
| TC-0183 | Skapa GDPR-behandling med ropa_reference_id | Skall (Art. 30) | P1 |
| TC-0184 | data_categories som JSONB-lista | Bör | P2 |
| TC-0185 | categories_of_data_subjects | Bör (Art. 30.1(c)) | P2 |
| TC-0186 | legal_basis (samtycke, avtal, etc.) | Bör (GDPR Art. 6) | P2 |
| TC-0187 | data_processor (PuB) namn | Skall (GDPR Art. 28) | P1 |
| TC-0188 | processor_agreement_status: ja | Skall (Art. 28) | P1 |
| TC-0189 | processor_agreement_status: nej | Skall | P1 |
| TC-0190 | processor_agreement_status: under_framtagande | Skall | P1 |
| TC-0191 | processor_agreement_status: ej_tillämpligt | Skall | P1 |
| TC-0192 | sub_processors som JSONB-lista | Bör (Art. 28) | P2 |
| TC-0193 | third_country_transfer: true/false | Skall (GDPR Art. 44-49) | P1 |
| TC-0194 | third_country_transfer_details sparas | Skall | P1 |
| TC-0195 | retention_policy (gallringsregler) | Bör (Art. 5.1(e)) | P2 |
| TC-0196 | dpia_conducted: true/false | Bör (Art. 35) | P2 |
| TC-0197 | dpia_date och dpia_link | Bör | P2 |
| TC-0198 | Lista GDPR-behandlingar per system | Skall | P1 |
| TC-0199 | Uppdatera GDPR-behandling (PATCH) | Skall | P1 |
| TC-0200 | Radera GDPR-behandling | Skall | P1 |
| TC-0201 | GDPR-behandling till icke-existerande system (404) | Skall | P1 |
| TC-0202 | System med personuppgifter utan GDPR = notification | Skall | P1 |
| TC-0203 | Flera GDPR-behandlingar per system | Skall | P1 |
| TC-0204 | GDPR kaskadraderas med system | Skall | P1 |
| TC-0205-TC-0230 | Parametriserade kombinationer av GDPR-fält | Skall | P1-P2 |

#### Kat 5: Driftmiljö och teknisk plattform (TC-0231 till TC-0265)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0231 | hosting_model: on-premise | Skall (ISO 27001 A.5.23) | P1 |
| TC-0232 | hosting_model: cloud | Skall | P1 |
| TC-0233 | hosting_model: hybrid | Skall | P1 |
| TC-0234 | cloud_provider sparas | Bör | P2 |
| TC-0235 | data_location_country (EU-lagring) | Skall (GDPR) | P1 |
| TC-0236 | product_name sparas | Skall (MSBFS 2020:7) | P1 |
| TC-0237 | product_version sparas | Skall | P1 |
| TC-0238-TC-0265 | Parametriserade kombinationer hosting + cloud + land | Skall | P1-P2 |

#### Kat 6: Livscykel och status (TC-0266 till TC-0300)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0266 | lifecycle_status: planerad | Skall (ITIL) | P1 |
| TC-0267 | lifecycle_status: under_inforande | Skall | P1 |
| TC-0268 | lifecycle_status: i_drift | Skall | P1 |
| TC-0269 | lifecycle_status: under_avveckling | Skall | P1 |
| TC-0270 | lifecycle_status: avvecklad | Skall | P1 |
| TC-0271 | Filtrera system på livscykelstatus | Skall | P1 |
| TC-0272 | deployment_date sparas | Bör (ITIL) | P2 |
| TC-0273 | planned_decommission_date | Bör (NIS2) | P2 |
| TC-0274 | end_of_support_date | Bör (NIS2) | P2 |
| TC-0275 | last_reviewed_at uppdateras | Skall (ISO 27001 A.5.9) | P1 |
| TC-0276 | last_reviewed_by sparas | Skall (audit) | P1 |
| TC-0277 | Ogiltig lifecycle_status avvisas | Skall | P1 |
| TC-0278-TC-0300 | Datumvalideringar och livscykelkombinationer | Skall | P1-P2 |

---

### TC-0301 till TC-0600: Kravspec Kategori 7-12

#### Kat 7: Integrationer och beroenden (TC-0301 till TC-0400)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0301 | Skapa integration (source -> target) | Skall (MSBFS 2020:7) | P1 |
| TC-0302 | integration_type: api | Skall | P1 |
| TC-0303 | integration_type: filöverföring | Skall | P1 |
| TC-0304 | integration_type: databasreplikering | Skall | P1 |
| TC-0305 | integration_type: event | Skall | P1 |
| TC-0306 | integration_type: manuell | Skall | P1 |
| TC-0307 | Ogiltig integration_type avvisas | Skall | P1 |
| TC-0308 | data_types sparas | Bör | P2 |
| TC-0309 | frequency sparas | Bör | P2 |
| TC-0310 | description sparas | Bör | P2 |
| TC-0311 | criticality per integration (låg-kritisk) | Bör | P2 |
| TC-0312 | is_external: true med external_party | Skall (MSBFS 2020:7 §4 p.2) | P1 |
| TC-0313 | is_external: false | Skall | P1 |
| TC-0314 | Lista integrationer per system (inbound + outbound) | Skall | P1 |
| TC-0315 | Filtrera integrationer på system_id | Skall | P1 |
| TC-0316 | Filtrera integrationer på type | Skall | P1 |
| TC-0317 | GET enskild integration | Skall | P1 |
| TC-0318 | Uppdatera integration (PATCH) | Skall | P1 |
| TC-0319 | Radera integration | Skall | P1 |
| TC-0320 | Samma system som source och target | Bör | P2 |
| TC-0321 | Cirkulärt beroende (A->B->C->A) | Bör | P2 |
| TC-0322 | Integration med icke-existerande source (404) | Skall | P1 |
| TC-0323 | Integration med icke-existerande target (404) | Skall | P1 |
| TC-0324 | Integration kaskadraderas med system | Skall | P1 |
| TC-0325 | 50+ integrationer per system | Bör | P2 |
| TC-0326-TC-0370 | Parametriserade: alla typer x kritikalitet x is_external | Skall | P1 |
| TC-0371-TC-0400 | Beroendekartor: systemkarta-data, drill-down | Bör (MSBFS 2020:7) | P2 |

#### Kat 8: Avtal och leverantörer (TC-0401 till TC-0470)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0401 | Skapa avtal med supplier_name | Skall (ISO 27001 A.5.19) | P1 |
| TC-0402 | supplier_org_number sparas | Skall (NIS2) | P1 |
| TC-0403 | contract_id_external | Bör | P2 |
| TC-0404 | contract_start/contract_end | Skall (NIS2, LOU) | P1 |
| TC-0405 | contract_end >= contract_start validering | Skall | P1 |
| TC-0406 | contract_end < contract_start avvisas | Skall | P1 |
| TC-0407 | auto_renewal: true/false | Bör | P2 |
| TC-0408 | notice_period_months | Bör | P2 |
| TC-0409 | sla_description | Bör (ITIL) | P2 |
| TC-0410 | license_model varianter | Bör (COBIT) | P2 |
| TC-0411 | procurement_type varianter | Bör (LOU) | P2 |
| TC-0412 | support_level | Bör (ITIL) | P2 |
| TC-0413 | annual_license_cost (SEK) | Bör | P2 |
| TC-0414 | annual_operations_cost (SEK) | Bör | P2 |
| TC-0415 | Negativ kostnad avvisas | Skall | P1 |
| TC-0416 | Noll-kostnad accepteras | Bör | P2 |
| TC-0417 | Stort belopp (100 000 000) | Bör | P3 |
| TC-0418 | Lista avtal per system | Skall | P1 |
| TC-0419 | Uppdatera avtal (PATCH) | Skall | P1 |
| TC-0420 | Radera avtal | Skall | P1 |
| TC-0421 | /contracts/expiring default 90 dagar | Skall | P1 |
| TC-0422 | /contracts/expiring med custom dagar (30) | Bör | P2 |
| TC-0423 | /contracts/expiring med 1 dag | Bör | P2 |
| TC-0424 | /contracts/expiring med 3650 dagar | Bör | P2 |
| TC-0425 | Avtal kaskadraderas med system | Skall | P1 |
| TC-0426 | Avtal till icke-existerande system (404) | Skall | P1 |
| TC-0427-TC-0470 | Parametriserade: alla fält-kombinationer, gränsfall | Skall | P1-P2 |

#### Kat 9: Backup, kontinuitet och DR (TC-0471 till TC-0510)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0471 | backup_frequency sparas | Skall (NIS2, ISO 27001) | P1 |
| TC-0472 | rpo (Recovery Point Objective) | Skall (NIS2) | P1 |
| TC-0473 | rto (Recovery Time Objective) | Skall (NIS2) | P1 |
| TC-0474 | dr_plan_exists: true/false | Bör (NIS2) | P2 |
| TC-0475-TC-0510 | Parametriserade backup-kombinationer | Skall | P1-P2 |

#### Kat 10: Kostnader (TC-0511 till TC-0540)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0511 | annual_license_cost via avtal | Bör (COBIT) | P2 |
| TC-0512 | annual_operations_cost via avtal | Bör | P2 |
| TC-0513-TC-0540 | TCO-beräkning, kostnad per org | Bör | P2-P3 |

#### Kat 11: Dokumentation och spårbarhet (TC-0541 till TC-0580)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0541 | Audit trail: create loggas | Skall (NIS2) | P1 |
| TC-0542 | Audit trail: update loggas med old/new | Skall | P1 |
| TC-0543 | Audit trail: delete loggas | Skall | P1 |
| TC-0544 | Audit: vem (changed_by) | Skall | P1 |
| TC-0545 | Audit: när (changed_at) | Skall | P1 |
| TC-0546 | Audit: filtrering per tabell | Skall | P1 |
| TC-0547 | Audit: filtrering per record_id | Skall | P1 |
| TC-0548 | Audit: paginering | Skall | P2 |
| TC-0549 | Audit per record: fullständig historik | Skall | P1 |
| TC-0550 | last_reviewed_at + last_reviewed_by | Skall (ISO 27001 A.5.9) | P1 |
| TC-0551-TC-0580 | Audit för alla tabeller (7 st) | Skall | P1 |

#### Kat 12: Regelefterlevnad och risk (TC-0581 till TC-0600)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0581 | nis2_applicable flagga | Skall (CSL) | P1 |
| TC-0582 | nis2_classification: väsentlig/viktig/ej_tillämplig | Bör | P2 |
| TC-0583 | last_risk_assessment_date | Skall (ISO 27001, NIS2) | P1 |
| TC-0584 | klassa_reference_id koppling | Bör (SKR) | P2 |
| TC-0585 | Filtrera på NIS2-system | Skall | P1 |
| TC-0586 | Filtrera på GDPR-system | Skall | P1 |
| TC-0587-TC-0600 | Compliance gap-scenarion | Skall | P1 |

---

### TC-0601 till TC-0800: Multi-organisation och säkerhet

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0601 | RLS: Org A ser inte Org B:s system | Skall (multi-tenant) | P1 |
| TC-0602 | RLS: Org A ser inte Org B:s klassificeringar | Skall | P1 |
| TC-0603 | RLS: Org A ser inte Org B:s ägare | Skall | P1 |
| TC-0604 | RLS: Org A ser inte Org B:s GDPR | Skall | P1 |
| TC-0605 | RLS: Org A ser inte Org B:s avtal | Skall | P1 |
| TC-0606 | RLS: Org A ser inte Org B:s integrationer | Skall | P1 |
| TC-0607 | RLS: Org A ser inte Org B:s audit | Skall | P1 |
| TC-0608 | RLS utan X-Organization-Id header | Skall | P1 |
| TC-0609 | RLS med ogiltigt UUID | Skall | P1 |
| TC-0610 | RLS med icke-existerande org | Skall | P1 |
| TC-0611 | RLS: SQL injection i header | Skall (säkerhet) | P1 |
| TC-0612 | RLS: Ändra annan orgs system via PATCH | Skall | P1 |
| TC-0613 | RLS: Radera annan orgs system | Skall | P1 |
| TC-0614 | RLS: Skapa system i annan org | Skall | P1 |
| TC-0615-TC-0650 | 5+ organisationer parallellt - alla endpoints | Skall | P1 |
| TC-0651-TC-0680 | Sök/filter/stats/export per organisation | Skall | P1 |
| TC-0681-TC-0720 | Superadmin (DigIT) tvärgående access | Skall | P1 |
| TC-0721-TC-0750 | Hierarkiska organisationer (parent-child) | Bör | P2 |
| TC-0751-TC-0780 | Org-typer: kommun, bolag, samverkan, digit | Skall | P1 |
| TC-0781-TC-0800 | Organisation CRUD + unik constraint (org_number) | Skall | P1 |

---

### TC-0801 till TC-1000: End-to-end arbetsflöden

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-0801 | Livscykelflöde: planerad -> i_drift (hela kedjan) | Skall | P1 |
| TC-0802 | Livscykelflöde: i_drift -> avvecklad | Skall | P1 |
| TC-0803 | Ogiltiga statusövergångar | Bör | P2 |
| TC-0804-TC-0830 | Fas 1 registreringsflöde: org -> system -> klassificera -> ägare | Skall | P1 |
| TC-0831-TC-0860 | GDPR-flöde: flagga PU -> GDPR-behandling -> PuB-avtal | Skall | P1 |
| TC-0861-TC-0890 | NIS2-complianceflöde: identifiera -> klassificera -> rapport | Skall | P1 |
| TC-0891-TC-0920 | Kontraktsflöde: skapa -> förfall -> notifiering | Skall | P1 |
| TC-0921-TC-0940 | Import/Export roundtrip: Excel -> import -> export -> jämför | Skall | P1 |
| TC-0941-TC-0960 | Import/Export roundtrip: CSV | Skall | P1 |
| TC-0961-TC-0980 | Import/Export roundtrip: JSON | Skall | P1 |
| TC-0981-TC-1000 | Rapportflöden: NIS2 + Compliance gap i alla format | Skall | P1 |

---

### TC-1001 till TC-1250: Gränsfall och säkerhet

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-1001 | Null bytes i alla strängfält (SafeStringMixin) | Skall | P1 |
| TC-1002 | HTML injection: `<script>alert('xss')</script>` | Skall | P1 |
| TC-1003 | SQL injection: `'; DROP TABLE systems; --` | Skall | P1 |
| TC-1004 | Path traversal: `../../etc/passwd` | Skall | P1 |
| TC-1005 | CRLF injection: `\r\n` | Skall | P1 |
| TC-1006-TC-1030 | Unicode: åäö, emoji, CJK, RTL, zero-width | Skall | P1 |
| TC-1031-TC-1050 | Numeriska gränsfall: -1, 0, MAX_INT, float | Skall | P1 |
| TC-1051-TC-1070 | UUID-fält: ogiltigt format, null-UUID, icke-existerande | Skall | P1 |
| TC-1071-TC-1090 | Datum: ogiltigt format, framtiden, förflutet, fel ordning | Skall | P1 |
| TC-1091-TC-1110 | API-säkerhet: Content-Type, stor body, tom body | Skall | P1 |
| TC-1111-TC-1130 | JSONB: djupt nested, stora objekt, specialtecken | Bör | P2 |
| TC-1131-TC-1150 | Konkurrens: samtidig uppdatering, radering under läsning | Bör | P2 |
| TC-1151-TC-1180 | Paginering: offset=0, limit=0, negativ, extrem | Skall | P1 |
| TC-1181-TC-1210 | Import: tom fil, bara headers, 10000 rader, fel filtyp | Skall | P1 |
| TC-1211-TC-1230 | Import: korrupt Excel, fel CSV-delimiter, BOM, encoding | Skall | P1 |
| TC-1231-TC-1250 | Export: 0 system, 1000+ system, alla null, alla fyllda | Skall | P1 |

---

### TC-1251 till TC-1600: Frontend-tester

#### Dashboard (TC-1251 till TC-1290)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-1251 | KPI-kort renderas med korrekta värden | Skall | P1 |
| TC-1252 | Totalt antal system visas | Skall | P1 |
| TC-1253 | NIS2-system count | Skall | P1 |
| TC-1254 | Personuppgifts-system count | Skall | P1 |
| TC-1255 | Kritiska system count | Skall | P1 |
| TC-1256 | Organisation-filter dropdown | Skall | P1 |
| TC-1257 | Filter uppdaterar alla KPI:er | Skall | P1 |
| TC-1258 | Livscykel-statusfördelning tabell | Skall | P1 |
| TC-1259 | Kritikalitetsfördelning tabell | Skall | P1 |
| TC-1260 | Laddningstillstånd (spinner) | Skall | P2 |
| TC-1261 | Feltillstånd (error message) | Skall | P2 |
| TC-1262 | Tom data (inga system) | Skall | P2 |
| TC-1263-TC-1290 | Responsivitet, interaktioner, edge cases | Bör | P2 |

#### Systemlista (TC-1291 till TC-1350)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-1291 | Tabell renderas med systemdata | Skall | P1 |
| TC-1292 | Sökfält med 300ms debounce | Skall | P1 |
| TC-1293 | Sök återställer paginering | Skall | P1 |
| TC-1294 | Filter: systemkategori | Skall | P1 |
| TC-1295 | Filter: livscykelstatus | Skall | P1 |
| TC-1296 | Filter: kritikalitet | Skall | P1 |
| TC-1297 | Kombinerade filter | Skall | P1 |
| TC-1298 | Paginering: 25 per sida | Skall | P1 |
| TC-1299 | Paginering: nästa/föregående | Skall | P1 |
| TC-1300 | Klick på rad -> systemdetalj | Skall | P1 |
| TC-1301 | Kritikalitets-badge: låg = grön | Skall | P2 |
| TC-1302 | Kritikalitets-badge: medel = gul | Skall | P2 |
| TC-1303 | Kritikalitets-badge: hög = orange | Skall | P2 |
| TC-1304 | Kritikalitets-badge: kritisk = röd | Skall | P2 |
| TC-1305 | NIS2-badge | Skall | P2 |
| TC-1306-TC-1350 | Tom lista, laddning, fel, responsivitet | Skall | P1-P2 |

#### Systemdetalj (TC-1351 till TC-1410)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-1351 | 6 tabbar renderas | Skall | P1 |
| TC-1352 | Översikt: alla attribut visas | Skall | P1 |
| TC-1353 | Klassning: CIA-bars 0-4 med färger | Skall | P1 |
| TC-1354 | CIA-bar: röd >= 3, gul = 2, grön < 2 | Skall | P2 |
| TC-1355 | Ägare: alla roller visas | Skall | P1 |
| TC-1356 | Integrationer: lista med typ och riktning | Skall | P1 |
| TC-1357 | Övrigt: extended attributes | Bör | P2 |
| TC-1358 | Ändringslogg: audit timeline | Skall (NIS2) | P1 |
| TC-1359 | Redigera-knapp navigerar | Skall | P1 |
| TC-1360 | Radera-dialog med bekräftelse | Skall | P1 |
| TC-1361 | Radera avbryt stänger dialog | Skall | P1 |
| TC-1362 | 404 för icke-existerande system | Skall | P1 |
| TC-1363-TC-1410 | Tabb-interaktioner, data-rendering, edge cases | Skall | P1-P2 |

#### Systemformulär (TC-1411 till TC-1470)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-1411 | Skapa-läge: tomt formulär | Skall | P1 |
| TC-1412 | Redigera-läge: förifyllt | Skall | P1 |
| TC-1413 | Obligatoriska fält: namn | Skall | P1 |
| TC-1414 | Obligatoriska fält: beskrivning | Skall | P1 |
| TC-1415 | Obligatoriska fält: organisation | Skall | P1 |
| TC-1416 | Obligatoriska fält: kategori | Skall | P1 |
| TC-1417 | Dropdown: alla systemkategorier | Skall | P1 |
| TC-1418 | Dropdown: alla livscykelstatusar | Skall | P1 |
| TC-1419 | Dropdown: alla kritikalitetsnivåer | Skall | P1 |
| TC-1420 | Checkbox: NIS2 | Skall | P1 |
| TC-1421 | Checkbox: personuppgifter | Skall | P1 |
| TC-1422 | Submit skapar system -> navigerar | Skall | P1 |
| TC-1423 | Submit uppdaterar -> navigerar | Skall | P1 |
| TC-1424 | API-fel visas i formuläret | Skall | P1 |
| TC-1425-TC-1470 | Validering, reset, responsivitet | Skall | P1-P2 |

#### Beroendegraf (TC-1471 till TC-1510)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-1471 | SVG-graf renderas | Skall | P1 |
| TC-1472 | Noder per system | Skall | P1 |
| TC-1473 | Kanter med riktningspilar | Skall | P1 |
| TC-1474 | Färgkodning per kritikalitet | Bör | P2 |
| TC-1475 | KPI-kort: totalt, system, kritiska | Skall | P1 |
| TC-1476 | Tabell-vy med detaljer | Skall | P1 |
| TC-1477 | Tom vy (inga integrationer) | Skall | P2 |
| TC-1478-TC-1510 | Hover, tooltips, stora grafer | Bör | P2-P3 |

#### Import (TC-1511 till TC-1550)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-1511 | 3 tabbar renderas | Skall | P1 |
| TC-1512 | Filuppladdning drag-drop | Skall | P1 |
| TC-1513 | Accepterar .xlsx | Skall | P1 |
| TC-1514 | Accepterar .csv | Skall | P1 |
| TC-1515 | Avvisar felaktiga filtyper | Skall | P1 |
| TC-1516 | Organisation-val (bara system-tab) | Skall | P1 |
| TC-1517 | Import-resultat med antal | Skall | P1 |
| TC-1518 | Import-resultat med fellista | Skall | P1 |
| TC-1519 | Laddningsindikator | Skall | P2 |
| TC-1520-TC-1550 | Felfallscenarier, stora filer | Skall | P1-P2 |

#### Rapporter (TC-1551 till TC-1580)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-1551 | 3 rapportkort renderas | Skall | P1 |
| TC-1552 | NIS2: JSON nedladdning | Skall | P1 |
| TC-1553 | NIS2: Excel nedladdning | Skall | P1 |
| TC-1554 | NIS2: PDF nedladdning | Skall | P1 |
| TC-1555 | NIS2: HTML nedladdning | Skall | P1 |
| TC-1556 | Compliance gap: JSON | Skall | P1 |
| TC-1557 | Compliance gap: PDF | Skall | P1 |
| TC-1558 | Export: Excel | Skall | P1 |
| TC-1559 | Export: CSV | Skall | P1 |
| TC-1560 | Export: JSON | Skall | P1 |
| TC-1561-TC-1580 | Felfallscenarier, laddning | Skall | P1-P2 |

#### API-klient & komponenter (TC-1581 till TC-1600)

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-1581 | API: alla endpoints anropas korrekt | Skall | P1 |
| TC-1582 | API: felhantering 404 | Skall | P1 |
| TC-1583 | API: felhantering 500 | Skall | P1 |
| TC-1584 | API: nätverksfel | Skall | P1 |
| TC-1585 | ConfirmDialog: öppen/stängd | Skall | P1 |
| TC-1586 | ConfirmDialog: bekräfta | Skall | P1 |
| TC-1587 | ConfirmDialog: avbryt | Skall | P1 |
| TC-1588 | ConfirmDialog: destructive variant | Skall | P2 |
| TC-1589 | ConfirmDialog: loading state | Skall | P2 |
| TC-1590 | NotificationBell: visar count | Skall | P1 |
| TC-1591 | NotificationBell: 99+ vid > 99 | Bör | P3 |
| TC-1592 | NotificationBell: refetch 60s | Bör | P3 |
| TC-1593-TC-1600 | Routing, navigation, layout | Skall | P1 |

---

### TC-1601 till TC-1800: Datakvalitet och regelefterlevnad

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-1601 | Notification: missing_classification | Skall | P1 |
| TC-1602 | Notification: missing_owner | Skall | P1 |
| TC-1603 | Notification: missing_gdpr_treatment | Skall | P1 |
| TC-1604 | Notification: stale_classification (>12 mån) | Skall | P1 |
| TC-1605 | Notification: expiring_contract (<90 dagar) | Skall | P1 |
| TC-1606 | Notification severity: info | Skall | P2 |
| TC-1607 | Notification severity: warning | Skall | P2 |
| TC-1608 | Notification severity: critical | Skall | P2 |
| TC-1609 | Notification paginering | Skall | P2 |
| TC-1610 | Notification summary per severity | Skall | P2 |
| TC-1611-TC-1650 | NIS2/CSL: Art. 21(2)(i) tillgångsförvaltning | Skall | P1 |
| TC-1651-TC-1690 | ISO 27001: A.5.9, A.5.12, A.5.14, A.5.15, A.5.19-22, A.5.23, A.5.30 | Skall | P1 |
| TC-1691-TC-1720 | MSBFS 2020:7 Kap 2 § 4: alla 4 punkter | Skall | P1 |
| TC-1721-TC-1750 | GDPR Art. 30: behandlingsregister-koppling | Skall | P1 |
| TC-1751-TC-1770 | MSBFS 2020:6 §6: K/R/T + årlig uppföljning | Skall | P1 |
| TC-1771-TC-1790 | NIS2-rapport: korrekt data, alla format | Skall | P1 |
| TC-1791-TC-1800 | Compliance gap: 5 kategorier korrekt | Skall | P1 |

---

### TC-1801 till TC-1950: Prestanda och skalbarhet

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-1801 | 100 system: GET /systems/ < 1s | Skall | P1 |
| TC-1802 | 500 system: GET /systems/ < 2s | Skall | P1 |
| TC-1803 | 1000 system: GET /systems/ < 3s | Bör | P2 |
| TC-1804 | 500 system: sök < 2s | Skall | P1 |
| TC-1805 | 500 system: filter < 2s | Skall | P1 |
| TC-1806 | 500 system: stats/overview < 2s | Skall | P1 |
| TC-1807 | 500 system: export Excel < 5s | Skall | P1 |
| TC-1808 | 500 system: export CSV < 3s | Skall | P1 |
| TC-1809 | 500 system: export JSON < 2s | Skall | P1 |
| TC-1810 | Paginering: 500 system, 20 sidor korrekt | Skall | P1 |
| TC-1811-TC-1830 | Relationer under skalning (500 integrationer) | Skall | P1 |
| TC-1831-TC-1850 | Import skalning (100, 500, 1000 rader) | Skall | P1 |
| TC-1851-TC-1870 | Rapport-generering med 500 system | Skall | P1 |
| TC-1871-TC-1890 | PDF-generering under last | Bör | P2 |
| TC-1891-TC-1910 | Concurrent requests (10/20/50 parallella) | Bör | P2 |
| TC-1911-TC-1930 | Response times: health < 100ms, CRUD < 500ms | Skall | P1 |
| TC-1931-TC-1950 | Memory usage under last (ingen OOM) | Bör | P2 |

---

### TC-1951 till TC-2000: Plattformskrav

| TC-ID | Beskrivning | Krav | Prioritet |
|-------|-------------|------|-----------|
| TC-1951 | REST API dokumenterat (OpenAPI/Swagger) | Skall | P1 |
| TC-1952 | API-autentisering (X-Organization-Id) | Skall | P1 |
| TC-1953 | CORS konfigurerad (localhost:5173, :3000) | Skall | P1 |
| TC-1954 | Health check endpoint | Skall | P1 |
| TC-1955 | Import: Excel (.xlsx, .xls) | Skall | P1 |
| TC-1956 | Import: CSV | Skall | P1 |
| TC-1957 | Import: JSON | Skall | P1 |
| TC-1958 | Export: Excel | Skall | P1 |
| TC-1959 | Export: CSV | Skall | P1 |
| TC-1960 | Export: JSON | Skall | P1 |
| TC-1961 | NIS2-rapport: JSON | Skall | P1 |
| TC-1962 | NIS2-rapport: Excel | Skall | P1 |
| TC-1963 | NIS2-rapport: HTML | Skall | P1 |
| TC-1964 | NIS2-rapport: PDF | Skall | P1 |
| TC-1965 | Compliance gap: JSON | Skall | P1 |
| TC-1966 | Compliance gap: PDF | Skall | P1 |
| TC-1967 | RBAC: multi-tenant isolation | Skall | P1 |
| TC-1968 | RBAC: superadmin tvärgående | Skall | P1 |
| TC-1969 | SSO-stöd (SAML/OIDC placeholder) | Bör | P2 |
| TC-1970 | Svenskt gränssnitt | Skall | P1 |
| TC-1971 | WCAG 2.1 AA: semantisk HTML | Skall | P2 |
| TC-1972 | WCAG 2.1 AA: tangentbordsnavigering | Skall | P2 |
| TC-1973 | WCAG 2.1 AA: kontrast-ratio | Skall | P2 |
| TC-1974 | WCAG 2.1 AA: screen reader-stöd | Skall | P2 |
| TC-1975 | Data lagras i EU/EES | Skall (GDPR) | P1 |
| TC-1976 | Webhook/event-integration (placeholder) | Bör | P3 |
| TC-1977 | Systemkarta/beroendevisualisering | Skall (MSBFS 2020:7) | P1 |
| TC-1978 | Dashboard med KPI:er | Skall | P1 |
| TC-1979 | Notifieringar: försenad klassning | Skall | P1 |
| TC-1980 | Notifieringar: utgående avtal | Skall | P1 |
| TC-1981 | Notifieringar: saknade fält | Skall | P1 |
| TC-1982 | Dockerfile multi-stage build | Bör | P2 |
| TC-1983 | Non-root user i container | Skall (säkerhet) | P1 |
| TC-1984 | PostgreSQL 16 kompatibilitet | Skall | P1 |
| TC-1985 | Alembic migrations fungerar | Skall | P1 |
| TC-1986 | Seed data fungerar | Bör | P2 |
| TC-1987 | Docker Compose dev-miljö | Bör | P2 |
| TC-1988 | Flexibel datamodell (extended_attributes) | Skall | P1 |
| TC-1989 | UUID som primärnycklar | Skall | P1 |
| TC-1990 | Async SQLAlchemy 2.0 | Bör | P2 |
| TC-1991 | Connection pool (20 size, 10 overflow) | Bör | P2 |
| TC-1992 | ProxyHeaders middleware | Bör | P3 |
| TC-1993 | SafeStringMixin blockerar null bytes | Skall | P1 |
| TC-1994 | Enum-värden på svenska | Skall | P1 |
| TC-1995 | Datum i ISO-format | Skall | P2 |
| TC-1996 | UUID-till-sträng i export | Skall | P2 |
| TC-1997 | Streaming responses för stora exporter | Bör | P2 |
| TC-1998 | WeasyPrint PDF-generering | Bör | P2 |
| TC-1999 | pg_trgm för snabb ILIKE-sök | Bör | P2 |
| TC-2000 | uuid-ossp extension aktiverad | Skall | P1 |

---

## Sammanfattning

| Kategori | TC-range | Antal | Område |
|----------|----------|-------|--------|
| Kravspec Kat 1-6 | TC-0001–TC-0300 | 300 | Attributvalidering |
| Kravspec Kat 7-12 | TC-0301–TC-0600 | 300 | Integrationer, avtal, compliance |
| Multi-org & säkerhet | TC-0601–TC-0800 | 200 | RLS, isolation, RBAC |
| E2E arbetsflöden | TC-0801–TC-1000 | 200 | Livscykel, import/export |
| Gränsfall & säkerhet | TC-1001–TC-1250 | 250 | Injection, fuzzing, edge cases |
| Frontend | TC-1251–TC-1600 | 350 | React, komponenter, UX |
| Datakvalitet & compliance | TC-1601–TC-1800 | 200 | NIS2, GDPR, ISO, notifikationer |
| Prestanda & skalbarhet | TC-1801–TC-1950 | 150 | Svarstider, 500-1000 system |
| Plattformskrav | TC-1951–TC-2000 | 50 | Infrastruktur, format, WCAG |
| **TOTALT** | **TC-0001–TC-2000** | **2000** | |

### Prioritetsfördelning

| Prioritet | Antal | Beskrivning |
|-----------|-------|-------------|
| P1 | ~1200 | Eliminatoriska, regulatoriskt krävda |
| P2 | ~550 | Starkt rekommenderade |
| P3 | ~250 | Nice-to-have, optimeringar |

### Regulatorisk täckning

| Regelverk | Testfall | Primär täckning |
|-----------|----------|----------------|
| NIS2/CSL (SFS 2025:1506) | ~400 | TC-0581–0600, TC-0601–0800, TC-1611–1650 |
| ISO 27001:2022 Annex A | ~350 | TC-0061–0110, TC-0111–0180, TC-1651–1690 |
| MSBFS 2020:6/7 | ~300 | TC-0111–0180, TC-0301–0400, TC-1691–1720 |
| GDPR Art. 30 | ~250 | TC-0181–0230, TC-1721–1750 |
| Säkerhetsskyddslagen | ~50 | TC-0160, TC-1001–1050 |
| WCAG 2.1 AA | ~20 | TC-1971–1974 |
