from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse, StreamingResponse
from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import Contract, GDPRTreatment, System, SystemClassification, SystemOwner
from app.schemas import ComplianceGapResponse, NIS2ReportResponse

router = APIRouter(prefix="/reports", tags=["Rapporter"])


async def _get_nis2_systems(db: AsyncSession) -> list[System]:
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
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/nis2", response_model=NIS2ReportResponse)
async def nis2_report(db: AsyncSession = Depends(get_db)):
    """NIS2-compliance-rapport med sammanfattning och systemlista."""
    systems = await _get_nis2_systems(db)

    without_classification = sum(1 for s in systems if s.nis2_classification is None)
    without_risk_assessment = sum(1 for s in systems if s.last_risk_assessment_date is None)

    system_entries = []
    for s in systems:
        system_entries.append(
            {
                "id": str(s.id),
                "name": s.name,
                "organization_id": str(s.organization_id),
                "nis2_classification": s.nis2_classification.value if s.nis2_classification else None,
                "criticality": s.criticality.value,
                "last_risk_assessment_date": s.last_risk_assessment_date.isoformat() if s.last_risk_assessment_date else None,
                "has_gdpr_treatment": len(s.gdpr_treatments) > 0,
                "owner_names": [o.name for o in s.owners],
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": len(systems),
            "without_classification": without_classification,
            "without_risk_assessment": without_risk_assessment,
        },
        "systems": system_entries,
    }


@router.get("/nis2.xlsx")
async def nis2_report_xlsx(db: AsyncSession = Depends(get_db)):
    """NIS2-compliance-rapport som Excel-fil."""
    systems = await _get_nis2_systems(db)

    wb = Workbook()
    ws = wb.active
    ws.title = "NIS2-system"

    headers = [
        "Namn",
        "Organisation-ID",
        "NIS2-klass",
        "Kritikalitet",
        "Senaste riskbedömning",
        "Personuppgifter",
    ]
    ws.append(headers)

    for s in systems:
        ws.append(
            [
                s.name,
                str(s.organization_id),
                s.nis2_classification.value if s.nis2_classification else "",
                s.criticality.value,
                s.last_risk_assessment_date.isoformat() if s.last_risk_assessment_date else "",
                "Ja" if len(s.gdpr_treatments) > 0 else "Nej",
            ]
        )

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=nis2-rapport.xlsx"},
    )


_REPORT_CSS = """
    body { font-family: Arial, sans-serif; font-size: 12px; margin: 2cm; color: #000; }
    h1 { font-size: 18px; margin-bottom: 4px; }
    h2 { font-size: 15px; margin-top: 24px; margin-bottom: 8px; }
    .meta { color: #555; margin-bottom: 16px; }
    .summary { background: #f5f5f5; padding: 12px; margin-bottom: 20px; border: 1px solid #ddd; }
    .summary h2 { font-size: 14px; margin: 0 0 8px 0; }
    .summary ul { margin: 0; padding-left: 18px; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 24px; }
    th { background: #2c5282; color: #fff; text-align: left; padding: 6px 8px; }
    td { padding: 5px 8px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
    tr:nth-child(even) { background: #f7fafc; }
    .no-gaps { color: #276749; font-style: italic; }
    @media print {
        body { margin: 1cm; }
        .summary { break-inside: avoid; }
        tr { break-inside: avoid; }
    }
"""


