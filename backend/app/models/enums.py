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
