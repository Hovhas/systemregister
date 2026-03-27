import axios from "axios"
import type {
  Organization,
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
} from "@/types"

const api = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
})

// --- Organisationer ---

export async function getOrganizations(): Promise<Organization[]> {
  const res = await api.get<Organization[]>("/organizations")
  return res.data
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

export async function deleteOwner(ownerId: string): Promise<void> {
  await api.delete(`/owners/${ownerId}`)
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

export async function deleteGDPRTreatment(id: string): Promise<void> {
  await api.delete(`/gdpr/${id}`)
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

export async function deleteContract(id: string): Promise<void> {
  await api.delete(`/contracts/${id}`)
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

export default api