def _render_nis2_html(systems: list[System]) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = len(systems)
    without_classification = sum(1 for s in systems if s.nis2_classification is None)
    without_risk = sum(1 for s in systems if s.last_risk_assessment_date is None)

    rows = ""
    for s in systems:
        classification = s.nis2_classification.value if s.nis2_classification else "—"
        risk_date = s.last_risk_assessment_date.isoformat() if s.last_risk_assessment_date else "—"
        personal_data = "Ja" if len(s.gdpr_treatments) > 0 else "Nej"
        owners = ", ".join(o.name for o in s.owners) or "—"
        rows += f"""
        <tr>
            <td>{s.name}</td>
            <td>{classification}</td>
            <td>{s.criticality.value}</td>
            <td>{risk_date}</td>
            <td>{personal_data}</td>
            <td>{owners}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>NIS2-rapport — Sundsvalls kommunkoncern</title>
    <style>{_REPORT_CSS}</style>
</head>
<body>
    <h1>NIS2-compliance-rapport</h1>
    <p class="meta">Sundsvalls kommunkoncern &mdash; Genererad: {generated_at}</p>

    <div class="summary">
        <h2>Sammanfattning</h2>
        <ul>
            <li>Totalt NIS2-klassade system: <strong>{total}</strong></li>
            <li>Utan NIS2-klassificering: <strong>{without_classification}</strong></li>
            <li>Utan riskbedomning: <strong>{without_risk}</strong></li>
        </ul>
    </div>

    <table>
        <thead>
            <tr>
                <th>Namn</th>
                <th>NIS2-klass</th>
                <th>Kritikalitet</th>
                <th>Senaste riskbedomning</th>
                <th>Personuppgifter</th>
                <th>Agare</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</body>
</html>"""


def _render_compliance_gap_html(gap_data: dict) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_gaps = gap_data["summary"]["total_gaps"]
    gaps = gap_data["gaps"]

    def _system_rows(items: list[dict]) -> str:
        if not items:
            return '<tr><td colspan="2" class="no-gaps">Inga gap hittades</td></tr>'
        return "".join(
            f"<tr><td>{i['name']}</td><td>{i['organization_id']}</td></tr>"
            for i in items
        )

    def _contract_rows(items: list[dict]) -> str:
        if not items:
            return '<tr><td colspan="3" class="no-gaps">Inga utgaende avtal</td></tr>'
        return "".join(
            f"<tr><td>{c['supplier_name'] or '—'}</td>"
            f"<td>{c['system_id']}</td>"
            f"<td>{c['contract_end'] or '—'}</td></tr>"
            for c in items
        )

    return f"""<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="UTF-8">
    <title>Compliance-gap-rapport — Sundsvalls kommunkoncern</title>
    <style>{_REPORT_CSS}</style>
</head>
<body>
    <h1>Compliance-gap-rapport</h1>
    <p class="meta">Sundsvalls kommunkoncern &mdash; Genererad: {generated_at}</p>

    <div class="summary">
        <h2>Sammanfattning</h2>
        <ul>
            <li>Totalt antal gap: <strong>{total_gaps}</strong></li>
            <li>System utan klassning: <strong>{len(gaps['missing_classification'])}</strong></li>
            <li>System utan agare: <strong>{len(gaps['missing_owner'])}</strong></li>
            <li>Personuppgifter utan GDPR-behandling: <strong>{len(gaps['personal_data_without_gdpr'])}</strong></li>
            <li>NIS2-system utan riskbedomning: <strong>{len(gaps['nis2_without_risk_assessment'])}</strong></li>
            <li>Utgaende avtal (90 dagar): <strong>{len(gaps['expiring_contracts'])}</strong></li>
        </ul>
    </div>

    <h2>System utan klassning</h2>
    <table>
        <thead><tr><th>Namn</th><th>Organisation-ID</th></tr></thead>
        <tbody>{_system_rows(gaps['missing_classification'])}</tbody>
    </table>

    <h2>System utan agare</h2>
    <table>
        <thead><tr><th>Namn</th><th>Organisation-ID</th></tr></thead>
        <tbody>{_system_rows(gaps['missing_owner'])}</tbody>
    </table>

    <h2>Personuppgifter utan GDPR-behandling</h2>
    <table>
        <thead><tr><th>Namn</th><th>Organisation-ID</th></tr></thead>
        <tbody>{_system_rows(gaps['personal_data_without_gdpr'])}</tbody>
    </table>

    <h2>NIS2-system utan riskbedomning</h2>
    <table>
        <thead><tr><th>Namn</th><th>Organisation-ID</th></tr></thead>
        <tbody>{_system_rows(gaps['nis2_without_risk_assessment'])}</tbody>
    </table>

    <h2>Utgaende avtal (inom 90 dagar)</h2>
    <table>
        <thead><tr><th>Leverantor</th><th>System-ID</th><th>Avtalsslutt</th></tr></thead>
        <tbody>{_contract_rows(gaps['expiring_contracts'])}</tbody>
    </table>
</body>
</html>"""


