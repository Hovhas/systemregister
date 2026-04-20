"""
Test factories for creating test entities via API calls.

All factories return the JSON response dict from the API.
Use `**overrides` to customize specific fields.
"""

from datetime import date
from uuid import UUID, uuid4

from httpx import AsyncClient


async def create_org(client: AsyncClient, **overrides) -> dict:
    """Create an organization and return the response dict."""
    data = {
        "name": overrides.pop("name", f"Test Organisation {uuid4().hex[:8]}"),
        "org_number": overrides.pop("org_number", None),
        "org_type": overrides.pop("org_type", "kommun"),
        "parent_org_id": overrides.pop("parent_org_id", None),
        "description": overrides.pop("description", None),
    }
    # Convert UUID to string
    if data["parent_org_id"] and isinstance(data["parent_org_id"], UUID):
        data["parent_org_id"] = str(data["parent_org_id"])
    # Remove None values
    data = {k: v for k, v in data.items() if v is not None}
    resp = await client.post("/api/v1/organizations/", json=data)
    assert resp.status_code == 201, f"create_org failed: {resp.status_code} {resp.text}"
    return resp.json()


async def create_system(client: AsyncClient, org_id: str, **overrides) -> dict:
    """Create a system and return the response dict."""
    data = {
        "organization_id": str(org_id),
        "name": overrides.pop("name", f"Testsystem {uuid4().hex[:8]}"),
        "description": overrides.pop("description", "Ett testsystem"),
        "system_category": overrides.pop("system_category", "verksamhetssystem"),
    }
    # Merge any additional overrides
    for key, value in overrides.items():
        if isinstance(value, (date,)):
            data[key] = value.isoformat()
        elif isinstance(value, UUID):
            data[key] = str(value)
        else:
            data[key] = value
    resp = await client.post("/api/v1/systems/", json=data)
    assert resp.status_code == 201, f"create_system failed: {resp.status_code} {resp.text}"
    return resp.json()


async def create_classification(client: AsyncClient, system_id: str, **overrides) -> dict:
    """Create a classification for a system."""
    data = {
        "confidentiality": overrides.pop("confidentiality", 2),
        "integrity": overrides.pop("integrity", 2),
        "availability": overrides.pop("availability", 2),
        "traceability": overrides.pop("traceability", None),
        "classified_by": overrides.pop("classified_by", "test@test.se"),
        "valid_until": overrides.pop("valid_until", None),
        "notes": overrides.pop("notes", None),
    }
    if data["valid_until"] and isinstance(data["valid_until"], date):
        data["valid_until"] = data["valid_until"].isoformat()
    data = {k: v for k, v in data.items() if v is not None}
    resp = await client.post(f"/api/v1/systems/{system_id}/classifications", json=data)
    assert resp.status_code == 201, f"create_classification failed: {resp.status_code} {resp.text}"
    return resp.json()


async def create_owner(client: AsyncClient, system_id: str, org_id: str, **overrides) -> dict:
    """Create an owner for a system."""
    data = {
        "organization_id": str(org_id),
        "role": overrides.pop("role", "systemägare"),
        "name": overrides.pop("name", "Test Testsson"),
        "email": overrides.pop("email", None),
        "phone": overrides.pop("phone", None),
    }
    data = {k: v for k, v in data.items() if v is not None}
    resp = await client.post(f"/api/v1/systems/{system_id}/owners", json=data)
    assert resp.status_code == 201, f"create_owner failed: {resp.status_code} {resp.text}"
    return resp.json()


async def create_integration(
    client: AsyncClient, source_id: str, target_id: str, **overrides
) -> dict:
    """Create an integration between two systems."""
    data = {
        "source_system_id": str(source_id),
        "target_system_id": str(target_id),
        "integration_type": overrides.pop("integration_type", "api"),
        "data_types": overrides.pop("data_types", None),
        "frequency": overrides.pop("frequency", None),
        "description": overrides.pop("description", None),
        "criticality": overrides.pop("criticality", None),
        "is_external": overrides.pop("is_external", False),
        "external_party": overrides.pop("external_party", None),
    }
    data = {k: v for k, v in data.items() if v is not None}
    resp = await client.post("/api/v1/integrations/", json=data)
    assert resp.status_code == 201, f"create_integration failed: {resp.status_code} {resp.text}"
    return resp.json()


