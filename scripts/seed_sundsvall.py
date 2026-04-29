"""Seed-data: sammanhållet utsnitt av Sundsvalls verksamhet.

Idempotent — `get_or_create` per (organization_id, name). Endast
manuell körning:

    docker compose exec backend python -m scripts.seed_sundsvall

OBS: Detta är ett demoverktyg — kör aldrig automatiskt i produktion.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import (
    BusinessCapability, BusinessProcess, BusinessRole, EmploymentTemplate,
    InformationAsset, Organization, OrgUnit, Position, RoleSystemAccess,
    System, SystemIntegration, ValueStream,
    capability_system_link, process_capability_link, process_information_link,
    process_system_link, template_role_link,
)
from app.models.enums import (
    AccessLevel, AccessType, Criticality, IntegrationType, LifecycleStatus,
    NIS2Classification, OrganizationType, OrgUnitType, SystemCategory,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("seed_sundsvall")


# ============================================================
# Helpers
# ============================================================

async def _get_or_create(
    db: AsyncSession, model, *, defaults: dict | None = None, **filters,
):
    stmt = select(model)
    for key, value in filters.items():
        stmt = stmt.where(getattr(model, key) == value)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        return existing, False
    payload = {**filters, **(defaults or {})}
    obj = model(**payload)
    db.add(obj)
    await db.flush()
    log.info("  + %s: %s", model.__name__, getattr(obj, "name", getattr(obj, "title", obj.id)))
    return obj, True


async def _link(db: AsyncSession, table, **values) -> None:
    """Idempotent länkning på N:M-tabell."""
    where = [getattr(table.c, k) == v for k, v in values.items()]
    exists = (await db.execute(table.select().where(*where))).first()
    if exists:
        return
    await db.execute(table.insert().values(**values))


# ============================================================
# Datasammanställning
# ============================================================

ORGANIZATIONS = [
    ("Sundsvalls kommun", "212000-2411", OrganizationType.KOMMUN),
    ("Ånge kommun", "212000-2387", OrganizationType.KOMMUN),
    ("Timrå kommun", "212000-2395", OrganizationType.KOMMUN),
    ("MittSverige Vatten & Avfall AB", "556407-7406", OrganizationType.BOLAG),
    ("Sundsvall Elnät AB", "556502-7445", OrganizationType.BOLAG),
    ("Sundsvall Energi AB", "556187-1085", OrganizationType.BOLAG),
    ("Sundsvalls Hamn AB", "556055-2376", OrganizationType.BOLAG),
    ("DigIT (samverkan)", None, OrganizationType.SAMVERKAN),
]


ORG_UNITS = [
    # (name, parent_name|None, unit_type)
    ("Kommunstyrelsekontoret (KSK)", None, OrgUnitType.FORVALTNING),
    ("Ekonomiavdelningen", "Kommunstyrelsekontoret (KSK)", OrgUnitType.AVDELNING),
    ("HR-avdelningen", "Kommunstyrelsekontoret (KSK)", OrgUnitType.AVDELNING),
    ("Kommunikationsavdelningen", "Kommunstyrelsekontoret (KSK)", OrgUnitType.AVDELNING),
    ("Barn- och utbildningsförvaltningen (BUF)", None, OrgUnitType.FORVALTNING),
    ("Förskola", "Barn- och utbildningsförvaltningen (BUF)", OrgUnitType.AVDELNING),
    ("Grundskola", "Barn- och utbildningsförvaltningen (BUF)", OrgUnitType.AVDELNING),
    ("Gymnasieskola", "Barn- och utbildningsförvaltningen (BUF)", OrgUnitType.AVDELNING),
    ("Vård- och omsorgsförvaltningen (VOF)", None, OrgUnitType.FORVALTNING),
    ("Hemtjänst", "Vård- och omsorgsförvaltningen (VOF)", OrgUnitType.AVDELNING),
    ("Särskilt boende", "Vård- och omsorgsförvaltningen (VOF)", OrgUnitType.AVDELNING),
    ("Individ- och arbetsmarknadsförvaltningen (IAF)", None, OrgUnitType.FORVALTNING),
    ("Försörjningsstöd", "Individ- och arbetsmarknadsförvaltningen (IAF)", OrgUnitType.AVDELNING),
    ("Barn och familj", "Individ- och arbetsmarknadsförvaltningen (IAF)", OrgUnitType.AVDELNING),
    ("Stadsbyggnadskontoret (SBK)", None, OrgUnitType.FORVALTNING),
    ("Bygglov", "Stadsbyggnadskontoret (SBK)", OrgUnitType.AVDELNING),
    ("Plan", "Stadsbyggnadskontoret (SBK)", OrgUnitType.AVDELNING),
    ("Lantmäteri", "Stadsbyggnadskontoret (SBK)", OrgUnitType.AVDELNING),
    ("Kultur- och fritidsförvaltningen", None, OrgUnitType.FORVALTNING),
    ("Miljökontoret", None, OrgUnitType.FORVALTNING),
    ("Drakfastigheter", None, OrgUnitType.FORVALTNING),
]


CAPABILITIES_TOP = [
    ("Demokrati och styrning", "Kommunstyrelsekontoret (KSK)", 4),
    ("Utbildning och lärande", "Barn- och utbildningsförvaltningen (BUF)", 3),
    ("Vård och omsorg", "Vård- och omsorgsförvaltningen (VOF)", 3),
    ("Stöd till individ och familj", "Individ- och arbetsmarknadsförvaltningen (IAF)", 3),
    ("Samhällsbyggnad", "Stadsbyggnadskontoret (SBK)", 3),
    ("Kultur och fritid", "Kultur- och fritidsförvaltningen", 2),
    ("Miljö och hälsoskydd", "Miljökontoret", 3),
    ("Räddning och beredskap", None, 2),
    ("Näringsliv och arbete", "Kommunstyrelsekontoret (KSK)", 2),
    ("Intern administration", "Kommunstyrelsekontoret (KSK)", 4),
]


CAPABILITIES_SUB = [
    ("Förskoleverksamhet", "Utbildning och lärande", 3),
    ("Grundskoleutbildning", "Utbildning och lärande", 3),
    ("Gymnasial utbildning", "Utbildning och lärande", 3),
    ("Vuxenutbildning", "Utbildning och lärande", 2),
    ("Hemtjänst", "Vård och omsorg", 3),
    ("Särskilt boende", "Vård och omsorg", 3),
    ("Hälso- och sjukvård i kommunal regi", "Vård och omsorg", 3),
    ("Plan", "Samhällsbyggnad", 3),
    ("Bygglov", "Samhällsbyggnad", 3),
    ("Lantmäteri", "Samhällsbyggnad", 3),
    ("Mark och exploatering", "Samhällsbyggnad", 2),
    ("HR", "Intern administration", 4),
    ("Ekonomi", "Intern administration", 4),
    ("IT", "Intern administration", 3),
    ("Kommunikation", "Intern administration", 3),
    ("Upphandling", "Intern administration", 3),
]


PROCESSES = [
    # (name, parent|None, top_capability, criticality)
    ("Bygglovshantering", None, "Samhällsbyggnad", Criticality.HIGH),
    ("Förenklad bygglovshandläggning", "Bygglovshantering", "Samhällsbyggnad", Criticality.MEDIUM),
    ("Bygglovshandläggning med grannehörande", "Bygglovshantering", "Samhällsbyggnad", Criticality.MEDIUM),
    ("Detaljplaneprocess", None, "Samhällsbyggnad", Criticality.MEDIUM),
    ("Antagning till förskola", None, "Utbildning och lärande", Criticality.HIGH),
    ("Skolskjutsplanering", None, "Utbildning och lärande", Criticality.MEDIUM),
    ("Hemtjänstplanering", None, "Vård och omsorg", Criticality.HIGH),
    ("Bostadsanpassningsbidrag", None, "Vård och omsorg", Criticality.MEDIUM),
    ("Försörjningsstödsutredning", None, "Stöd till individ och familj", Criticality.HIGH),
    ("Faktureringsprocess", None, "Intern administration", Criticality.HIGH),
    ("Anställningsprocess", None, "Intern administration", Criticality.HIGH),
    ("Inköp och upphandling", None, "Intern administration", Criticality.MEDIUM),
    ("Diarieföring", None, "Demokrati och styrning", Criticality.HIGH),
    ("Tillsyn livsmedel", None, "Miljö och hälsoskydd", Criticality.MEDIUM),
]


VALUE_STREAMS = [
    (
        "Bli ny invånare i Sundsvall",
        "Från flyttanmälan till välkomstinformation.",
        [
            "Anmäl flytt", "Få personnummer-koppling", "Söka skola/förskola",
            "Folkbokföring klar", "Få välkomstinformation",
        ],
    ),
    (
        "Söka och få bygglov",
        "Hela bygglovsprocessen från förfrågan till slutbesked.",
        [
            "Förfrågan", "Inlämning ansökan", "Granskning", "Grannehörande",
            "Beslut", "Slutbesked",
        ],
    ),
    (
        "Bli äldre och få stöd hemma",
        "Från första kontakt till verkställighet och uppföljning.",
        [
            "Kontakt med biståndshandläggare", "Behovsbedömning", "Beslut",
            "Insatsplanering", "Verkställighet", "Uppföljning",
        ],
    ),
]


SYSTEMS_DATA = [
    # (name, category, criticality, treats_personal_data, nis2_applicable, nis2_classification|None)
    ("Active Directory", SystemCategory.INFRASTRUKTUR, Criticality.CRITICAL, True, True, NIS2Classification.ESSENTIAL),
    ("Microsoft Identity Manager (MIM)", SystemCategory.PLATTFORM, Criticality.CRITICAL, True, True, NIS2Classification.ESSENTIAL),
    ("Metakatalogen", SystemCategory.PLATTFORM, Criticality.HIGH, True, False, None),
    ("WSO2 API Manager", SystemCategory.PLATTFORM, Criticality.HIGH, False, True, NIS2Classification.IMPORTANT),
    ("Camunda BPM", SystemCategory.PLATTFORM, Criticality.MEDIUM, False, False, None),
    ("Eneo AI", SystemCategory.PLATTFORM, Criticality.MEDIUM, False, False, None),
    ("Diwise IoT", SystemCategory.PLATTFORM, Criticality.MEDIUM, False, False, None),
    ("SiteVision CMS", SystemCategory.STODSYSTEM, Criticality.MEDIUM, False, False, None),
    ("Open ePlatform", SystemCategory.STODSYSTEM, Criticality.HIGH, True, False, None),
    ("Mitt Sundsvall", SystemCategory.STODSYSTEM, Criticality.MEDIUM, True, False, None),
    ("Procapita VoO", SystemCategory.VERKSAMHETSSYSTEM, Criticality.HIGH, True, False, None),
    ("Combine (IFO)", SystemCategory.VERKSAMHETSSYSTEM, Criticality.HIGH, True, False, None),
    ("ByggR", SystemCategory.VERKSAMHETSSYSTEM, Criticality.MEDIUM, True, False, None),
    ("IST Administration / Edlevo", SystemCategory.VERKSAMHETSSYSTEM, Criticality.HIGH, True, False, None),
    ("Heroma", SystemCategory.VERKSAMHETSSYSTEM, Criticality.HIGH, True, False, None),
    ("Raindance", SystemCategory.VERKSAMHETSSYSTEM, Criticality.HIGH, False, False, None),
    ("Visma Proceedo", SystemCategory.STODSYSTEM, Criticality.MEDIUM, False, False, None),
    ("Public 360", SystemCategory.VERKSAMHETSSYSTEM, Criticality.HIGH, True, False, None),
]


INTEGRATIONS = [
    # (source, target, type, frequency, criticality)
    ("Heroma", "Metakatalogen", IntegrationType.FILE_TRANSFER, "dagligen", Criticality.CRITICAL),
    ("Metakatalogen", "Active Directory", IntegrationType.API, "near-realtime", Criticality.CRITICAL),
    ("Procapita VoO", "WSO2 API Manager", IntegrationType.API, "on-demand", Criticality.HIGH),
    ("Combine (IFO)", "WSO2 API Manager", IntegrationType.API, "on-demand", Criticality.HIGH),
    ("Open ePlatform", "Camunda BPM", IntegrationType.EVENT, "realtime", Criticality.MEDIUM),
    ("Mitt Sundsvall", "Open ePlatform", IntegrationType.API, "on-demand", Criticality.MEDIUM),
    ("Public 360", "SiteVision CMS", IntegrationType.FILE_TRANSFER, "dagligen", Criticality.MEDIUM),
    ("IST Administration / Edlevo", "Active Directory", IntegrationType.FILE_TRANSFER, "dagligen", Criticality.HIGH),
    ("Heroma", "Raindance", IntegrationType.FILE_TRANSFER, "månadsvis", Criticality.HIGH),
    ("ByggR", "Public 360", IntegrationType.API, "on-demand", Criticality.MEDIUM),
    ("Procapita VoO", "Public 360", IntegrationType.API, "on-demand", Criticality.MEDIUM),
    ("Eneo AI", "WSO2 API Manager", IntegrationType.API, "on-demand", Criticality.MEDIUM),
    ("Diwise IoT", "WSO2 API Manager", IntegrationType.EVENT, "realtime", Criticality.MEDIUM),
    ("Visma Proceedo", "Raindance", IntegrationType.FILE_TRANSFER, "veckovis", Criticality.MEDIUM),
    ("Combine (IFO)", "Public 360", IntegrationType.API, "on-demand", Criticality.MEDIUM),
]


INFORMATION_ASSETS = [
    # (name, K, R, T, contains_personal_data, personal_data_type, retention_period)
    ("Personalakter", 3, 3, 4, True, "vanliga", "Bevaras enl. arbetsrätt"),
    ("Elevregister", 3, 4, 4, True, "vanliga", "Bevaras"),
    ("Hälso- och sjukvårdsdokumentation", 4, 4, 4, True, "känsliga", "Bevaras min. 10 år"),
    ("Försörjningsstödsutredningar", 4, 4, 4, True, "känsliga", "Gallras efter 5 år"),
    ("Bygglovsärenden", 2, 3, 3, True, "vanliga", "Bevaras"),
    ("Diarieförda allmänna handlingar", 2, 4, 4, True, None, "Bevaras"),
    ("Leverantörsregister", 2, 3, 3, False, None, "Bevaras"),
    ("Lönedata", 3, 4, 3, True, "vanliga", "Bevaras enl. lönerätt"),
]


PROCESS_SYSTEM_LINKS = [
    ("Bygglovshantering", "ByggR"),
    ("Bygglovshantering", "Public 360"),
    ("Detaljplaneprocess", "Public 360"),
    ("Antagning till förskola", "IST Administration / Edlevo"),
    ("Skolskjutsplanering", "IST Administration / Edlevo"),
    ("Hemtjänstplanering", "Procapita VoO"),
    ("Bostadsanpassningsbidrag", "Procapita VoO"),
    ("Försörjningsstödsutredning", "Combine (IFO)"),
    ("Faktureringsprocess", "Raindance"),
    ("Anställningsprocess", "Heroma"),
    ("Anställningsprocess", "Active Directory"),
    ("Inköp och upphandling", "Visma Proceedo"),
    ("Diarieföring", "Public 360"),
]


PROCESS_INFO_LINKS = [
    ("Bygglovshantering", "Bygglovsärenden"),
    ("Diarieföring", "Diarieförda allmänna handlingar"),
    ("Anställningsprocess", "Personalakter"),
    ("Anställningsprocess", "Lönedata"),
    ("Försörjningsstödsutredning", "Försörjningsstödsutredningar"),
    ("Hemtjänstplanering", "Hälso- och sjukvårdsdokumentation"),
    ("Antagning till förskola", "Elevregister"),
    ("Faktureringsprocess", "Leverantörsregister"),
]


CAPABILITY_SYSTEM_LINKS = [
    ("Bygglov", "ByggR"),
    ("Hemtjänst", "Procapita VoO"),
    ("Grundskoleutbildning", "IST Administration / Edlevo"),
    ("HR", "Heroma"),
    ("Ekonomi", "Raindance"),
    ("IT", "Active Directory"),
    ("IT", "Microsoft Identity Manager (MIM)"),
    ("IT", "Metakatalogen"),
    ("IT", "WSO2 API Manager"),
    ("Demokrati och styrning", "Public 360"),
]


ROLES_DATA = [
    # (name, description)
    ("Bygglovshandläggare", "Handlägger bygglovsärenden i ByggR."),
    ("Biståndshandläggare hemtjänst", "Bedömer behov och beslutar insatser."),
    ("Försörjningsstödshandläggare", "Utreder ansökningar om försörjningsstöd."),
    ("Lärare grundskola", "Undervisar elever i grundskolan."),
    ("Rektor grundskola", "Pedagogiskt och administrativt ansvar."),
    ("Sjuksköterska kommun", "Hälso- och sjukvård i kommunal regi."),
    ("HR-partner", "Stödjer chefer i HR-frågor."),
    ("Ekonomihandläggare", "Hanterar fakturor och bokföring."),
    ("Diarieförare", "Diarieför allmänna handlingar."),
    ("IT-tekniker DigIT", "Driftar och felsöker IT-infrastruktur."),
    ("Standardanvändare Sundsvall", "Grundläggande åtkomst för alla anställda."),
]


# (role_name, system_name, level, type)
ROLE_ACCESS_DATA = [
    ("Bygglovshandläggare", "ByggR", AccessLevel.WRITE, AccessType.BIRTHRIGHT),
    ("Bygglovshandläggare", "Public 360", AccessLevel.WRITE, AccessType.BIRTHRIGHT),
    ("Bygglovshandläggare", "Active Directory", AccessLevel.READ, AccessType.BIRTHRIGHT),
    ("Bygglovshandläggare", "Heroma", AccessLevel.READ, AccessType.BIRTHRIGHT),

    ("Biståndshandläggare hemtjänst", "Procapita VoO", AccessLevel.WRITE, AccessType.BIRTHRIGHT),
    ("Biståndshandläggare hemtjänst", "Public 360", AccessLevel.READ, AccessType.BIRTHRIGHT),

    ("Försörjningsstödshandläggare", "Combine (IFO)", AccessLevel.WRITE, AccessType.BIRTHRIGHT),
    ("Försörjningsstödshandläggare", "Public 360", AccessLevel.READ, AccessType.BIRTHRIGHT),

    ("Lärare grundskola", "IST Administration / Edlevo", AccessLevel.WRITE, AccessType.BIRTHRIGHT),

    ("Rektor grundskola", "IST Administration / Edlevo", AccessLevel.ADMIN, AccessType.CONDITIONAL),

    ("Sjuksköterska kommun", "Procapita VoO", AccessLevel.WRITE, AccessType.BIRTHRIGHT),

    ("HR-partner", "Heroma", AccessLevel.WRITE, AccessType.BIRTHRIGHT),
    ("HR-partner", "Public 360", AccessLevel.READ, AccessType.BIRTHRIGHT),

    ("Ekonomihandläggare", "Raindance", AccessLevel.WRITE, AccessType.BIRTHRIGHT),
    ("Ekonomihandläggare", "Visma Proceedo", AccessLevel.WRITE, AccessType.BIRTHRIGHT),

    ("Diarieförare", "Public 360", AccessLevel.WRITE, AccessType.BIRTHRIGHT),

    ("IT-tekniker DigIT", "Active Directory", AccessLevel.ADMIN, AccessType.CONDITIONAL),
    ("IT-tekniker DigIT", "Metakatalogen", AccessLevel.ADMIN, AccessType.CONDITIONAL),
    ("IT-tekniker DigIT", "Microsoft Identity Manager (MIM)", AccessLevel.ADMIN, AccessType.CONDITIONAL),

    ("Standardanvändare Sundsvall", "Active Directory", AccessLevel.READ, AccessType.BIRTHRIGHT),
    ("Standardanvändare Sundsvall", "Heroma", AccessLevel.READ, AccessType.BIRTHRIGHT),
    ("Standardanvändare Sundsvall", "Mitt Sundsvall", AccessLevel.READ, AccessType.BIRTHRIGHT),
]


POSITIONS_DATA = [
    # (title, org_unit_name, primary_role)
    ("Bygglovshandläggare", "Bygglov", "Bygglovshandläggare"),
    ("Biståndshandläggare hemtjänst", "Hemtjänst", "Biståndshandläggare hemtjänst"),
    ("Lärare", "Grundskola", "Lärare grundskola"),
    ("Ekonomihandläggare", "Ekonomiavdelningen", "Ekonomihandläggare"),
    ("IT-tekniker", None, "IT-tekniker DigIT"),
]


# ============================================================
# Seed-funktionen
# ============================================================

async def seed() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with Session() as db:
        # --- Organisationer ---
        log.info("Organisationer:")
        org_by_name: dict[str, Organization] = {}
        for name, org_number, org_type in ORGANIZATIONS:
            org, _ = await _get_or_create(
                db, Organization,
                name=name,
                defaults={"org_number": org_number, "org_type": org_type},
            )
            org_by_name[name] = org

        sundsvall = org_by_name["Sundsvalls kommun"]

        # --- Org-enheter ---
        log.info("Organisationsenheter:")
        unit_by_name: dict[str, OrgUnit] = {}
        # Skapa toppnoder först
        for name, parent_name, unit_type in ORG_UNITS:
            if parent_name:
                continue
            unit, _ = await _get_or_create(
                db, OrgUnit,
                organization_id=sundsvall.id, name=name,
                defaults={"unit_type": unit_type},
            )
            unit_by_name[name] = unit
        # Sedan barn
        for name, parent_name, unit_type in ORG_UNITS:
            if not parent_name:
                continue
            parent = unit_by_name.get(parent_name)
            unit, _ = await _get_or_create(
                db, OrgUnit,
                organization_id=sundsvall.id, name=name,
                defaults={
                    "unit_type": unit_type,
                    "parent_unit_id": parent.id if parent else None,
                },
            )
            unit_by_name[name] = unit

        # --- Verksamhetsförmågor (toppnivå) ---
        log.info("Förmågor (toppnivå):")
        cap_by_name: dict[str, BusinessCapability] = {}
        for name, owner_unit, maturity in CAPABILITIES_TOP:
            cap, _ = await _get_or_create(
                db, BusinessCapability,
                organization_id=sundsvall.id, name=name,
                defaults={
                    "capability_owner": owner_unit, "maturity_level": maturity,
                },
            )
            cap_by_name[name] = cap

        # --- Förmågor (andra nivå) ---
        log.info("Förmågor (andra nivå):")
        for name, parent_name, maturity in CAPABILITIES_SUB:
            parent = cap_by_name.get(parent_name)
            cap, _ = await _get_or_create(
                db, BusinessCapability,
                organization_id=sundsvall.id, name=name,
                defaults={
                    "parent_capability_id": parent.id if parent else None,
                    "maturity_level": maturity,
                },
            )
            cap_by_name[name] = cap

        # --- Processer ---
        log.info("Processer:")
        proc_by_name: dict[str, BusinessProcess] = {}
        # Toppprocesser först
        for name, parent_name, _, criticality in PROCESSES:
            if parent_name:
                continue
            proc, _ = await _get_or_create(
                db, BusinessProcess,
                organization_id=sundsvall.id, name=name,
                defaults={"criticality": criticality},
            )
            proc_by_name[name] = proc
        # Sedan delprocesser
        for name, parent_name, _, criticality in PROCESSES:
            if not parent_name:
                continue
            parent = proc_by_name.get(parent_name)
            proc, _ = await _get_or_create(
                db, BusinessProcess,
                organization_id=sundsvall.id, name=name,
                defaults={
                    "parent_process_id": parent.id if parent else None,
                    "criticality": criticality,
                },
            )
            proc_by_name[name] = proc

        # Process → top-capability (extra realiseringskoppling)
        for proc_name, _, top_cap_name, _ in PROCESSES:
            cap = cap_by_name.get(top_cap_name)
            if cap and proc_by_name.get(proc_name):
                await _link(
                    db, process_capability_link,
                    process_id=proc_by_name[proc_name].id,
                    capability_id=cap.id,
                )

        # --- Värdeströmmar ---
        log.info("Värdeströmmar:")
        for name, description, stage_names in VALUE_STREAMS:
            stages = [
                {"name": stage, "description": None, "order": idx}
                for idx, stage in enumerate(stage_names)
            ]
            await _get_or_create(
                db, ValueStream,
                organization_id=sundsvall.id, name=name,
                defaults={"description": description, "stages": stages},
            )

        # --- System ---
        log.info("System:")
        system_by_name: dict[str, System] = {}
        for (name, category, criticality, treats_pd,
             nis2_app, nis2_class) in SYSTEMS_DATA:
            system, _ = await _get_or_create(
                db, System,
                organization_id=sundsvall.id, name=name,
                defaults={
                    "description": f"Seedat system: {name}",
                    "system_category": category,
                    "criticality": criticality,
                    "lifecycle_status": LifecycleStatus.ACTIVE,
                    "treats_personal_data": treats_pd,
                    "nis2_applicable": nis2_app,
                    "nis2_classification": nis2_class,
                    "data_location_country": "Sverige",
                    "deployment_date": date(2020, 1, 1),
                },
            )
            system_by_name[name] = system

        # --- Integrationer ---
        log.info("Integrationer:")
        for source_name, target_name, itype, freq, crit in INTEGRATIONS:
            source = system_by_name.get(source_name)
            target = system_by_name.get(target_name)
            if not source or not target:
                continue
            existing = (await db.execute(
                select(SystemIntegration).where(
                    SystemIntegration.source_system_id == source.id,
                    SystemIntegration.target_system_id == target.id,
                    SystemIntegration.integration_type == itype,
                )
            )).scalar_one_or_none()
            if existing:
                continue
            db.add(SystemIntegration(
                source_system_id=source.id,
                target_system_id=target.id,
                integration_type=itype,
                frequency=freq,
                criticality=crit,
            ))
        await db.flush()

        # --- Informationsmängder ---
        log.info("Informationsmängder:")
        info_by_name: dict[str, InformationAsset] = {}
        for (name, k, r, t, has_pd, pd_type, retention) in INFORMATION_ASSETS:
            asset, _ = await _get_or_create(
                db, InformationAsset,
                organization_id=sundsvall.id, name=name,
                defaults={
                    "confidentiality": k,
                    "integrity": r,
                    "availability": t,
                    "contains_personal_data": has_pd,
                    "personal_data_type": pd_type,
                    "retention_period": retention,
                },
            )
            info_by_name[name] = asset

        # --- Länkar process ↔ system ---
        log.info("Länkar (process ↔ system):")
        for proc_name, sys_name in PROCESS_SYSTEM_LINKS:
            proc = proc_by_name.get(proc_name)
            system = system_by_name.get(sys_name)
            if not (proc and system):
                continue
            await _link(
                db, process_system_link,
                process_id=proc.id, system_id=system.id,
            )

        # --- Länkar process ↔ informationsmängd ---
        log.info("Länkar (process ↔ informationsmängd):")
        for proc_name, info_name in PROCESS_INFO_LINKS:
            proc = proc_by_name.get(proc_name)
            asset = info_by_name.get(info_name)
            if not (proc and asset):
                continue
            await _link(
                db, process_information_link,
                process_id=proc.id, information_asset_id=asset.id,
            )

        # --- Länkar capability ↔ system ---
        log.info("Länkar (förmåga ↔ system):")
        for cap_name, sys_name in CAPABILITY_SYSTEM_LINKS:
            cap = cap_by_name.get(cap_name)
            system = system_by_name.get(sys_name)
            if not (cap and system):
                continue
            await _link(
                db, capability_system_link,
                capability_id=cap.id, system_id=system.id,
            )

        # --- Verksamhetsroller ---
        log.info("Verksamhetsroller:")
        role_by_name: dict[str, BusinessRole] = {}
        for name, description in ROLES_DATA:
            role, _ = await _get_or_create(
                db, BusinessRole,
                organization_id=sundsvall.id, name=name,
                defaults={"description": description},
            )
            role_by_name[name] = role

        # --- Roll → System åtkomst ---
        log.info("Roll-åtkomst:")
        for role_name, sys_name, level, atype in ROLE_ACCESS_DATA:
            role = role_by_name.get(role_name)
            system = system_by_name.get(sys_name)
            if not (role and system):
                continue
            existing = (await db.execute(
                select(RoleSystemAccess).where(
                    RoleSystemAccess.business_role_id == role.id,
                    RoleSystemAccess.system_id == system.id,
                )
            )).scalar_one_or_none()
            if existing:
                continue
            db.add(RoleSystemAccess(
                business_role_id=role.id,
                system_id=system.id,
                access_level=level,
                access_type=atype,
            ))
        await db.flush()

        # --- Befattningar + mallar ---
        log.info("Befattningar och anställningsmallar:")
        std_role = role_by_name["Standardanvändare Sundsvall"]
        for title, unit_name, primary_role in POSITIONS_DATA:
            unit = unit_by_name.get(unit_name) if unit_name else None
            primary = role_by_name.get(primary_role)
            position, _ = await _get_or_create(
                db, Position,
                organization_id=sundsvall.id, title=title,
                defaults={"org_unit_id": unit.id if unit else None},
            )
            template_name = f"Standardmall — {title}"
            template, created = await _get_or_create(
                db, EmploymentTemplate,
                organization_id=sundsvall.id, name=template_name,
                defaults={
                    "position_id": position.id,
                    "version": 1,
                    "is_active": True,
                },
            )
            if created and primary:
                await _link(
                    db, template_role_link,
                    template_id=template.id, role_id=primary.id,
                )
                await _link(
                    db, template_role_link,
                    template_id=template.id, role_id=std_role.id,
                )

        await db.commit()
        log.info("✅ Seed klar för Sundsvalls kommun.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
