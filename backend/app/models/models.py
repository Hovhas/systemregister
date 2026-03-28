import uuid
from datetime import datetime, date

from sqlalchemy import (
    String, Text, Boolean, Integer, Date, DateTime,
    ForeignKey, Enum as SAEnum, JSON, UniqueConstraint, Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import (
    OrganizationType, SystemCategory, LifecycleStatus, Criticality,
    OwnerRole, IntegrationType, ProcessorAgreementStatus,
    NIS2Classification, AuditAction,
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
    parent_org_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("organizations.id"))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    systems: Mapped[list["System"]] = relationship(back_populates="organization")
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

    # --- Kategori 3: Klassning & säkerhet (senaste aktiva) ---
    criticality: Mapped[Criticality] = mapped_column(_enum(Criticality), default=Criticality.MEDIUM)
    has_elevated_protection: Mapped[bool] = mapped_column(Boolean, default=False)  # MSBFS 2020:7 §4 p.3
    security_protection: Mapped[bool] = mapped_column(Boolean, default=False)  # Säkerhetsskyddslagen
    nis2_applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    nis2_classification: Mapped[NIS2Classification | None] = mapped_column(_enum(NIS2Classification))

    # --- Kategori 4: GDPR grundflaggor ---
    treats_personal_data: Mapped[bool] = mapped_column(Boolean, default=False)
    treats_sensitive_data: Mapped[bool] = mapped_column(Boolean, default=False)  # Art. 9
    third_country_transfer: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Kategori 5: Driftmiljö ---
    hosting_model: Mapped[str | None] = mapped_column(String(50))  # on-premise / cloud / hybrid
    cloud_provider: Mapped[str | None] = mapped_column(String(255))
    data_location_country: Mapped[str | None] = mapped_column(String(100), default="Sverige")
    product_name: Mapped[str | None] = mapped_column(String(255))
    product_version: Mapped[str | None] = mapped_column(String(100))

    # --- Kategori 6: Livscykel ---
    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(
        _enum(LifecycleStatus), default=LifecycleStatus.ACTIVE
    )
    deployment_date: Mapped[date | None] = mapped_column(Date)
    planned_decommission_date: Mapped[date | None] = mapped_column(Date)
    end_of_support_date: Mapped[date | None] = mapped_column(Date)

    # --- Kategori 9: Backup/DR ---
    backup_frequency: Mapped[str | None] = mapped_column(String(100))
    rpo: Mapped[str | None] = mapped_column(String(100))
    rto: Mapped[str | None] = mapped_column(String(100))
    dr_plan_exists: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Kategori 12: Compliance ---
    last_risk_assessment_date: Mapped[date | None] = mapped_column(Date)
    klassa_reference_id: Mapped[str | None] = mapped_column(String(100))

    # --- Flexibla attribut ---
    extended_attributes: Mapped[dict | None] = mapped_column(JSONB, default=dict)

    # --- Meta ---
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reviewed_by: Mapped[str | None] = mapped_column(String(255))

    # Relationships
    organization: Mapped["Organization"] = relationship(back_populates="systems")
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
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
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
