import uuid
from datetime import datetime, date

from sqlalchemy import (
    String, Text, Boolean, Integer, Date, DateTime,
    ForeignKey, Enum as SAEnum, UniqueConstraint, Index, CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import (
    OrganizationType, SystemCategory, LifecycleStatus, Criticality,
    OwnerRole, IntegrationType, ProcessorAgreementStatus,
    NIS2Classification, AuditAction, AIRiskClass, FRIAStatus,
    ApprovalStatus, ApprovalType, OrgUnitType, AccessLevel, AccessType,
)


def _enum(enum_cls):
    """SAEnum that uses .value (lowercase Swedish) instead of .name (UPPERCASE)."""
    return SAEnum(enum_cls, values_callable=lambda e: [x.value for x in e])


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    org_number: Mapped[str | None] = mapped_column(String(20), unique=True)
    org_type: Mapped[OrganizationType] = mapped_column(_enum(OrganizationType), nullable=False)
    parent_org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id", ondelete="SET NULL"))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    systems: Mapped[list["System"]] = relationship(back_populates="organization")
    objekt: Mapped[list["Objekt"]] = relationship(back_populates="organization")
    children: Mapped[list["Organization"]] = relationship(back_populates="parent")
    parent: Mapped["Organization | None"] = relationship(back_populates="children", remote_side=[id])


class System(Base):
    __tablename__ = "systems"

    # --- Kategori 1: Grundläggande identifiering ---
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    aliases: Mapped[str | None] = mapped_column(Text)  # Kommaseparerade alternativa namn
    description: Mapped[str] = mapped_column(Text, nullable=False)
    system_category: Mapped[SystemCategory] = mapped_column(_enum(SystemCategory), nullable=False)
    business_area: Mapped[str | None] = mapped_column(String(255))  # Verksamhetsområde
    business_processes: Mapped[str | None] = mapped_column(Text)  # 1.6 Verksamhetsprocesser (kommasep.)

    # --- Kategori 3: Klassning & säkerhet (senaste aktiva) ---
    criticality: Mapped[Criticality] = mapped_column(_enum(Criticality), default=Criticality.MEDIUM)
    has_elevated_protection: Mapped[bool] = mapped_column(Boolean, default=False)  # MSBFS 2020:7 §4 p.3
    security_protection: Mapped[bool] = mapped_column(Boolean, default=False)  # Säkerhetsskyddslagen
    nis2_applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    nis2_classification: Mapped[NIS2Classification | None] = mapped_column(_enum(NIS2Classification))
    encryption_at_rest: Mapped[str | None] = mapped_column(String(255))  # 3.10 Kryptering at rest
    encryption_in_transit: Mapped[str | None] = mapped_column(String(255))  # 3.10 Kryptering in transit
    access_control_model: Mapped[str | None] = mapped_column(String(255))  # 3.11 AD/RBAC/SSO, MFA ja/nej

    # --- Kategori 4: GDPR grundflaggor ---
    treats_personal_data: Mapped[bool] = mapped_column(Boolean, default=False)
    treats_sensitive_data: Mapped[bool] = mapped_column(Boolean, default=False)  # Art. 9
    third_country_transfer: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Kategori 4b: GDPR utökat ---
    retention_rules: Mapped[str | None] = mapped_column(Text)  # 4.10 Gallringsregler/bevarandetider

    # --- Kategori 5: Driftmiljö ---
    hosting_model: Mapped[str | None] = mapped_column(String(50))  # on-premise / cloud / hybrid
    cloud_provider: Mapped[str | None] = mapped_column(String(255))
    data_location_country: Mapped[str | None] = mapped_column(String(100), default="Sverige")
    product_name: Mapped[str | None] = mapped_column(String(255))
    product_version: Mapped[str | None] = mapped_column(String(100))
    architecture_type: Mapped[str | None] = mapped_column(String(100))  # 5.6 Monolitisk/Microservices/Serverless
    environments: Mapped[str | None] = mapped_column(String(255))  # 5.7 Produktion/Test/Utveckling/Staging

    # --- Kategori 6: Livscykel ---
    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(
        _enum(LifecycleStatus), default=LifecycleStatus.ACTIVE
    )
    deployment_date: Mapped[date | None] = mapped_column(Date)
    planned_decommission_date: Mapped[date | None] = mapped_column(Date)
    end_of_support_date: Mapped[date | None] = mapped_column(Date)
    last_major_upgrade: Mapped[str | None] = mapped_column(String(255))  # 6.5 Datum + version
    next_planned_review: Mapped[date | None] = mapped_column(Date)  # 6.6 Nästa planerade review

    # --- Kategori 9: Backup/DR ---
    backup_frequency: Mapped[str | None] = mapped_column(String(100))
    rpo: Mapped[str | None] = mapped_column(String(100))
    rto: Mapped[str | None] = mapped_column(String(100))
    dr_plan_exists: Mapped[bool] = mapped_column(Boolean, default=False)
    backup_storage_location: Mapped[str | None] = mapped_column(String(255))  # 9.5 Var lagras backup
    last_restore_test: Mapped[str | None] = mapped_column(String(255))  # 9.6 Datum + resultat

    # --- Kategori 10: Kostnader utökat ---
    cost_center: Mapped[str | None] = mapped_column(String(255))  # 10.3 Kostnadsbärare
    total_cost_of_ownership: Mapped[int | None] = mapped_column(Integer)  # 10.4 TCO i SEK

    # --- Kategori 11: Dokumentation utökat ---
    documentation_links: Mapped[list | None] = mapped_column(JSONB)  # 11.1 Lista av URL:er

    # --- Kategori 12: Compliance ---
    last_risk_assessment_date: Mapped[date | None] = mapped_column(Date)
    klassa_reference_id: Mapped[str | None] = mapped_column(String(100))
    linked_risks: Mapped[str | None] = mapped_column(Text)  # 12.4 Koppling till riskregister
    incident_history: Mapped[str | None] = mapped_column(Text)  # 12.5 Incidenthistorik

    # --- Kategori 13: AI-förordningen (EU 2024/1689) ---
    uses_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_risk_class: Mapped[AIRiskClass | None] = mapped_column(_enum(AIRiskClass))
    ai_usage_description: Mapped[str | None] = mapped_column(Text)
    fria_status: Mapped[FRIAStatus | None] = mapped_column(_enum(FRIAStatus))
    fria_date: Mapped[date | None] = mapped_column(Date)
    fria_link: Mapped[str | None] = mapped_column(Text)
    ai_human_oversight: Mapped[str | None] = mapped_column(String(255))
    ai_supplier: Mapped[str | None] = mapped_column(String(255))
    ai_transparency_fulfilled: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_model_version: Mapped[str | None] = mapped_column(String(255))
    ai_last_review_date: Mapped[date | None] = mapped_column(Date)

    # --- Entitetshierarki ---
    objekt_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("objekt.id", ondelete="SET NULL"))

    # --- SBOM ---
    license_id: Mapped[str | None] = mapped_column(String(100))
    cpe: Mapped[str | None] = mapped_column(String(500))
    purl: Mapped[str | None] = mapped_column(String(500))

    # --- Metakatalog ---
    metakatalog_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    metakatalog_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # --- Flexibla attribut ---
    extended_attributes: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # --- Meta ---
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reviewed_by: Mapped[str | None] = mapped_column(String(255))

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="systems")
    objekt: Mapped["Objekt | None"] = relationship(back_populates="systems")
    classifications: Mapped[list["SystemClassification"]] = relationship(
        back_populates="system", order_by="desc(SystemClassification.classified_at)",
        passive_deletes=True,
    )
    owners: Mapped[list["SystemOwner"]] = relationship(back_populates="system", passive_deletes=True)
    integrations_out: Mapped[list["SystemIntegration"]] = relationship(
        back_populates="source_system", foreign_keys="SystemIntegration.source_system_id",
        passive_deletes=True,
    )
    integrations_in: Mapped[list["SystemIntegration"]] = relationship(
        back_populates="target_system", foreign_keys="SystemIntegration.target_system_id",
        passive_deletes=True,
    )
    gdpr_treatments: Mapped[list["GDPRTreatment"]] = relationship(back_populates="system", passive_deletes=True)
    contracts: Mapped[list["Contract"]] = relationship(back_populates="system", passive_deletes=True)
    components: Mapped[list["Component"]] = relationship(back_populates="system", passive_deletes=True)
    modules_used: Mapped[list["Module"]] = relationship(secondary="module_system_link", back_populates="systems")
    information_assets: Mapped[list["InformationAsset"]] = relationship(
        secondary="information_asset_system_link", back_populates="systems"
    )
    capabilities: Mapped[list["BusinessCapability"]] = relationship(
        secondary="capability_system_link", back_populates="systems"
    )
    processes: Mapped[list["BusinessProcess"]] = relationship(
        secondary="process_system_link", back_populates="systems"
    )
    role_accesses: Mapped[list["RoleSystemAccess"]] = relationship(
        back_populates="system", passive_deletes=True,
    )

    __table_args__ = (
        Index("ix_systems_org_name", "organization_id", "name"),
        Index("ix_systems_lifecycle", "lifecycle_status"),
        Index("ix_systems_criticality", "criticality"),
    )


