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
  BusinessCapability,
  CapabilityCreate,
  CapabilityUpdate,
  BusinessProcess,
  ProcessCreate,
  ProcessUpdate,
  ValueStream,
  ValueStreamCreate,
  ValueStreamUpdate,
  OrgUnit,
  OrgUnitCreate,
  OrgUnitUpdate,
  OrgUnitTreeNode,
  BusinessRole,
  BusinessRoleCreate,
  BusinessRoleUpdate,
  RoleSystemAccess,
  RoleSystemAccessCreate,
  RoleSystemAccessUpdate,
  RoleSystemAccessRow,
  Position,
  PositionCreate,
  PositionUpdate,
  EmploymentTemplate,
  EmploymentTemplateCreate,
  EmploymentTemplateUpdate,
  ResolvedAccessResponse,
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

// --- Förmågor ---

export async function getCapabilities(params?: { organization_id?: string; q?: string; limit?: number; offset?: number }): Promise<PaginatedResponse<BusinessCapability>> {
  const res = await api.get<PaginatedResponse<BusinessCapability>>("/capabilities/", { params })
  return res.data
}

export async function getCapability(id: string): Promise<BusinessCapability> {
  const res = await api.get<BusinessCapability>(`/capabilities/${id}`)
  return res.data
}

export async function createCapability(data: CapabilityCreate): Promise<BusinessCapability> {
  const res = await api.post<BusinessCapability>("/capabilities/", data)
  return res.data
}

export async function updateCapability(id: string, data: CapabilityUpdate): Promise<BusinessCapability> {
  const res = await api.patch<BusinessCapability>(`/capabilities/${id}`, data)
  return res.data
}

export async function deleteCapability(id: string): Promise<void> {
  await api.delete(`/capabilities/${id}`)
}

export async function getCapabilitySystems(id: string): Promise<Array<{ id: string; name: string; system_category: string }>> {
  const res = await api.get<Array<{ id: string; name: string; system_category: string }>>(`/capabilities/${id}/systems`)
  return res.data
}

export async function linkCapabilityToSystem(capId: string, systemId: string): Promise<void> {
  await api.post(`/capabilities/${capId}/systems`, { system_id: systemId })
}

export async function unlinkCapabilityFromSystem(capId: string, systemId: string): Promise<void> {
  await api.delete(`/capabilities/${capId}/systems/${systemId}`)
}

// --- Processer ---

export async function getProcesses(params?: { organization_id?: string; q?: string; limit?: number; offset?: number }): Promise<PaginatedResponse<BusinessProcess>> {
  const res = await api.get<PaginatedResponse<BusinessProcess>>("/processes/", { params })
  return res.data
}

export async function getProcess(id: string): Promise<BusinessProcess> {
  const res = await api.get<BusinessProcess>(`/processes/${id}`)
  return res.data
}

export async function createProcess(data: ProcessCreate): Promise<BusinessProcess> {
  const res = await api.post<BusinessProcess>("/processes/", data)
  return res.data
}

export async function updateProcess(id: string, data: ProcessUpdate): Promise<BusinessProcess> {
  const res = await api.patch<BusinessProcess>(`/processes/${id}`, data)
  return res.data
}

export async function deleteProcess(id: string): Promise<void> {
  await api.delete(`/processes/${id}`)
}

export async function getProcessSystems(id: string): Promise<Array<{ id: string; name: string; system_category: string }>> {
  const res = await api.get<Array<{ id: string; name: string; system_category: string }>>(`/processes/${id}/systems`)
  return res.data
}

export async function getProcessCapabilities(id: string): Promise<Array<{ id: string; name: string }>> {
  const res = await api.get<Array<{ id: string; name: string }>>(`/processes/${id}/capabilities`)
  return res.data
}

export async function getProcessInformationAssets(id: string): Promise<Array<{ id: string; name: string }>> {
  const res = await api.get<Array<{ id: string; name: string }>>(`/processes/${id}/information-assets`)
  return res.data
}

