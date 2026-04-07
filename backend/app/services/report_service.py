"""Business logic for NIS2 and compliance-gap reports."""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Contract, System


class ReportService:

    @staticmethod
    async def get_nis2_systems(db: AsyncSession, organization_id: UUID | None = None) -> list[System]:
        stmt = (
            select(System)
            .where(System.nis2_applicable == True)  # noqa: E712
            .options(
                selectinload(System.classifications),
                selectinload(System.owners),
                selectinload(System.gdpr_treatments),
            )
            .order_by(System.name)
        )
        if organization_id:
            stmt = stmt.where(System.organization_id == organization_id)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def build_nis2_report(systems: list[System]) -> dict:
        without_classification = sum(1 for s in systems if s.nis2_classification is None)
        without_risk_assessment = sum(1 for s in systems if s.last_risk_assessment_date is None)

        system_entries = []
        for s in systems:
            system_entries.append({
                "id": str(s.id),
                "name": s.name,
                "organization_id": str(s.organization_id),
                "nis2_classification": s.nis2_classification.value if s.nis2_classification else None,
                "criticality": s.criticality.value,
                "last_risk_assessment_date": s.last_risk_assessment_date.isoformat() if s.last_risk_assessment_date else None,
                "has_gdpr_treatment": len(s.gdpr_treatments) > 0,
                "owner_names": [o.name for o in s.owners],
            })

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total": len(systems),
                "without_classification": without_classification,
                "without_risk_assessment": without_risk_assessment,
            },
            "systems": system_entries,
        }

    @staticmethod
    async def get_compliance_gap_data(db: AsyncSession) -> dict:
        """Collect compliance gap data — reused by JSON and PDF endpoints."""
        stmt_no_class = select(System).where(~System.classifications.any()).options(
            selectinload(System.classifications)
        )
        systems_no_class = [
            {"id": str(s.id), "name": str(s.name), "organization_id": str(s.organization_id)}
            for s in (await db.execute(stmt_no_class)).scalars().all()
        ]

        stmt_no_owner = select(System).where(~System.owners.any()).options(
            selectinload(System.owners)
        )
        systems_no_owner = [
            {"id": str(s.id), "name": str(s.name), "organization_id": str(s.organization_id)}
            for s in (await db.execute(stmt_no_owner)).scalars().all()
        ]

        stmt_personal_no_gdpr = (
            select(System)
            .where(System.treats_personal_data == True)  # noqa: E712
            .where(~System.gdpr_treatments.any())
            .options(selectinload(System.gdpr_treatments))
        )
        personal_no_gdpr = [
            {"id": str(s.id), "name": str(s.name), "organization_id": str(s.organization_id)}
            for s in (await db.execute(stmt_personal_no_gdpr)).scalars().all()
        ]

        stmt_nis2_no_risk = (
            select(System)
            .where(System.nis2_applicable == True)  # noqa: E712
            .where(System.last_risk_assessment_date == None)  # noqa: E711
        )
        nis2_no_risk = [
            {"id": str(s.id), "name": str(s.name), "organization_id": str(s.organization_id)}
            for s in (await db.execute(stmt_nis2_no_risk)).scalars().all()
        ]

        cutoff = date.today() + timedelta(days=90)
        stmt_expiring = (
            select(Contract)
            .where(Contract.contract_end.is_not(None))
            .where(Contract.contract_end <= cutoff)
            .where(Contract.contract_end >= date.today())
            .order_by(Contract.contract_end)
        )
        expiring = [
            {
                "id": str(c.id),
                "system_id": str(c.system_id),
                "supplier_name": c.supplier_name,
                "contract_end": c.contract_end.isoformat() if c.contract_end else None,
            }
            for c in (await db.execute(stmt_expiring)).scalars().all()
        ]

        total_gaps = (
            len(systems_no_class) + len(systems_no_owner)
            + len(personal_no_gdpr) + len(nis2_no_risk) + len(expiring)
        )

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "gaps": {
                "missing_classification": systems_no_class,
                "missing_owner": systems_no_owner,
                "personal_data_without_gdpr": personal_no_gdpr,
                "nis2_without_risk_assessment": nis2_no_risk,
                "expiring_contracts": expiring,
            },
            "summary": {"total_gaps": total_gaps},
        }
