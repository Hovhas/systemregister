from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.rls import get_rls_db
from app.models.models import System, SystemClassification, SystemOwner, Contract

router = APIRouter(prefix="/notifications", tags=["Notifieringar"])


@router.get("/")
async def get_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_rls_db),
):
    """Returnerar aktiva varningar/notifieringar."""
    notifications = []
    today = date.today()

    # 1. Avtal som löper ut inom 90 dagar
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
        notifications.append({
            "type": "expiring_contract",
            "severity": "warning" if days_left > 30 else "critical",
            "title": f"Avtal med {c.supplier_name} löper ut",
            "description": f"Löper ut {c.contract_end.isoformat()} ({days_left} dagar kvar)",
            "system_id": str(c.system_id),
            "record_id": str(c.id),
        })

    # 2. System utan klassning
    stmt_no_class = select(System).where(~System.classifications.any()).options(selectinload(System.classifications))
    result = await db.execute(stmt_no_class)
    for s in result.scalars().all():
        notifications.append({
            "type": "missing_classification",
            "severity": "warning",
            "title": f"{s.name} saknar klassning",
            "description": "Ingen K/R/T-klassning registrerad",
            "system_id": str(s.id),
        })

    # 3. System utan ägare
    stmt_no_owner = select(System).where(~System.owners.any()).options(selectinload(System.owners))
    result = await db.execute(stmt_no_owner)
    for s in result.scalars().all():
        notifications.append({
            "type": "missing_owner",
            "severity": "warning",
            "title": f"{s.name} saknar ägare",
            "description": "Ingen systemägare eller informationsägare registrerad",
            "system_id": str(s.id),
        })

    # 4. System med personuppgifter men utan GDPR-behandling
    stmt_gdpr = (
        select(System)
        .where(System.treats_personal_data == True)  # noqa: E712
        .where(~System.gdpr_treatments.any())
        .options(selectinload(System.gdpr_treatments))
    )
    result = await db.execute(stmt_gdpr)
    for s in result.scalars().all():
        notifications.append({
            "type": "missing_gdpr_treatment",
            "severity": "critical",
            "title": f"{s.name} saknar GDPR-behandling",
            "description": "Behandlar personuppgifter men har ingen registrerad GDPR-behandling",
            "system_id": str(s.id),
        })

    # 5. Klassningar äldre än 12 månader eller med passerat valid_until (MSBFS 2020:6 §14)
    twelve_months_ago = datetime.now(timezone.utc) - timedelta(days=365)
    from sqlalchemy import and_, or_ as sa_or  # noqa: F401
    subq = (
        select(
            SystemClassification.system_id,
            func.max(SystemClassification.classified_at).label("latest"),
            func.min(SystemClassification.valid_until).label("earliest_valid_until")
        )
        .group_by(SystemClassification.system_id)
        .subquery()
    )
    stmt_stale = (
        select(System)
        .join(subq, System.id == subq.c.system_id)
        .where(
            sa_or(
                subq.c.latest < twelve_months_ago,
                and_(
                    subq.c.earliest_valid_until.is_not(None),
                    subq.c.earliest_valid_until < today,
                )
            )
        )
    )
    result = await db.execute(stmt_stale)
    for s in result.scalars().all():
        notifications.append({
            "type": "stale_classification",
            "severity": "info",
            "title": f"{s.name} behöver omklassas",
            "description": "Senaste klassning är äldre än 12 månader eller har passerat giltighetsdatum",
            "system_id": str(s.id),
        })

    # 6. NIS2-system utan riskbedömning (NIS2 Art. 21)
    stmt_nis2 = (
        select(System)
        .where(System.nis2_applicable == True)  # noqa: E712
        .where(System.last_risk_assessment_date == None)  # noqa: E711
    )
    result_nis2 = await db.execute(stmt_nis2)
    for s in result_nis2.scalars().all():
        notifications.append({
            "type": "missing_risk_assessment",
            "severity": "warning",
            "title": f"{s.name} saknar riskbedömning",
            "description": "NIS2-tillämpligt system utan registrerad riskbedömning",
            "system_id": str(s.id),
        })

    # Summering per allvarlighetsgrad
    by_severity: dict[str, int] = {}
    for n in notifications:
        by_severity[n["severity"]] = by_severity.get(n["severity"], 0) + 1

    return {
        "items": notifications[offset:offset + limit],
        "total": len(notifications),
        "limit": limit,
        "offset": offset,
        "by_severity": by_severity,
    }
