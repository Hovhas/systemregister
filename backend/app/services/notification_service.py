"""Business logic for generating system notifications/warnings."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, func, and_, or_ as sa_or
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import System, SystemClassification, Contract


class NotificationService:

    @staticmethod
    async def generate_notifications(db: AsyncSession) -> list[dict]:
        """Generate all active notifications. Returns list of notification dicts."""
        notifications: list[dict] = []
        today = date.today()

        await NotificationService._expiring_contracts(db, notifications, today)
        await NotificationService._missing_classifications(db, notifications)
        await NotificationService._missing_owners(db, notifications)
        await NotificationService._missing_gdpr_treatments(db, notifications)
        await NotificationService._stale_classifications(db, notifications, today)
        await NotificationService._missing_risk_assessments(db, notifications)

        return notifications

    @staticmethod
    async def _expiring_contracts(db: AsyncSession, out: list[dict], today: date) -> None:
        cutoff = today + timedelta(days=90)
        stmt = (
            select(Contract)
            .where(Contract.contract_end.is_not(None))
            .where(Contract.contract_end <= cutoff)
            .where(Contract.contract_end >= today)
            .order_by(Contract.contract_end)
        )
        result = await db.execute(stmt)
        for c in result.scalars().all():
            days_left = (c.contract_end - today).days
            out.append({
                "type": "expiring_contract",
                "severity": "warning" if days_left > 30 else "critical",
                "title": f"Avtal med {c.supplier_name} löper ut",
                "description": f"Löper ut {c.contract_end.isoformat()} ({days_left} dagar kvar)",
                "system_id": str(c.system_id),
                "record_id": str(c.id),
            })

    @staticmethod
    async def _missing_classifications(db: AsyncSession, out: list[dict]) -> None:
        stmt = select(System).where(~System.classifications.any()).options(
            selectinload(System.classifications)
        )
        for s in (await db.execute(stmt)).scalars().all():
            out.append({
                "type": "missing_classification",
                "severity": "warning",
                "title": f"{s.name} saknar klassning",
                "description": "Ingen K/R/T-klassning registrerad",
                "system_id": str(s.id),
            })

    @staticmethod
    async def _missing_owners(db: AsyncSession, out: list[dict]) -> None:
        stmt = select(System).where(~System.owners.any()).options(
            selectinload(System.owners)
        )
        for s in (await db.execute(stmt)).scalars().all():
            out.append({
                "type": "missing_owner",
                "severity": "warning",
                "title": f"{s.name} saknar ägare",
                "description": "Ingen systemägare eller informationsägare registrerad",
                "system_id": str(s.id),
            })

    @staticmethod
    async def _missing_gdpr_treatments(db: AsyncSession, out: list[dict]) -> None:
        stmt = (
            select(System)
            .where(System.treats_personal_data == True)  # noqa: E712
            .where(~System.gdpr_treatments.any())
            .options(selectinload(System.gdpr_treatments))
        )
        for s in (await db.execute(stmt)).scalars().all():
            out.append({
                "type": "missing_gdpr_treatment",
                "severity": "critical",
                "title": f"{s.name} saknar GDPR-behandling",
                "description": "Behandlar personuppgifter men har ingen registrerad GDPR-behandling",
                "system_id": str(s.id),
            })

    @staticmethod
    async def _stale_classifications(db: AsyncSession, out: list[dict], today: date) -> None:
        twelve_months_ago = datetime.now(timezone.utc) - timedelta(days=365)
        subq = (
            select(
                SystemClassification.system_id,
                func.max(SystemClassification.classified_at).label("latest"),
                func.min(SystemClassification.valid_until).label("earliest_valid_until"),
            )
            .group_by(SystemClassification.system_id)
            .subquery()
        )
        stmt = (
            select(System)
            .join(subq, System.id == subq.c.system_id)
            .where(
                sa_or(
                    subq.c.latest < twelve_months_ago,
                    and_(
                        subq.c.earliest_valid_until.is_not(None),
                        subq.c.earliest_valid_until < today,
                    ),
                )
            )
        )
        for s in (await db.execute(stmt)).scalars().all():
            out.append({
                "type": "stale_classification",
                "severity": "info",
                "title": f"{s.name} behöver omklassas",
                "description": "Senaste klassning är äldre än 12 månader eller har passerat giltighetsdatum",
                "system_id": str(s.id),
            })

    @staticmethod
    async def _missing_risk_assessments(db: AsyncSession, out: list[dict]) -> None:
        stmt = (
            select(System)
            .where(System.nis2_applicable == True)  # noqa: E712
            .where(System.last_risk_assessment_date == None)  # noqa: E711
        )
        for s in (await db.execute(stmt)).scalars().all():
            out.append({
                "type": "missing_risk_assessment",
                "severity": "warning",
                "title": f"{s.name} saknar riskbedömning",
                "description": "NIS2-tillämpligt system utan registrerad riskbedömning",
                "system_id": str(s.id),
            })
