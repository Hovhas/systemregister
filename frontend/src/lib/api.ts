import axios from "axios"
import type {
  Organization,
  System,
  SystemDetail,
  SystemStats,
  Classification,
  ClassificationCreate,
  Owner,
  OwnerCreate,
  Integration,
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
  const res = await api.get<SystemStats>("/systems/stats", {
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

export default api