class SystemClassification(Base):
    """Historisk K/R/T-klassning. Ny rad per klassning."""
    __tablename__ = "system_classifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("systems.id", ondelete="CASCADE"), nullable=False, index=True)
    confidentiality: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-4
    integrity: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-4
    availability: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-4
    traceability: Mapped[int | None] = mapped_column(Integer)  # 0-4, optional
    classified_by: Mapped[str] = mapped_column(String(255), nullable=False)
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    valid_until: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)

    system: Mapped["System"] = relationship(back_populates="classifications")


class SystemOwner(Base):
    """Roller/ansvariga per system."""
    __tablename__ = "system_owners"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("systems.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    role: Mapped[OwnerRole] = mapped_column(_enum(OwnerRole), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    system: Mapped["System"] = relationship(back_populates="owners")

    __table_args__ = (
        UniqueConstraint("system_id", "role", "name", name="uq_system_owner_role"),
    )


class SystemIntegration(Base):
    """Integrationer/beroenden mellan system."""
    __tablename__ = "system_integrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_system_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("systems.id", ondelete="CASCADE"), nullable=False, index=True)
    target_system_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("systems.id", ondelete="CASCADE"), nullable=False, index=True)
    integration_type: Mapped[IntegrationType] = mapped_column(_enum(IntegrationType), nullable=False)
    data_types: Mapped[str | None] = mapped_column(Text)
    frequency: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    criticality: Mapped[Criticality | None] = mapped_column(
        SAEnum(Criticality, name="criticality", values_callable=lambda e: [x.value for x in e])
    )
    is_external: Mapped[bool] = mapped_column(Boolean, default=False)  # MSBFS 2020:7 §4 p.2
    external_party: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_system: Mapped["System"] = relationship(back_populates="integrations_out", foreign_keys=[source_system_id])
    target_system: Mapped["System"] = relationship(back_populates="integrations_in", foreign_keys=[target_system_id])


