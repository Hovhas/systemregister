import enum


class OrganizationType(str, enum.Enum):
    KOMMUN = "kommun"
    BOLAG = "bolag"
    SAMVERKAN = "samverkan"
    DIGIT = "digit"


class SystemCategory(str, enum.Enum):
    VERKSAMHETSSYSTEM = "verksamhetssystem"
    STODSYSTEM = "stödsystem"
    INFRASTRUKTUR = "infrastruktur"
    PLATTFORM = "plattform"
    IOT = "iot"


class LifecycleStatus(str, enum.Enum):
    PLANNED = "planerad"
    IMPLEMENTING = "under_inforande"
    ACTIVE = "i_drift"
    DECOMMISSIONING = "under_avveckling"
    DECOMMISSIONED = "avvecklad"


class Criticality(str, enum.Enum):
    LOW = "låg"
    MEDIUM = "medel"
    HIGH = "hög"
    CRITICAL = "kritisk"


class OwnerRole(str, enum.Enum):
    SYSTEM_OWNER = "systemägare"
    INFORMATION_OWNER = "informationsägare"
    SYSTEM_ADMINISTRATOR = "systemförvaltare"
    TECHNICAL_ADMINISTRATOR = "teknisk_förvaltare"
    IT_CONTACT = "it_kontakt"
    DPO = "dataskyddsombud"


class IntegrationType(str, enum.Enum):
    API = "api"
    FILE_TRANSFER = "filöverföring"
    DB_REPLICATION = "databasreplikering"
    EVENT = "event"
    MANUAL = "manuell"


class ProcessorAgreementStatus(str, enum.Enum):
    YES = "ja"
    NO = "nej"
    IN_PROGRESS = "under_framtagande"
    NOT_APPLICABLE = "ej_tillämpligt"


class NIS2Classification(str, enum.Enum):
    ESSENTIAL = "väsentlig"
    IMPORTANT = "viktig"
    NOT_APPLICABLE = "ej_tillämplig"


class AuditAction(str, enum.Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


# --- Entitetshierarki (Kravspec avsnitt 3) ---

class EntityType(str, enum.Enum):
    """Typ av entitet i hierarkin."""
    OBJEKT = "objekt"
    SYSTEM = "system"
    KOMPONENT = "komponent"
    MODUL = "modul"
    INFORMATIONSMANGD = "informationsmängd"


# --- AI-förordningen (Kravspec kategori 13) ---

class AIRiskClass(str, enum.Enum):
    """EU AI Act (2024/1689) riskklass."""
    FORBIDDEN = "förbjuden"
    HIGH_RISK = "hög_risk"
    LIMITED_RISK = "begränsad_risk"
    MINIMAL_RISK = "minimal_risk"
    NOT_APPLICABLE = "ej_tillämplig"


class FRIAStatus(str, enum.Enum):
    """Fundamental Rights Impact Assessment status."""
    YES = "ja"
    NO = "nej"
    NOT_APPLICABLE = "ej_tillämplig"


# --- Arbetsflöden (FK-15) ---

class ApprovalStatus(str, enum.Enum):
    PENDING = "väntande"
    APPROVED = "godkänd"
    REJECTED = "avvisad"
    CANCELLED = "avbruten"


class ApprovalType(str, enum.Enum):
    SYSTEM_REGISTRATION = "systemregistrering"
    SYSTEM_DECOMMISSION = "avveckling"
    CLASSIFICATION_CHANGE = "klassningsändring"
    GDPR_TREATMENT = "gdpr_behandling"
    DATA_CHANGE = "dataändring"


# --- Verksamhetsskikt (Paket A) ---

class OrgUnitType(str, enum.Enum):
    """Typ av organisationsenhet inom en organisation."""
    FORVALTNING = "förvaltning"
    AVDELNING = "avdelning"
    ENHET = "enhet"
    SEKTION = "sektion"
    BOLAG = "bolag"


# --- Rollkatalog/IGA (Paket C) ---

class AccessLevel(str, enum.Enum):
    """Behörighetsnivå för en roll mot ett system."""
    READ = "läs"
    WRITE = "skriv"
    ADMIN = "administratör"


class AccessType(str, enum.Enum):
    """Typ av åtkomst — styr om den ges automatiskt eller kräver beslut."""
    BIRTHRIGHT = "grundbehörighet"
    CONDITIONAL = "villkorad"
    MANUAL = "manuell"
