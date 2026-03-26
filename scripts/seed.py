"""Seed-data: organisationer och exempelsystem för Sundsvalls kommunkoncern."""
import asyncio
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import get_settings
from app.models.models import Organization, System, SystemClassification, SystemOwner
from app.models.enums import *

settings = get_settings()


async def seed():
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        # --- Organisationer ---
        digit = Organization(
            id=uuid.uuid4(), name="DigIT", org_number="2120001451",
            org_type=OrganizationType.DIGIT,
            description="Gemensam IT-avdelning för Sundsvall, Ånge m.fl.",
        )
        sundsvall = Organization(
            id=uuid.uuid4(), name="Sundsvalls kommun", org_number="2120001361",
            org_type=OrganizationType.KOMMUN,
            description="Sundsvalls kommun — moderorganisation",
        )
        ange = Organization(
            id=uuid.uuid4(), name="Ånge kommun", org_number="2120002476",
            org_type=OrganizationType.KOMMUN,
            description="Ånge kommun",
        )
        timra = Organization(
            id=uuid.uuid4(), name="Timrå kommun", org_number="2120002526",
            org_type=OrganizationType.KOMMUN,
            description="Timrå kommun",
        )
        servanet = Organization(
            id=uuid.uuid4(), name="ServaNet AB", org_number="5565596024",
            org_type=OrganizationType.BOLAG,
            parent_org_id=sundsvall.id,
            description="Kommunalt stadsnätsbolag",
        )
        db.add_all([digit, sundsvall, ange, timra, servanet])

        # --- Exempelsystem ---
        p360 = System(
            organization_id=sundsvall.id,
            name="Public 360°",
            description="Ärende- och dokumenthanteringssystem (diarium). Centralt verksamhetssystem för hela kommunen.",
            system_category=SystemCategory.VERKSAMHETSSYSTEM,
            business_area="Förvaltningsövergripande",
            criticality=Criticality.CRITICAL,
            has_elevated_protection=True,
            treats_personal_data=True,
            treats_sensitive_data=True,
            hosting_model="cloud",
            cloud_provider="TietoEvry",
            data_location_country="Sverige",
            product_name="TietoEvry Public 360°",
            product_version="2024.1",
            lifecycle_status=LifecycleStatus.ACTIVE,
            deployment_date=date(2018, 1, 15),
            backup_frequency="Daglig",
            rpo="24h", rto="4h",
            dr_plan_exists=True,
            nis2_applicable=True,
            nis2_classification=NIS2Classification.ESSENTIAL,
        )

        eneo = System(
            organization_id=sundsvall.id,
            name="Eneo",
            description="Digital plattform för medborgarservice och e-tjänster. Bygger på Open ePlatform.",
            system_category=SystemCategory.PLATTFORM,
            business_area="Medborgarservice",
            criticality=Criticality.HIGH,
            has_elevated_protection=True,
            treats_personal_data=True,
            hosting_model="on-premise",
            data_location_country="Sverige",
            product_name="Eneo (Open ePlatform)",
            lifecycle_status=LifecycleStatus.ACTIVE,
            deployment_date=date(2020, 6, 1),
            backup_frequency="Daglig",
            rpo="24h", rto="8h",
            dr_plan_exists=True,
            nis2_applicable=True,
            nis2_classification=NIS2Classification.IMPORTANT,
        )

        ad = System(
            organization_id=digit.id,
            name="Active Directory",
            description="Central katalogtjänst för identitets- och behörighetshantering i hela kommunkoncernen.",
            system_category=SystemCategory.INFRASTRUKTUR,
            business_area="IT-infrastruktur",
            criticality=Criticality.CRITICAL,
            has_elevated_protection=True,
            treats_personal_data=True,
            hosting_model="on-premise",
            data_location_country="Sverige",
            product_name="Microsoft Active Directory",
            lifecycle_status=LifecycleStatus.ACTIVE,
            backup_frequency="Daglig",
            rpo="1h", rto="1h",
            dr_plan_exists=True,
            nis2_applicable=True,
            nis2_classification=NIS2Classification.ESSENTIAL,
        )

        treserva = System(
            organization_id=sundsvall.id,
            name="Treserva",
            description="Verksamhetssystem för socialtjänst, vård och omsorg. Hanterar känsliga personuppgifter.",
            system_category=SystemCategory.VERKSAMHETSSYSTEM,
            business_area="Vård och omsorg",
            criticality=Criticality.CRITICAL,
            has_elevated_protection=True,
            security_protection=False,
            treats_personal_data=True,
            treats_sensitive_data=True,
            hosting_model="cloud",
            cloud_provider="CGI",
            data_location_country="Sverige",
            product_name="CGI Treserva",
            lifecycle_status=LifecycleStatus.ACTIVE,
            deployment_date=date(2015, 9, 1),
            backup_frequency="Daglig",
            rpo="24h", rto="4h",
            dr_plan_exists=True,
            nis2_applicable=True,
            nis2_classification=NIS2Classification.ESSENTIAL,
        )

        skolplattform = System(
            organization_id=sundsvall.id,
            name="IST Administration",
            description="Skoladministrativt system för elever, betyg och schemaläggning.",
            system_category=SystemCategory.VERKSAMHETSSYSTEM,
            business_area="Utbildning",
            criticality=Criticality.HIGH,
            treats_personal_data=True,
            treats_sensitive_data=True,
            hosting_model="cloud",
            cloud_provider="IST Group",
            data_location_country="Sverige",
            product_name="IST Administration",
            lifecycle_status=LifecycleStatus.ACTIVE,
            nis2_applicable=False,
        )

        db.add_all([p360, eneo, ad, treserva, skolplattform])
        await db.flush()

        # --- Klassningar ---
        for sys_obj, k, r, t in [
            (p360, 3, 3, 3),
            (eneo, 2, 3, 3),
            (ad, 3, 4, 4),
            (treserva, 4, 3, 3),
            (skolplattform, 3, 3, 2),
        ]:
            db.add(SystemClassification(
                system_id=sys_obj.id,
                confidentiality=k, integrity=r, availability=t,
                traceability=2,
                classified_by="Håkan Simonsson",
                classified_at=datetime.now(timezone.utc),
                valid_until=date(2027, 3, 26),
            ))

        # --- Ägarskap (exempel) ---
        db.add(SystemOwner(
            system_id=p360.id, organization_id=sundsvall.id,
            role=OwnerRole.SYSTEM_OWNER,
            name="Kommunstyrelseförvaltningen", email="ks@sundsvall.se",
        ))
        db.add(SystemOwner(
            system_id=ad.id, organization_id=digit.id,
            role=OwnerRole.SYSTEM_ADMINISTRATOR,
            name="DigIT Infrastruktur", email="infra@digit.sundsvall.se",
        ))

        await db.commit()
        print(f"✅ Seed klar: 5 organisationer, 5 system, 5 klassningar, 2 ägare")


if __name__ == "__main__":
    asyncio.run(seed())