class GDPRTreatment(Base):
    """ROPA-koppling per system."""
    __tablename__ = "gdpr_treatments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("systems.id", ondelete="CASCADE"), nullable=False, index=True)
    ropa_reference_id: Mapped[str | None] = mapped_column(String(100))
    data_categories: Mapped[list | None] = mapped_column(JSONB)  # ["vanliga", "känsliga_art9", "brottsdata_art10"]
    categories_of_data_subjects: Mapped[str | None] = mapped_column(Text)  # medborgare, anställda, elever...
    legal_basis: Mapped[str | None] = mapped_column(String(255))
    data_processor: Mapped[str | None] = mapped_column(String(255))
    processor_agreement_status: Mapped[ProcessorAgreementStatus | None] = mapped_column(
        _enum(ProcessorAgreementStatus)
    )
    sub_processors: Mapped[list | None] = mapped_column(JSONB)
    third_country_transfer_details: Mapped[str | None] = mapped_column(Text)
    retention_policy: Mapped[str | None] = mapped_column(Text)
    dpia_conducted: Mapped[bool] = mapped_column(Boolean, default=False)
    dpia_date: Mapped[date | None] = mapped_column(Date)
    dpia_link: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    system: Mapped["System"] = relationship(back_populates="gdpr_treatments")


