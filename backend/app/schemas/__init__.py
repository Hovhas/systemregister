"""
Pydantic schemas for the Systemregister API.

All schemas are defined in domain-specific submodules and re-exported here
so that existing imports (e.g. ``from app.schemas import SystemCreate``)
keep working.
"""

from app.schemas.base import (  # noqa: F401
    SafeStringMixin,
    PaginatedResponse,
    T,
)

from app.schemas.organizations import (  # noqa: F401
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
)

from app.schemas.systems import (  # noqa: F401
    SystemCreate,
    SystemUpdate,
    SystemResponse,
    SystemDetailResponse,
)

from app.schemas.classifications import (  # noqa: F401
    ClassificationCreate,
    ClassificationResponse,
)

from app.schemas.owners import (  # noqa: F401
    OwnerCreate,
    OwnerUpdate,
    OwnerResponse,
)

from app.schemas.integrations import (  # noqa: F401
    IntegrationCreate,
    IntegrationUpdate,
    IntegrationResponse,
)

from app.schemas.gdpr import (  # noqa: F401
    GDPRTreatmentCreate,
    GDPRTreatmentUpdate,
    GDPRTreatmentResponse,
)

from app.schemas.contracts import (  # noqa: F401
    ContractCreate,
    ContractUpdate,
    ContractResponse,
)

from app.schemas.reports import (  # noqa: F401
    NIS2SystemEntry,
    NIS2ReportSummary,
    NIS2ReportResponse,
    ComplianceGaps,
    ComplianceGapSummary,
    ComplianceGapResponse,
    GDPRReportEntry,
    GDPRReportSummary,
    GDPRReportResponse,
    AIReportEntry,
    AIModuleEntry,
    AIReportSummary,
    AIReportResponse,
    ClassificationReportEntry,
    ClassificationReportSummary,
    ClassificationReportResponse,
    LifecycleContractEntry,
    LifecycleSystemEntry,
    LifecycleReportSummary,
    LifecycleReportResponse,
)

from app.schemas.audit import (  # noqa: F401
    AuditEntryResponse,
    AuditListResponse,
)

from app.schemas.notifications import (  # noqa: F401
    NotificationItem,
    NotificationListResponse,
)

from app.schemas.approvals import (  # noqa: F401
    ApprovalCreate,
    ApprovalReview,
    ApprovalResponse,
)

from app.schemas.entities import (  # noqa: F401
    ObjektCreate,
    ObjektUpdate,
    ObjektResponse,
    ComponentCreate,
    ComponentUpdate,
    ComponentResponse,
    ModuleCreate,
    ModuleUpdate,
    ModuleResponse,
    ModuleLinkRequest,
    InformationAssetCreate,
    InformationAssetUpdate,
    InformationAssetResponse,
    InformationAssetLinkRequest,
)
