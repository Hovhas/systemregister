import axios from "axios"
import type {
  Organization,
  OrganizationCreate,
  OrganizationUpdate,
  System,
  SystemCreate,
  SystemUpdate,
  SystemDetail,
  SystemStats,
  Classification,
  ClassificationCreate,
  Owner,
  OwnerCreate,
  Integration,
  IntegrationCreate,
  GDPRTreatment,
  GDPRTreatmentCreate,
  Contract,
  ContractCreate,
  ImportResult,
  PaginatedResponse,
  SystemSearchParams,
  IntegrationSearchParams,
  NotificationsResponse,
  ExpiringContract,
  AuditResponse,
  AuditEntry,
  Objekt,
  ObjektCreate,
  ObjektUpdate,
  Component,
  ComponentCreate,
  Module,
  ModuleCreate,
  InformationAsset,
  InformationAssetCreate,
  Approval,
  ApprovalCreate,
  ApprovalReview,
  ApprovalStatus,
} from "@/types"

const api = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
})

// Auth token injection (used when OIDC is enabled)
let _accessToken: string | null = null
export function setAuthToken(token: string | null) {
  _accessToken = token
}

api.interceptors.request.use((config) => {
  if (_accessToken) {
    config.headers.Authorization = `Bearer ${_accessToken}`
  }
  return config
})

// Global error interceptor — visar toast vid API-fel
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status
      const detail = error.response?.data?.detail

      // Extrahera felmeddelande
      const message =
        typeof detail === "string"
          ? detail
          : typeof detail === "object" && detail?.message
          ? detail.message
          : status === 401
          ? "Ej autentiserad"
          : status === 403
          ? "Åtkomst nekad"
          : status === 404
          ? "Resursen hittades inte"
          : status === 409
          ? "Konflikt — resursen finns redan"
          : status === 422
          ? "Valideringsfel — kontrollera indata"
          : status && status >= 500
          ? "Serverfel — försök igen senare"
          : "Nätverksfel — kontrollera din anslutning"

      // Importera toast dynamiskt för att undvika cirkulär dep
      import("sonner").then(({ toast }) => {
        toast.error(message)
      })
    }
    return Promise.reject(error)
  }
)

// --- Organisationer ---

export async function getOrganizations(): Promise<Organization[]> {
  const res = await api.get<Organization[]>("/organizations")
  return res.data
}

export async function createOrganization(data: OrganizationCreate): Promise<Organization> {
  const res = await api.post<Organization>("/organizations", data)
  return res.data
}

export async function updateOrganization(id: string, data: OrganizationUpdate): Promise<Organization> {
  const res = await api.patch<Organization>(`/organizations/${id}`, data)
  return res.data
}

export async function deleteOrganization(id: string): Promise<void> {
  await api.delete(`/organizations/${id}`)
}

// --- System ---

export async function getSystems(
  params?: SystemSearchParams
): Promise<PaginatedResponse<System>> {
  const res = await api.get<PaginatedResponse<System>>("/systems", { params })
  return res.data
}

export async function getSystem(id: string): Promise<SystemDetail> {
  const res = await api.get<SystemDetail>(`/systems/${id}`)
  return res.data
}

export async function getSystemStats(
  organization_id?: string
): Promise<SystemStats> {
  const res = await api.get<SystemStats>("/systems/stats/overview", {
    params: organization_id ? { organization_id } : undefined,
  })
  return res.data
}

// --- Klassningar ---

export async function getClassifications(
  systemId: string
): Promise<Classification[]> {
  const res = await api.get<Classification[]>(
    `/systems/${systemId}/classifications`
  )
  return res.data
}

export async function createClassification(
  systemId: string,
  data: ClassificationCreate
): Promise<Classification> {
  const res = await api.post<Classification>(
    `/systems/${systemId}/classifications`,
    data
  )
  return res.data
}

// --- Ägare ---

export async function getOwners(systemId: string): Promise<Owner[]> {
  const res = await api.get<Owner[]>(`/systems/${systemId}/owners`)
  return res.data
}

export async function createOwner(
  systemId: string,
  data: OwnerCreate
): Promise<Owner> {
  const res = await api.post<Owner>(`/systems/${systemId}/owners`, data)
  return res.data
}

// --- Integrationer ---

export async function getIntegrations(
  params?: IntegrationSearchParams
): Promise<Integration[]> {
  const res = await api.get<Integration[]>("/integrations", { params })
  return res.data
}

