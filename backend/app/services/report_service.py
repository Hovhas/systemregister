"""Business logic for NIS2 and compliance-gap reports."""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Contract, Module, System


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

    # ------------------------------------------------------------------
    # GDPR-rapport
    # ------------------------------------------------------------------

    @staticmethod
    async def get_gdpr_report(db: AsyncSession, organization_id: UUID | None = None) -> dict:
        stmt = (
            select(System)
            .where(System.treats_personal_data == True)  # noqa: E712
            .options(selectinload(System.gdpr_treatments))
            .order_by(System.name)
        )
        if organization_id:
            stmt = stmt.where(System.organization_id == organization_id)
        result = await db.execute(stmt)
        systems = list(result.scalars().all())

        entries = []
        missing_pub_count = 0
        missing_dpia_count = 0
        third_country_count = 0
        missing_treatment_count = 0

        for s in systems:
            treatments = s.gdpr_treatments
            has_pub = any(t.processor_agreement_status is not None for t in treatments)
            has_dpia = any(t.dpia_conducted for t in treatments)
            has_third_country = s.third_country_transfer
            missing_treatment = len(treatments) == 0

            if not has_pub:
                missing_pub_count += 1
            if not has_dpia:
                missing_dpia_count += 1
            if has_third_country:
                third_country_count += 1
            if missing_treatment:
                missing_treatment_count += 1

            entries.append({
                "id": str(s.id),
                "name": s.name,
                "organization_id": str(s.organization_id),
                "has_pub": has_pub,
                "has_dpia": has_dpia,
                "third_country_transfer": has_third_country,
                "missing_treatment": missing_treatment,
                "treatment_count": len(treatments),
            })

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_personal_data_systems": len(systems),
                "missing_pub_count": missing_pub_count,
                "missing_dpia_count": missing_dpia_count,
                "third_country_count": third_country_count,
                "missing_treatment_count": missing_treatment_count,
            },
            "systems": entries,
        }

    # ------------------------------------------------------------------
    # AI-rapport
    # ------------------------------------------------------------------

    @staticmethod
    async def get_ai_report(db: AsyncSession, organization_id: UUID | None = None) -> dict:
        stmt = (
            select(System)
            .where(System.uses_ai == True)  # noqa: E712
            .options(
                selectinload(System.gdpr_treatments),
                selectinload(System.owners),
            )
            .order_by(System.name)
        )
        if organization_id:
            stmt = stmt.where(System.organization_id == organization_id)
        result = await db.execute(stmt)
        systems = list(result.scalars().all())

        mod_stmt = select(Module).where(Module.uses_ai == True)  # noqa: E712
        if organization_id:
            mod_stmt = mod_stmt.where(Module.organization_id == organization_id)
        mod_result = await db.execute(mod_stmt)
        ai_modules = list(mod_result.scalars().all())

        by_risk_class: dict[str, int] = {}
        missing_fria_count = 0
        missing_transparency_count = 0
        entries = []

        for s in systems:
            rc = s.ai_risk_class.value if s.ai_risk_class else "ej_klassad"
            by_risk_class[rc] = by_risk_class.get(rc, 0) + 1

            if s.ai_risk_class and s.ai_risk_class.value == "hög_risk" and (s.fria_status is None or s.fria_status.value != "ja"):
                missing_fria_count += 1
            if not s.ai_transparency_fulfilled:
                missing_transparency_count += 1

            entries.append({
                "id": str(s.id),
                "name": s.name,
                "organization_id": str(s.organization_id),
                "ai_risk_class": s.ai_risk_class.value if s.ai_risk_class else None,
                "fria_status": s.fria_status.value if s.fria_status else None,
                "ai_transparency_fulfilled": s.ai_transparency_fulfilled,
                "ai_usage_description": s.ai_usage_description,
            })

        module_entries = []
        for m in ai_modules:
            module_entries.append({
                "id": str(m.id),
                "name": m.name,
                "organization_id": str(m.organization_id),
                "ai_risk_class": m.ai_risk_class.value if m.ai_risk_class else None,
            })

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_ai_systems": len(systems),
                "by_risk_class": by_risk_class,
                "missing_fria_count": missing_fria_count,
                "missing_transparency_count": missing_transparency_count,
                "ai_modules_count": len(ai_modules),
            },
            "systems": entries,
            "modules": module_entries,
        }

    # ------------------------------------------------------------------
    # Klassningsstatus-rapport
    # ------------------------------------------------------------------

    @staticmethod
    async def get_classification_report(db: AsyncSession, organization_id: UUID | None = None) -> dict:
        stmt = (
            select(System)
            .options(selectinload(System.classifications))
            .order_by(System.name)
        )
        if organization_id:
            stmt = stmt.where(System.organization_id == organization_id)
        result = await db.execute(stmt)
        systems = list(result.scalars().all())

        today = date.today()
        without_classification = 0
        expired_count = 0
        valid_count = 0
        entries = []

        for s in systems:
            has_classification = len(s.classifications) > 0
            most_recent_date = None
            is_expired = False

            if has_classification:
                # classifications are ordered desc by classified_at
                most_recent = s.classifications[0]
                most_recent_date = most_recent.classified_at.isoformat() if most_recent.classified_at else None
                if most_recent.valid_until and most_recent.valid_until < today:
                    is_expired = True

            if not has_classification:
                without_classification += 1
            elif is_expired:
                expired_count += 1
            else:
                valid_count += 1

            entries.append({
                "id": str(s.id),
                "name": s.name,
                "organization_id": str(s.organization_id),
                "has_classification": has_classification,
                "most_recent_date": most_recent_date,
                "is_expired": is_expired,
            })

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_systems": len(systems),
                "without_classification": without_classification,
                "expired_count": expired_count,
                "valid_count": valid_count,
            },
            "systems": entries,
        }

    # ------------------------------------------------------------------
    # Livscykel-rapport
    # ------------------------------------------------------------------

    @staticmethod
    async def get_lifecycle_report(db: AsyncSession, organization_id: UUID | None = None) -> dict:
        today = date.today()

        # Expiring contracts bucketed by 30/60/90/180 days
        cutoffs = [
            ("30d", today + timedelta(days=30)),
            ("60d", today + timedelta(days=60)),
            ("90d", today + timedelta(days=90)),
            ("180d", today + timedelta(days=180)),
        ]

        contract_entries = []
        contract_stmt = (
            select(Contract)
            .where(Contract.contract_end.is_not(None))
            .where(Contract.contract_end >= today)
            .where(Contract.contract_end <= today + timedelta(days=180))
            .order_by(Contract.contract_end)
        )
        contract_result = await db.execute(contract_stmt)
        contracts = list(contract_result.scalars().all())

        expiring_30d = 0
        expiring_90d = 0
        expiring_180d = 0
        for c in contracts:
            days_left = (c.contract_end - today).days
            if days_left <= 30:
                expiring_30d += 1
            if days_left <= 90:
                expiring_90d += 1
            if days_left <= 180:
                expiring_180d += 1
            contract_entries.append({
                "id": str(c.id),
                "system_id": str(c.system_id),
                "supplier_name": c.supplier_name,
                "contract_end": c.contract_end.isoformat(),
                "days_remaining": days_left,
            })

        # Systems with end_of_support_date approaching (within 180 days)
        eos_stmt = (
            select(System)
            .where(System.end_of_support_date.is_not(None))
            .where(System.end_of_support_date >= today)
            .where(System.end_of_support_date <= today + timedelta(days=180))
            .order_by(System.end_of_support_date)
        )
        if organization_id:
            eos_stmt = eos_stmt.where(System.organization_id == organization_id)
        eos_result = await db.execute(eos_stmt)
        eos_systems = list(eos_result.scalars().all())

        eos_entries = []
        for s in eos_systems:
            eos_entries.append({
                "id": str(s.id),
                "name": s.name,
                "organization_id": str(s.organization_id),
                "end_of_support_date": s.end_of_support_date.isoformat(),
                "days_remaining": (s.end_of_support_date - today).days,
            })

        # Systems under decommission
        decomm_stmt = (
            select(System)
            .where(System.lifecycle_status == "under_avveckling")
            .order_by(System.name)
        )
        if organization_id:
            decomm_stmt = decomm_stmt.where(System.organization_id == organization_id)
        decomm_result = await db.execute(decomm_stmt)
        decomm_systems = list(decomm_result.scalars().all())

        decomm_entries = []
        for s in decomm_systems:
            decomm_entries.append({
                "id": str(s.id),
                "name": s.name,
                "organization_id": str(s.organization_id),
                "planned_decommission_date": s.planned_decommission_date.isoformat() if s.planned_decommission_date else None,
            })

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "expiring_contracts_30d": expiring_30d,
                "expiring_contracts_90d": expiring_90d,
                "expiring_contracts_180d": expiring_180d,
                "end_of_support_count": len(eos_systems),
                "decommission_count": len(decomm_systems),
            },
            "contracts": contract_entries,
            "end_of_support_systems": eos_entries,
            "decommissioning_systems": decomm_entries,
        }