class Contract(Base):
    """Avtal och leverantörer kopplade till system."""
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("systems.id", ondelete="CASCADE"), nullable=False, index=True)
    supplier_name: Mapped[str] = mapped_column(String(255), nullable=False)
    supplier_org_number: Mapped[str | None] = mapped_column(String(20))
    contract_id_external: Mapped[str | None] = mapped_column(String(100))
    contract_start: Mapped[date | None] = mapped_column(Date)
    contract_end: Mapped[date | None] = mapped_column(Date)
    auto_renewal: Mapped[bool] = mapped_column(Boolean, default=False)
    notice_period_months: Mapped[int | None] = mapped_column(Integer)
    sla_description: Mapped[str | None] = mapped_column(Text)
    license_model: Mapped[str | None] = mapped_column(String(100))
    annual_license_cost: Mapped[int | None] = mapped_column(Integer)  # SEK
    annual_operations_cost: Mapped[int | None] = mapped_column(Integer)  # SEK
    procurement_type: Mapped[str | None] = mapped_column(String(100))
    support_level: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    system: Mapped["System"] = relationship(back_populates="contracts")


class AuditLog(Base):
    """Automatisk ändringslogg."""
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    table_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    action: Mapped[AuditAction] = mapped_column(_enum(AuditAction), nullable=False)
    changed_by: Mapped[str | None] = mapped_column(String(255))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    old_values: Mapped[dict | None] = mapped_column(JSONB)
    new_values: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(45))

    __table_args__ = (
        Index("ix_audit_log_table_record", "table_name", "record_id"),
        Index("ix_audit_log_changed_at", "changed_at"),
    )


# ============================================================
# Entitetshierarki (Kravspec avsnitt 3)
# ============================================================


class Objekt(Base):
    """Förvaltningsobjekt — aggregerar system, moduler och komponenter."""
    __tablename__ = "objekt"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    object_owner: Mapped[str | None] = mapped_column(String(255))
    object_leader: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="objekt")
    systems: Mapped[list["System"]] = relationship(back_populates="objekt")


class Component(Base):
    """Komponent — del av ett system. Ärver systemets grundattribut men kan ha egna."""
    __tablename__ = "components"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    system_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("systems.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    component_type: Mapped[str | None] = mapped_column(String(100))  # webbsida, kartvy, instans, etc.
    url: Mapped[str | None] = mapped_column(Text)
    business_area: Mapped[str | None] = mapped_column(String(255))  # Eget verksamhetsområde (override)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    system: Mapped["System"] = relationship(back_populates="components")
    organization: Mapped["Organization"] = relationship()


class Module(Base):
    """Modul — återanvändbar mikrotjänst/funktion. N:M-relation till system."""
    __tablename__ = "modules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    lifecycle_status: Mapped[LifecycleStatus | None] = mapped_column(_enum(LifecycleStatus))
    hosting_model: Mapped[str | None] = mapped_column(String(50))
    product_name: Mapped[str | None] = mapped_column(String(255))
    product_version: Mapped[str | None] = mapped_column(String(100))
    # AI-förordningen — moduler kan ha AI-komponenter
    uses_ai: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_risk_class: Mapped[AIRiskClass | None] = mapped_column(_enum(AIRiskClass))
    ai_usage_description: Mapped[str | None] = mapped_column(Text)
    # SBOM
    license_id: Mapped[str | None] = mapped_column(String(100))
    cpe: Mapped[str | None] = mapped_column(String(500))
    purl: Mapped[str | None] = mapped_column(String(500))
    supplier: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization: Mapped["Organization"] = relationship()
    systems: Mapped[list["System"]] = relationship(secondary="module_system_link", back_populates="modules_used")


class Approval(Base):
    """Godkännandeärende — arbetsflöde för ändringar som kräver granskning (FK-15)."""
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    approval_type: Mapped[ApprovalType] = mapped_column(_enum(ApprovalType), nullable=False)
    status: Mapped[ApprovalStatus] = mapped_column(_enum(ApprovalStatus), default=ApprovalStatus.PENDING)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Vad ärendet gäller
    target_table: Mapped[str | None] = mapped_column(String(100))  # systems, gdpr_treatments, etc.
    target_record_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    proposed_changes: Mapped[dict | None] = mapped_column(JSONB)  # JSON med föreslagna ändringar
    # Vem
    requested_by: Mapped[str | None] = mapped_column(String(255))
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    review_comment: Mapped[str | None] = mapped_column(Text)
    # När
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        Index("ix_approvals_status", "status"),
        Index("ix_approvals_target", "target_table", "target_record_id"),
    )