async def create_gdpr_treatment(client: AsyncClient, system_id: str, **overrides) -> dict:
    """Create a GDPR treatment for a system."""
    data = {
        "ropa_reference_id": overrides.pop("ropa_reference_id", None),
        "data_categories": overrides.pop("data_categories", ["vanliga"]),
        "categories_of_data_subjects": overrides.pop("categories_of_data_subjects", None),
        "legal_basis": overrides.pop("legal_basis", None),
        "data_processor": overrides.pop("data_processor", None),
        "processor_agreement_status": overrides.pop("processor_agreement_status", None),
        "sub_processors": overrides.pop("sub_processors", None),
        "third_country_transfer_details": overrides.pop("third_country_transfer_details", None),
        "retention_policy": overrides.pop("retention_policy", None),
        "dpia_conducted": overrides.pop("dpia_conducted", False),
        "dpia_date": overrides.pop("dpia_date", None),
        "dpia_link": overrides.pop("dpia_link", None),
    }
    if data.get("dpia_date") and isinstance(data["dpia_date"], date):
        data["dpia_date"] = data["dpia_date"].isoformat()
    resp = await client.post(f"/api/v1/systems/{system_id}/gdpr", json=data)
    assert resp.status_code == 201, f"create_gdpr failed: {resp.status_code} {resp.text}"
    return resp.json()


async def create_contract(client: AsyncClient, system_id: str, **overrides) -> dict:
    """Create a contract for a system."""
    data = {
        "supplier_name": overrides.pop("supplier_name", "Test Leverantör AB"),
        "supplier_org_number": overrides.pop("supplier_org_number", None),
        "contract_id_external": overrides.pop("contract_id_external", None),
        "contract_start": overrides.pop("contract_start", None),
        "contract_end": overrides.pop("contract_end", None),
        "auto_renewal": overrides.pop("auto_renewal", False),
        "notice_period_months": overrides.pop("notice_period_months", None),
        "sla_description": overrides.pop("sla_description", None),
        "license_model": overrides.pop("license_model", None),
        "annual_license_cost": overrides.pop("annual_license_cost", None),
        "annual_operations_cost": overrides.pop("annual_operations_cost", None),
        "procurement_type": overrides.pop("procurement_type", None),
        "support_level": overrides.pop("support_level", None),
    }
    if data.get("contract_start") and isinstance(data["contract_start"], date):
        data["contract_start"] = data["contract_start"].isoformat()
    if data.get("contract_end") and isinstance(data["contract_end"], date):
        data["contract_end"] = data["contract_end"].isoformat()
    resp = await client.post(f"/api/v1/systems/{system_id}/contracts", json=data)
    assert resp.status_code == 201, f"create_contract failed: {resp.status_code} {resp.text}"
    return resp.json()


# --- Convenience helpers ---

async def create_full_system(client: AsyncClient, org_id: str, **overrides) -> dict:
    """Create a system with classification, owner, GDPR treatment and contract."""
    _SYSTEM_FIELDS = {
        "name", "description", "system_category", "criticality",
        "lifecycle_status", "nis2_applicable", "nis2_classification",
        "treats_personal_data", "treats_sensitive_data",
        "hosting_model", "cloud_provider", "data_location_country",
        "backup_frequency", "rpo", "rto", "dr_plan_exists",
        "extended_attributes", "third_country_transfer",
        "product_name", "product_version", "deployment_date",
        "planned_decommission_date", "end_of_support_date",
        "last_risk_assessment_date", "klassa_reference_id",
        "has_elevated_protection", "security_protection",
        "business_area", "aliases",
        # Kategori 1–12 utökat
        "business_processes", "encryption_at_rest", "encryption_in_transit",
        "access_control_model", "retention_rules", "architecture_type",
        "environments", "last_major_upgrade", "next_planned_review",
        "backup_storage_location", "last_restore_test",
        "cost_center", "total_cost_of_ownership", "documentation_links",
        "linked_risks", "incident_history",
        # Kategori 13: AI-förordningen
        "uses_ai", "ai_risk_class", "ai_usage_description",
        "fria_status", "fria_date", "fria_link",
        "ai_human_oversight", "ai_supplier", "ai_transparency_fulfilled",
        "ai_model_version", "ai_last_review_date",
        # Entitetshierarki
        "objekt_id",
    }
    sys = await create_system(client, org_id, **{
        k: v for k, v in overrides.items() if k in _SYSTEM_FIELDS
    })
    sid = sys["id"]
    await create_classification(client, sid)
    await create_owner(client, sid, org_id)
    if overrides.get("treats_personal_data", False):
        await create_gdpr_treatment(client, sid)
    await create_contract(client, sid)
    return sys