export async function getSystemIntegrations(
  systemId: string
): Promise<Integration[]> {
  const res = await api.get<Integration[]>(`/systems/${systemId}/integrations`)
  return res.data
}

// --- System CRUD ---

export async function createSystem(data: SystemCreate): Promise<System> {
  const res = await api.post<System>("/systems", data)
  return res.data
}

export async function updateSystem(id: string, data: SystemUpdate): Promise<System> {
  const res = await api.patch<System>(`/systems/${id}`, data)
  return res.data
}

export async function deleteSystem(id: string): Promise<void> {
  await api.delete(`/systems/${id}`)
}

// --- Owner CRUD ---

export async function deleteOwner(systemId: string, ownerId: string): Promise<void> {
  await api.delete(`/systems/${systemId}/owners/${ownerId}`)
}

// --- Integration CRUD ---

export async function createIntegration(data: IntegrationCreate): Promise<Integration> {
  const res = await api.post<Integration>("/integrations", data)
  return res.data
}

export async function deleteIntegration(id: string): Promise<void> {
  await api.delete(`/integrations/${id}`)
}

// --- GDPR ---

export async function getGDPRTreatments(systemId: string): Promise<GDPRTreatment[]> {
  const res = await api.get<GDPRTreatment[]>(`/systems/${systemId}/gdpr`)
  return res.data
}

export async function createGDPRTreatment(
  systemId: string,
  data: GDPRTreatmentCreate
): Promise<GDPRTreatment> {
  const res = await api.post<GDPRTreatment>(`/systems/${systemId}/gdpr`, data)
  return res.data
}

export async function deleteGDPRTreatment(systemId: string, id: string): Promise<void> {
  await api.delete(`/systems/${systemId}/gdpr/${id}`)
}

// --- Contracts ---

export async function getContracts(systemId: string): Promise<Contract[]> {
  const res = await api.get<Contract[]>(`/systems/${systemId}/contracts`)
  return res.data
}

export async function createContract(
  systemId: string,
  data: ContractCreate
): Promise<Contract> {
  const res = await api.post<Contract>(`/systems/${systemId}/contracts`, data)
  return res.data
}

export async function deleteContract(systemId: string, id: string): Promise<void> {
  await api.delete(`/systems/${systemId}/contracts/${id}`)
}

// --- Import ---