export async function linkProcessToSystem(processId: string, systemId: string): Promise<void> {
  await api.post(`/processes/${processId}/systems`, { system_id: systemId })
}

export async function unlinkProcessFromSystem(processId: string, systemId: string): Promise<void> {
  await api.delete(`/processes/${processId}/systems/${systemId}`)
}

export async function linkProcessToCapability(processId: string, capabilityId: string): Promise<void> {
  await api.post(`/processes/${processId}/capabilities`, { capability_id: capabilityId })
}

export async function unlinkProcessFromCapability(processId: string, capabilityId: string): Promise<void> {
  await api.delete(`/processes/${processId}/capabilities/${capabilityId}`)
}

export async function linkProcessToInformationAsset(processId: string, assetId: string): Promise<void> {
  await api.post(`/processes/${processId}/information-assets`, { information_asset_id: assetId })
}

export async function unlinkProcessFromInformationAsset(processId: string, assetId: string): Promise<void> {
  await api.delete(`/processes/${processId}/information-assets/${assetId}`)
}

// --- Värdeströmmar ---

export async function getValueStreams(params?: { organization_id?: string; limit?: number; offset?: number }): Promise<PaginatedResponse<ValueStream>> {
  const res = await api.get<PaginatedResponse<ValueStream>>("/value-streams/", { params })
  return res.data
}

export async function getValueStream(id: string): Promise<ValueStream> {
  const res = await api.get<ValueStream>(`/value-streams/${id}`)
  return res.data
}

export async function createValueStream(data: ValueStreamCreate): Promise<ValueStream> {
  const res = await api.post<ValueStream>("/value-streams/", data)
  return res.data
}

export async function updateValueStream(id: string, data: ValueStreamUpdate): Promise<ValueStream> {
  const res = await api.patch<ValueStream>(`/value-streams/${id}`, data)
  return res.data
}

export async function deleteValueStream(id: string): Promise<void> {
  await api.delete(`/value-streams/${id}`)
}

// --- Organisationsenheter ---

export async function getOrgUnits(params?: { organization_id?: string; limit?: number; offset?: number }): Promise<PaginatedResponse<OrgUnit>> {
  const res = await api.get<PaginatedResponse<OrgUnit>>("/org-units/", { params })
  return res.data
}

export async function getOrgUnit(id: string): Promise<OrgUnit> {
  const res = await api.get<OrgUnit>(`/org-units/${id}`)
  return res.data
}

export async function createOrgUnit(data: OrgUnitCreate): Promise<OrgUnit> {
  const res = await api.post<OrgUnit>("/org-units/", data)
  return res.data
}

export async function updateOrgUnit(id: string, data: OrgUnitUpdate): Promise<OrgUnit> {
  const res = await api.patch<OrgUnit>(`/org-units/${id}`, data)
  return res.data
}

export async function deleteOrgUnit(id: string): Promise<void> {
  await api.delete(`/org-units/${id}`)
}

export async function getOrgUnitTree(organization_id: string): Promise<OrgUnitTreeNode[]> {
  const res = await api.get<OrgUnitTreeNode[]>("/org-units/tree", { params: { organization_id } })
  return res.data
}

// --- Diagram (Paket B) ---

export async function getMermaidDiagram(path: string): Promise<string> {
  const res = await api.get<string>(path, { responseType: "text" })
  return res.data
}

export const archimateExportUrl = (organizationId: string) =>
  `/api/v1/export/archimate.xml?organization_id=${organizationId}`

export const twoseightPackageUrl = (organizationId: string) =>
  `/api/v1/export/2c8/full-package.zip?organization_id=${organizationId}`

// --- Verksamhetsroller (Paket C) ---

export async function getBusinessRoles(params?: {
  organization_id?: string
  q?: string
  include_counts?: boolean
  limit?: number
  offset?: number
}): Promise<PaginatedResponse<BusinessRole>> {
  const res = await api.get<PaginatedResponse<BusinessRole>>("/business-roles/", { params })
  return res.data
}

export async function getBusinessRole(id: string): Promise<BusinessRole> {
  const res = await api.get<BusinessRole>(`/business-roles/${id}`)
  return res.data
}