# Junction table for Module ↔ System (N:M)
from sqlalchemy import Table, Column  # noqa: E402
module_system_link = Table(
    "module_system_link",
    Base.metadata,
    Column("module_id", UUID(as_uuid=True), ForeignKey("modules.id", ondelete="CASCADE"), primary_key=True),
    Column("system_id", UUID(as_uuid=True), ForeignKey("systems.id", ondelete="CASCADE"), primary_key=True),
)


class InformationAsset(Base):
    """Informationsmängd — sammanhållen uppsättning data med gemensamt syfte."""
    __tablename__ = "information_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    information_owner: Mapped[str | None] = mapped_column(String(255))
    # K/R/T-klassning (egen, inte ärvd)
    confidentiality: Mapped[int | None] = mapped_column(Integer)  # 0-4
    integrity: Mapped[int | None] = mapped_column(Integer)  # 0-4
    availability: Mapped[int | None] = mapped_column(Integer)  # 0-4
    traceability: Mapped[int | None] = mapped_column(Integer)  # 0-4
    # Personuppgifter
    contains_personal_data: Mapped[bool] = mapped_column(Boolean, default=False)
    personal_data_type: Mapped[str | None] = mapped_column(String(100))  # vanliga/känsliga/brottsdata
    contains_public_records: Mapped[bool] = mapped_column(Boolean, default=False)  # Allmänna handlingar
    ropa_reference_id: Mapped[str | None] = mapped_column(String(100))
    # Informationshantering & arkiv (kategori 15)
    ihp_reference: Mapped[str | None] = mapped_column(Text)  # Koppling till IHP
    preservation_class: Mapped[str | None] = mapped_column(String(100))  # bevara/gallra/ej_klassificerad
    retention_period: Mapped[str | None] = mapped_column(String(255))  # Gallringsfrist
    archive_responsible: Mapped[str | None] = mapped_column(String(255))
    e_archive_delivery: Mapped[str | None] = mapped_column(String(100))  # ja/nej/planerad
    long_term_format: Mapped[str | None] = mapped_column(String(255))  # PDF/A, TIFF, XML
    last_ihp_review: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    organization: Mapped["Organization"] = relationship()
    systems: Mapped[list["System"]] = relationship(
        secondary="information_asset_system_link", back_populates="information_assets"
    )
    processes: Mapped[list["BusinessProcess"]] = relationship(
        secondary="process_information_link", back_populates="information_assets"
    )


# Junction table for InformationAsset ↔ System (N:M)
information_asset_system_link = Table(
    "information_asset_system_link",
    Base.metadata,
    Column("information_asset_id", UUID(as_uuid=True), ForeignKey("information_assets.id", ondelete="CASCADE"), primary_key=True),
    Column("system_id", UUID(as_uuid=True), ForeignKey("systems.id", ondelete="CASCADE"), primary_key=True),
)