async def create_objekt(client: AsyncClient, org_id: str, **overrides) -> dict:
    """Create an objekt (förvaltningsobjekt) and return the response dict."""
    data = {
        "organization_id": str(org_id),
        "name": overrides.pop("name", "Testobjekt"),
        "description": overrides.pop("description", "Ett testobjekt"),
        "object_owner": overrides.pop("object_owner", None),
        "object_leader": overrides.pop("object_leader", None),
    }
    data = {k: v for k, v in data.items() if v is not None}
    resp = await client.post("/api/v1/objekt/", json=data)
    assert resp.status_code == 201, f"create_objekt failed: {resp.status_code} {resp.text}"
    return resp.json()


async def create_component(client: AsyncClient, system_id: str, org_id: str, **overrides) -> dict:
    """Create a component and return the response dict."""
    data = {
        "system_id": str(system_id),
        "organization_id": str(org_id),
        "name": overrides.pop("name", "Testkomponent"),
        "description": overrides.pop("description", None),
        "component_type": overrides.pop("component_type", None),
        "url": overrides.pop("url", None),
        "business_area": overrides.pop("business_area", None),
    }
    data = {k: v for k, v in data.items() if v is not None}
    resp = await client.post("/api/v1/components/", json=data)
    assert resp.status_code == 201, f"create_component failed: {resp.status_code} {resp.text}"
    return resp.json()


async def create_module(client: AsyncClient, org_id: str, **overrides) -> dict:
    """Create a module and return the response dict."""
    data = {
        "organization_id": str(org_id),
        "name": overrides.pop("name", "Testmodul"),
        "description": overrides.pop("description", None),
        "lifecycle_status": overrides.pop("lifecycle_status", None),
        "uses_ai": overrides.pop("uses_ai", False),
        "ai_risk_class": overrides.pop("ai_risk_class", None),
    }
    data = {k: v for k, v in data.items() if v is not None}
    resp = await client.post("/api/v1/modules/", json=data)
    assert resp.status_code == 201, f"create_module failed: {resp.status_code} {resp.text}"
    return resp.json()


async def create_information_asset(client: AsyncClient, org_id: str, **overrides) -> dict:
    """Create an information asset and return the response dict."""
    data = {
        "organization_id": str(org_id),
        "name": overrides.pop("name", "Testinformationsmängd"),
        "description": overrides.pop("description", None),
        "information_owner": overrides.pop("information_owner", None),
        "confidentiality": overrides.pop("confidentiality", None),
        "integrity": overrides.pop("integrity", None),
        "availability": overrides.pop("availability", None),
        "contains_personal_data": overrides.pop("contains_personal_data", False),
        "contains_public_records": overrides.pop("contains_public_records", False),
    }
    data = {k: v for k, v in data.items() if v is not None}
    resp = await client.post("/api/v1/information-assets/", json=data)
    assert resp.status_code == 201, f"create_information_asset failed: {resp.status_code} {resp.text}"
    return resp.json()


async def create_approval(client: AsyncClient, org_id: str, **overrides) -> dict:
    """Create an approval request and return the response dict."""
    data = {
        "organization_id": str(org_id),
        "approval_type": overrides.pop("approval_type", "systemregistrering"),
        "title": overrides.pop("title", "Testärende"),
        "description": overrides.pop("description", None),
        "target_table": overrides.pop("target_table", None),
        "target_record_id": overrides.pop("target_record_id", None),
        "proposed_changes": overrides.pop("proposed_changes", None),
        "requested_by": overrides.pop("requested_by", None),
    }
    if data.get("target_record_id"):
        data["target_record_id"] = str(data["target_record_id"])
    data = {k: v for k, v in data.items() if v is not None}
    resp = await client.post("/api/v1/approvals/", json=data)
    assert resp.status_code == 201, f"create_approval failed: {resp.status_code} {resp.text}"
    return resp.json()


async def create_two_orgs_with_systems(client: AsyncClient) -> dict:
    """Create two orgs with systems for RLS testing. Returns dict with org/system IDs."""
    org_a = await create_org(client, name="Org A", org_type="kommun")
    org_b = await create_org(client, name="Org B", org_type="bolag")
    sys_a = await create_system(client, org_a["id"], name="System A")
    sys_b = await create_system(client, org_b["id"], name="System B")
    return {
        "org_a": org_a, "org_b": org_b,
        "sys_a": sys_a, "sys_b": sys_b,
    }