export async function createBusinessRole(data: BusinessRoleCreate): Promise<BusinessRole> {
  const res = await api.post<BusinessRole>("/business-roles/", data)
  return res.data
}

export async function updateBusinessRole(id: string, data: BusinessRoleUpdate): Promise<BusinessRole> {
  const res = await api.patch<BusinessRole>(`/business-roles/${id}`, data)
  return res.data
}

export async function deleteBusinessRole(id: string): Promise<void> {
  await api.delete(`/business-roles/${id}`)
}

export async function getRoleSystems(roleId: string): Promise<RoleSystemAccessRow[]> {
  const res = await api.get<RoleSystemAccessRow[]>(`/business-roles/${roleId}/systems`)
  return res.data
}

// --- Rollåtkomst ---

export async function createRoleAccess(data: RoleSystemAccessCreate): Promise<RoleSystemAccess> {
  const res = await api.post<RoleSystemAccess>("/role-access/", data)
  return res.data
}

export async function updateRoleAccess(id: string, data: RoleSystemAccessUpdate): Promise<RoleSystemAccess> {
  const res = await api.patch<RoleSystemAccess>(`/role-access/${id}`, data)
  return res.data
}

export async function deleteRoleAccess(id: string): Promise<void> {
  await api.delete(`/role-access/${id}`)
}

// --- Befattningar ---

export async function getPositions(params?: {
  organization_id?: string
  q?: string
  limit?: number
  offset?: number
}): Promise<PaginatedResponse<Position>> {
  const res = await api.get<PaginatedResponse<Position>>("/positions/", { params })
  return res.data
}

export async function getPosition(id: string): Promise<Position> {
  const res = await api.get<Position>(`/positions/${id}`)
  return res.data
}

export async function createPosition(data: PositionCreate): Promise<Position> {
  const res = await api.post<Position>("/positions/", data)
  return res.data
}

export async function updatePosition(id: string, data: PositionUpdate): Promise<Position> {
  const res = await api.patch<Position>(`/positions/${id}`, data)
  return res.data
}

export async function deletePosition(id: string): Promise<void> {
  await api.delete(`/positions/${id}`)
}

// --- Anställningsmallar ---

export async function getEmploymentTemplates(params?: {
  organization_id?: string
  q?: string
  limit?: number
  offset?: number
}): Promise<PaginatedResponse<EmploymentTemplate>> {
  const res = await api.get<PaginatedResponse<EmploymentTemplate>>("/employment-templates/", { params })
  return res.data
}

export async function getEmploymentTemplate(id: string): Promise<EmploymentTemplate> {
  const res = await api.get<EmploymentTemplate>(`/employment-templates/${id}`)
  return res.data
}

export async function createEmploymentTemplate(data: EmploymentTemplateCreate): Promise<EmploymentTemplate> {
  const res = await api.post<EmploymentTemplate>("/employment-templates/", data)
  return res.data
}

export async function updateEmploymentTemplate(id: string, data: EmploymentTemplateUpdate): Promise<EmploymentTemplate> {
  const res = await api.patch<EmploymentTemplate>(`/employment-templates/${id}`, data)
  return res.data
}

export async function deleteEmploymentTemplate(id: string): Promise<void> {
  await api.delete(`/employment-templates/${id}`)
}

export async function addRoleToTemplate(templateId: string, roleId: string): Promise<void> {
  await api.post(`/employment-templates/${templateId}/roles`, { business_role_id: roleId })
}

export async function removeRoleFromTemplate(templateId: string, roleId: string): Promise<void> {
  await api.delete(`/employment-templates/${templateId}/roles/${roleId}`)
}

export async function getResolvedAccess(templateId: string): Promise<ResolvedAccessResponse> {
  const res = await api.get<ResolvedAccessResponse>(`/employment-templates/${templateId}/resolved-access`)
  return res.data
}

export const resolvedAccessCsvUrl = (templateId: string) =>
  `/api/v1/employment-templates/${templateId}/resolved-access.csv`

export default api