# ============================================================
# Paket A — Verksamhetsskikt
# ============================================================


class BusinessCapability(Base):
    """Verksamhetsförmåga (ArchiMate Capability). Hierarkisk."""
    __tablename__ = "business_capabilities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    parent_capability_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("business_capabilities.id", ondelete="SET NULL"), index=True,
    )
    capability_owner: Mapped[str | None] = mapped_column(String(255))
    maturity_level: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    parent: Mapped["BusinessCapability | None"] = relationship(
        back_populates="children", remote_side=[id],
    )
    children: Mapped[list["BusinessCapability"]] = relationship(back_populates="parent")
    systems: Mapped[list["System"]] = relationship(
        secondary="capability_system_link", back_populates="capabilities",
    )
    processes: Mapped[list["BusinessProcess"]] = relationship(
        secondary="process_capability_link", back_populates="capabilities",
    )
    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        Index("ix_capabilities_org_name", "organization_id", "name"),
        CheckConstraint(
            "maturity_level IS NULL OR (maturity_level BETWEEN 0 AND 5)",
            name="ck_capability_maturity_range",
        ),
    )


class BusinessProcess(Base):
    """Verksamhetsprocess. Hierarkisk (huvud-/delprocess)."""
    __tablename__ = "business_processes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    parent_process_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("business_processes.id", ondelete="SET NULL"), index=True,
    )
    process_owner: Mapped[str | None] = mapped_column(String(255))
    criticality: Mapped[Criticality | None] = mapped_column(_enum(Criticality))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    parent: Mapped["BusinessProcess | None"] = relationship(
        back_populates="children", remote_side=[id],
    )
    children: Mapped[list["BusinessProcess"]] = relationship(back_populates="parent")
    systems: Mapped[list["System"]] = relationship(
        secondary="process_system_link", back_populates="processes",
    )
    capabilities: Mapped[list["BusinessCapability"]] = relationship(
        secondary="process_capability_link", back_populates="processes",
    )
    information_assets: Mapped[list["InformationAsset"]] = relationship(
        secondary="process_information_link", back_populates="processes",
    )
    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        Index("ix_processes_org_name", "organization_id", "name"),
    )


class ValueStream(Base):
    """Värdeström. Stages som JSONB-lista av {name, description, order}."""
    __tablename__ = "value_streams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    stages: Mapped[list | None] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        Index("ix_value_streams_org_name", "organization_id", "name"),
    )


class OrgUnit(Base):
    """Organisationsenhet inom en organisation (förvaltning/avdelning/enhet/sektion)."""
    __tablename__ = "org_units"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("org_units.id", ondelete="SET NULL"), index=True,
    )
    unit_type: Mapped[OrgUnitType] = mapped_column(_enum(OrgUnitType), nullable=False)
    manager_name: Mapped[str | None] = mapped_column(String(255))
    cost_center: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    parent: Mapped["OrgUnit | None"] = relationship(
        back_populates="children", remote_side=[id],
    )
    children: Mapped[list["OrgUnit"]] = relationship(back_populates="parent")
    capabilities_owned: Mapped[list["BusinessCapability"]] = relationship(
        secondary="unit_capability_link",
    )
    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        Index("ix_org_units_org_name", "organization_id", "name"),
    )


# --- Paket A länktabeller ---

capability_system_link = Table(
    "capability_system_link", Base.metadata,
    Column(
        "capability_id", UUID(as_uuid=True),
        ForeignKey("business_capabilities.id", ondelete="CASCADE"), primary_key=True,
    ),
    Column(
        "system_id", UUID(as_uuid=True),
        ForeignKey("systems.id", ondelete="CASCADE"), primary_key=True,
    ),
)

process_system_link = Table(
    "process_system_link", Base.metadata,
    Column(
        "process_id", UUID(as_uuid=True),
        ForeignKey("business_processes.id", ondelete="CASCADE"), primary_key=True,
    ),
    Column(
        "system_id", UUID(as_uuid=True),
        ForeignKey("systems.id", ondelete="CASCADE"), primary_key=True,
    ),
)