@router.get("/nis2.html", response_class=HTMLResponse)
async def nis2_report_html(db: AsyncSession = Depends(get_db)):
    """Print-vanlig HTML-rapport over NIS2-system."""
    systems = await _get_nis2_systems(db)
    return HTMLResponse(content=_render_nis2_html(systems))


@router.get("/nis2.pdf")
async def nis2_report_pdf(db: AsyncSession = Depends(get_db)):
    """NIS2-compliance-rapport som PDF."""
    from weasyprint import HTML as WeasyHTML
    systems = await _get_nis2_systems(db)
    html = _render_nis2_html(systems)
    pdf_bytes = WeasyHTML(string=html).write_pdf()
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=nis2-rapport.pdf"},
    )


async def _get_compliance_gap_data(db: AsyncSession) -> dict:
    """Samlar compliance-gap-data. Återanvänds av JSON- och PDF-endpoints."""
    stmt_no_class = select(System).where(~System.classifications.any())
    result = await db.execute(stmt_no_class.options(selectinload(System.classifications)))
    systems_no_class = [
        {"id": str(s.id), "name": str(s.name), "organization_id": str(s.organization_id)}
        for s in result.scalars().all()
    ]

    stmt_no_owner = select(System).where(~System.owners.any())
    result = await db.execute(stmt_no_owner.options(selectinload(System.owners)))
    systems_no_owner = [
        {"id": str(s.id), "name": str(s.name), "organization_id": str(s.organization_id)}
        for s in result.scalars().all()
    ]

    stmt_personal_no_gdpr = (
        select(System)
        .where(System.treats_personal_data == True)  # noqa: E712
        .where(~System.gdpr_treatments.any())
    )
    result = await db.execute(stmt_personal_no_gdpr.options(selectinload(System.gdpr_treatments)))
    personal_no_gdpr = [
        {"id": str(s.id), "name": str(s.name), "organization_id": str(s.organization_id)}
        for s in result.scalars().all()
    ]

    stmt_nis2_no_risk = (
        select(System)
        .where(System.nis2_applicable == True)  # noqa: E712
        .where(System.last_risk_assessment_date == None)  # noqa: E711
    )
    result = await db.execute(stmt_nis2_no_risk)
    nis2_no_risk = [
        {"id": str(s.id), "name": str(s.name), "organization_id": str(s.organization_id)}
        for s in result.scalars().all()
    ]

    cutoff = date.today() + timedelta(days=90)
    stmt_expiring = (
        select(Contract)
        .where(Contract.contract_end.is_not(None))
        .where(Contract.contract_end <= cutoff)
        .where(Contract.contract_end >= date.today())
        .order_by(Contract.contract_end)
    )
    result = await db.execute(stmt_expiring)
    expiring = [
        {
            "id": str(c.id),
            "system_id": str(c.system_id),
            "supplier_name": c.supplier_name,
            "contract_end": c.contract_end.isoformat() if c.contract_end else None,
        }
        for c in result.scalars().all()
    ]

    total_gaps = (
        len(systems_no_class)
        + len(systems_no_owner)
        + len(personal_no_gdpr)
        + len(nis2_no_risk)
        + len(expiring)
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
        "summary": {
            "total_gaps": total_gaps,
        },
    }


@router.get("/compliance-gap", response_model=ComplianceGapResponse)
async def compliance_gap(db: AsyncSession = Depends(get_db)):
    """Compliance-gap-analys — identifierar system med ofullstandig dokumentation."""
    return await _get_compliance_gap_data(db)


@router.get("/compliance-gap.pdf")
async def compliance_gap_pdf(db: AsyncSession = Depends(get_db)):
    """Compliance-gap-rapport som PDF."""
    from weasyprint import HTML as WeasyHTML
    gap_data = await _get_compliance_gap_data(db)
    html = _render_compliance_gap_html(gap_data)
    pdf_bytes = WeasyHTML(string=html).write_pdf()
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=compliance-gap-rapport.pdf"},
    )