export async function importFile(
  type: "systems" | "classifications" | "owners",
  file: File,
  organizationId?: string
): Promise<ImportResult> {
  const formData = new FormData()
  formData.append("file", file)
  const params = organizationId ? `?organization_id=${organizationId}` : ""
  const res = await api.post<ImportResult>(`/import/${type}${params}`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return res.data
}

// --- Utgående avtal ---

export async function getExpiringContracts(days = 90): Promise<ExpiringContract[]> {
  const res = await api.get<ExpiringContract[]>("/contracts/expiring", { params: { days } })
  return res.data
}

// --- Audit-logg ---

export async function getAuditLog(params?: {
  table_name?: string
  action?: string
  limit?: number
  offset?: number
}): Promise<AuditResponse> {
  const res = await api.get<AuditResponse>("/audit", { params })
  return res.data
}

export async function getAuditForRecord(recordId: string): Promise<AuditEntry[]> {
  const res = await api.get<AuditEntry[]>(`/audit/record/${recordId}`)
  return res.data
}

// --- Notifikationer ---

export async function getNotifications(params?: {
  limit?: number
  offset?: number
}): Promise<NotificationsResponse> {
  const res = await api.get<NotificationsResponse>("/notifications", { params })
  return res.data
}

// --- Objekt ---

export async function getObjekt(params?: { organization_id?: string; q?: string; limit?: number; offset?: number }): Promise<PaginatedResponse<Objekt>> {
  const res = await api.get<PaginatedResponse<Objekt>>("/objekt", { params })
  return res.data
}

export async function getObjektById(id: string): Promise<Objekt> {
  const res = await api.get<Objekt>(`/objekt/${id}`)
  return res.data
}

export async function createObjekt(data: ObjektCreate): Promise<Objekt> {
  const res = await api.post<Objekt>("/objekt", data)
  return res.data
}

export async function updateObjekt(id: string, data: ObjektUpdate): Promise<Objekt> {
  const res = await api.patch<Objekt>(`/objekt/${id}`, data)
  return res.data
}

export async function deleteObjekt(id: string): Promise<void> {
  await api.delete(`/objekt/${id}`)
}

// --- Komponenter ---

export async function getComponents(params?: { system_id?: string; organization_id?: string; q?: string; limit?: number; offset?: number }): Promise<PaginatedResponse<Component>> {
  const res = await api.get<PaginatedResponse<Component>>("/components", { params })
  return res.data
}

export async function createComponent(data: ComponentCreate): Promise<Component> {
  const res = await api.post<Component>("/components", data)
  return res.data
}

export async function updateComponent(id: string, data: Partial<ComponentCreate>): Promise<Component> {
  const res = await api.patch<Component>(`/components/${id}`, data)
  return res.data
}

export async function deleteComponent(id: string): Promise<void> {
  await api.delete(`/components/${id}`)
}

export async function getComponentById(id: string): Promise<Component> {
  const res = await api.get<Component>(`/components/${id}`)
  return res.data
}

// --- Moduler ---

export async function getModules(params?: { organization_id?: string; q?: string; limit?: number; offset?: number }): Promise<PaginatedResponse<Module>> {
  const res = await api.get<PaginatedResponse<Module>>("/modules", { params })
  return res.data
}

export async function createModule(data: ModuleCreate): Promise<Module> {
  const res = await api.post<Module>("/modules", data)
  return res.data
}

export async function updateModule(id: string, data: Partial<ModuleCreate>): Promise<Module> {
  const res = await api.patch<Module>(`/modules/${id}`, data)
  return res.data
}

export async function deleteModule(id: string): Promise<void> {
  await api.delete(`/modules/${id}`)
}

export async function getModule(id: string): Promise<Module> {
  const res = await api.get<Module>(`/modules/${id}`)
  return res.data
}

export async function linkModuleToSystem(moduleId: string, systemId: string): Promise<void> {
  await api.post(`/modules/${moduleId}/systems`, { system_id: systemId })
}

export async function unlinkModuleFromSystem(moduleId: string, systemId: string): Promise<void> {
  await api.delete(`/modules/${moduleId}/systems/${systemId}`)
}

// --- Informationsmängder ---

export async function getInformationAssets(params?: { organization_id?: string; contains_personal_data?: boolean; q?: string; limit?: number; offset?: number }): Promise<PaginatedResponse<InformationAsset>> {
  const res = await api.get<PaginatedResponse<InformationAsset>>("/information-assets", { params })
  return res.data
}

export async function createInformationAsset(data: InformationAssetCreate): Promise<InformationAsset> {
  const res = await api.post<InformationAsset>("/information-assets", data)
  return res.data
}

export async function updateInformationAsset(id: string, data: Partial<InformationAssetCreate>): Promise<InformationAsset> {
  const res = await api.patch<InformationAsset>(`/information-assets/${id}`, data)
  return res.data
}

export async function deleteInformationAsset(id: string): Promise<void> {
  await api.delete(`/information-assets/${id}`)
}

export async function getInformationAsset(id: string): Promise<InformationAsset> {
  const res = await api.get<InformationAsset>(`/information-assets/${id}`)
  return res.data
}

export async function linkAssetToSystem(assetId: string, systemId: string): Promise<void> {
  await api.post(`/information-assets/${assetId}/systems`, { system_id: systemId })
}

export async function unlinkAssetFromSystem(assetId: string, systemId: string): Promise<void> {
  await api.delete(`/information-assets/${assetId}/systems/${systemId}`)
}

// --- Godkännanden ---

export async function getApprovals(params?: { organization_id?: string; status?: ApprovalStatus; limit?: number; offset?: number }): Promise<PaginatedResponse<Approval>> {
  const res = await api.get<PaginatedResponse<Approval>>("/approvals", { params })
  return res.data
}

export async function getPendingApprovalCount(organizationId?: string): Promise<number> {
  const res = await api.get<{ pending: number }>("/approvals/pending/count", {
    params: organizationId ? { organization_id: organizationId } : undefined,
  })
  return res.data.pending
}

export async function createApproval(data: ApprovalCreate): Promise<Approval> {
  const res = await api.post<Approval>("/approvals", data)
  return res.data
}

export async function reviewApproval(id: string, data: ApprovalReview): Promise<Approval> {
  const res = await api.post<Approval>(`/approvals/${id}/review`, data)
  return res.data
}

export async function getApproval(id: string): Promise<Approval> {
  const res = await api.get<Approval>(`/approvals/${id}`)
  return res.data
}

export async function deleteApproval(id: string): Promise<void> {
  await api.delete(`/approvals/${id}`)
}

export default api