process_capability_link = Table(
    "process_capability_link", Base.metadata,
    Column(
        "process_id", UUID(as_uuid=True),
        ForeignKey("business_processes.id", ondelete="CASCADE"), primary_key=True,
    ),
    Column(
        "capability_id", UUID(as_uuid=True),
        ForeignKey("business_capabilities.id", ondelete="CASCADE"), primary_key=True,
    ),
)

process_information_link = Table(
    "process_information_link", Base.metadata,
    Column(
        "process_id", UUID(as_uuid=True),
        ForeignKey("business_processes.id", ondelete="CASCADE"), primary_key=True,
    ),
    Column(
        "information_asset_id", UUID(as_uuid=True),
        ForeignKey("information_assets.id", ondelete="CASCADE"), primary_key=True,
    ),
)

unit_capability_link = Table(
    "unit_capability_link", Base.metadata,
    Column(
        "unit_id", UUID(as_uuid=True),
        ForeignKey("org_units.id", ondelete="CASCADE"), primary_key=True,
    ),
    Column(
        "capability_id", UUID(as_uuid=True),
        ForeignKey("business_capabilities.id", ondelete="CASCADE"), primary_key=True,
    ),
)


# ============================================================
# Paket C — Rollkatalog och anställningsmallar (IGA)
# ============================================================


class BusinessRole(Base):
    """Verksamhetsroll — semantisk roll, ej AD-grupp."""
    __tablename__ = "business_roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    role_owner: Mapped[str | None] = mapped_column(String(255))
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    system_accesses: Mapped[list["RoleSystemAccess"]] = relationship(
        back_populates="business_role", cascade="all, delete-orphan",
    )
    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        Index("ix_business_roles_org_name", "organization_id", "name"),
    )


class Position(Base):
    """Befattning — kopplad till en organisationsenhet och 0..N verksamhetsroller via mall."""
    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True,
    )
    org_unit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("org_units.id", ondelete="SET NULL"), index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    position_code: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    org_unit: Mapped["OrgUnit | None"] = relationship()
    organization: Mapped["Organization"] = relationship()

    __table_args__ = (
        Index("ix_positions_org_title", "organization_id", "title"),
    )


class RoleSystemAccess(Base):
    """Vilka system en verksamhetsroll behöver och med vilken nivå."""
    __tablename__ = "role_system_access"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("business_roles.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    system_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("systems.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    access_level: Mapped[AccessLevel] = mapped_column(_enum(AccessLevel), nullable=False)
    access_type: Mapped[AccessType] = mapped_column(
        _enum(AccessType), nullable=False, default=AccessType.BIRTHRIGHT,
    )
    justification: Mapped[str | None] = mapped_column(Text)
    approver_name: Mapped[str | None] = mapped_column(String(255))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    business_role: Mapped["BusinessRole"] = relationship(back_populates="system_accesses")
    system: Mapped["System"] = relationship(back_populates="role_accesses")

    __table_args__ = (
        UniqueConstraint("business_role_id", "system_id", name="uq_role_system"),
    )


class EmploymentTemplate(Base):
    """IT-samordnarens 'anställningsmall' — paket av roller per befattning."""
    __tablename__ = "employment_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True,
    )
    position_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("positions.id", ondelete="SET NULL"), index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(255))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
    )

    position: Mapped["Position | None"] = relationship()
    organization: Mapped["Organization"] = relationship()
    roles: Mapped[list["BusinessRole"]] = relationship(secondary="template_role_link")

    __table_args__ = (
        Index("ix_employment_templates_org_name", "organization_id", "name"),
    )


template_role_link = Table(
    "template_role_link", Base.metadata,
    Column(
        "template_id", UUID(as_uuid=True),
        ForeignKey("employment_templates.id", ondelete="CASCADE"), primary_key=True,
    ),
    Column(
        "role_id", UUID(as_uuid=True),
        ForeignKey("business_roles.id", ondelete="CASCADE"), primary_key=True,
    ),
)
