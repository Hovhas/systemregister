/**
 * Testsvit: API-klient (src/lib/api.ts)
 * ~40 testfall
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest"
import { setupServer, http, HttpResponse } from "../setup"
import {
  getOrganizations,
  getSystems,
  getSystem,
  getSystemStats,
  createSystem,
  updateSystem,
  deleteSystem,
  getClassifications,
  createClassification,
  getOwners,
  createOwner,
  deleteOwner,
  getIntegrations,
  getSystemIntegrations,
  createIntegration,
  deleteIntegration,
  getGDPRTreatments,
  createGDPRTreatment,
  deleteGDPRTreatment,
  getContracts,
  createContract,
  deleteContract,
  importFile,
} from "@/lib/api"
import {
  Criticality,
  SystemCategory,
  LifecycleStatus,
  OwnerRole,
  IntegrationType,
} from "@/types"

// --- Testdata ---

const mockOrg = {
  id: "org-1",
  name: "Kommunen",
  org_number: null,
  org_type: "kommun",
  parent_org_id: null,
  description: null,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
}

const mockSystem = {
  id: "sys-1",
  organization_id: "org-1",
  name: "Testsystem",
  aliases: null,
  description: "Testar API",
  system_category: SystemCategory.VERKSAMHETSSYSTEM,
  business_area: null,
  criticality: Criticality.MEDIUM,
  has_elevated_protection: false,
  security_protection: false,
  nis2_applicable: false,
  nis2_classification: null,
  treats_personal_data: false,
  treats_sensitive_data: false,
  third_country_transfer: false,
  hosting_model: null,
  cloud_provider: null,
  data_location_country: null,
  product_name: null,
  product_version: null,
  lifecycle_status: LifecycleStatus.ACTIVE,
  deployment_date: null,
  planned_decommission_date: null,
  end_of_support_date: null,
  backup_frequency: null,
  rpo: null,
  rto: null,
  dr_plan_exists: false,
  last_risk_assessment_date: null,
  klassa_reference_id: null,
  extended_attributes: null,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  last_reviewed_at: null,
  last_reviewed_by: null,
}

const mockSystemDetail = {
  ...mockSystem,
  classifications: [],
  owners: [],
  integrations: [],
  gdpr_treatments: [],
  contracts: [],
}

const mockStats = {
  total: 42,
  by_criticality: { kritisk: 5, hög: 10, medel: 20, låg: 7 },
  by_lifecycle_status: { i_drift: 35, planerad: 7 },
  by_system_category: { verksamhetssystem: 20 },
  nis2_count: 10,
}

const mockClassification = {
  id: "cls-1",
  system_id: "sys-1",
  confidentiality: 2,
  integrity: 3,
  availability: 2,
  traceability: null,
  classified_by: "admin",
  classified_at: "2024-01-01T00:00:00Z",
  valid_until: null,
  notes: null,
}

const mockOwner = {
  id: "own-1",
  system_id: "sys-1",
  role: OwnerRole.SYSTEM_OWNER,
  name: "Test Person",
  email: "test@test.se",
  phone: null,
  organization_id: "org-1",
  created_at: "2024-01-01T00:00:00Z",
}

const mockIntegration = {
  id: "int-1",
  source_system_id: "sys-1",
  target_system_id: "sys-2",
  integration_type: IntegrationType.API,
  data_types: null,
  frequency: null,
  description: null,
  criticality: null,
  is_external: false,
  external_party: null,
  created_at: "2024-01-01T00:00:00Z",
}

// --- MSW-server ---

const server = setupServer(
  // Organisationer
  http.get("/api/v1/organizations/", () => HttpResponse.json([mockOrg])),

  // System
  http.get("/api/v1/systems/", ({ request }) => {
    const url = new URL(request.url)
    const items = [mockSystem]
    return HttpResponse.json({
      items,
      total: items.length,
      limit: parseInt(url.searchParams.get("limit") ?? "25"),
      offset: parseInt(url.searchParams.get("offset") ?? "0"),
    })
  }),
  http.get("/api/v1/systems/stats/overview", () =>
    HttpResponse.json(mockStats)
  ),
  http.get("/api/v1/systems/:id", ({ params }) => {
    if (params.id === "nonexistent") {
      return HttpResponse.json({ detail: "Not found" }, { status: 404 })
    }
    return HttpResponse.json(mockSystemDetail)
  }),
  http.post("/api/v1/systems/", async ({ request }) => {
    const body = await request.json() as object
    return HttpResponse.json({ ...mockSystem, ...body }, { status: 201 })
  }),
  http.patch("/api/v1/systems/:id", async ({ request }) => {
    const body = await request.json() as object
    return HttpResponse.json({ ...mockSystem, ...body })
  }),
  http.delete("/api/v1/systems/:id", () =>
    new HttpResponse(null, { status: 204 })
  ),

  // Klassningar
  http.get("/api/v1/systems/:id/classifications/", () =>
    HttpResponse.json([mockClassification])
  ),
  http.post("/api/v1/systems/:id/classifications/", async ({ request }) => {
    const body = await request.json() as object
    return HttpResponse.json({ ...mockClassification, ...body }, { status: 201 })
  }),

  // Ägare
  http.get("/api/v1/systems/:id/owners/", () =>
    HttpResponse.json([mockOwner])
  ),
  http.post("/api/v1/systems/:id/owners/", async ({ request }) => {
    const body = await request.json() as object
    return HttpResponse.json({ ...mockOwner, ...body }, { status: 201 })
  }),
  http.delete("/api/v1/owners/:id", () =>
    new HttpResponse(null, { status: 204 })
  ),

  // Integrationer
  http.get("/api/v1/integrations/", () =>
    HttpResponse.json([mockIntegration])
  ),
  http.get("/api/v1/systems/:id/integrations/", () =>
    HttpResponse.json([mockIntegration])
  ),
  http.post("/api/v1/integrations/", async ({ request }) => {
    const body = await request.json() as object
    return HttpResponse.json({ ...mockIntegration, ...body }, { status: 201 })
  }),
  http.delete("/api/v1/integrations/:id", () =>
    new HttpResponse(null, { status: 204 })
  ),

  // GDPR
  http.get("/api/v1/systems/:id/gdpr/", () => HttpResponse.json([])),
  http.post("/api/v1/systems/:id/gdpr/", () =>
    HttpResponse.json(
      {
        id: "gdpr-1",
        system_id: "sys-1",
        dpia_conducted: false,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      },
      { status: 201 }
    )
  ),
  http.delete("/api/v1/gdpr/:id", () =>
    new HttpResponse(null, { status: 204 })
  ),

  // Contracts
  http.get("/api/v1/systems/:id/contracts/", () => HttpResponse.json([])),
  http.post("/api/v1/systems/:id/contracts/", () =>
    HttpResponse.json(
      {
        id: "con-1",
        system_id: "sys-1",
        supplier_name: "Leverantör AB",
        auto_renewal: false,
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      },
      { status: 201 }
    )
  ),
  http.delete("/api/v1/contracts/:id", () =>
    new HttpResponse(null, { status: 204 })
  ),

  // Import
  http.post("/api/v1/import/:type", () =>
    HttpResponse.json({ imported: 3, errors: [] })
  )
)

beforeAll(() => server.listen({ onUnhandledRequest: "warn" }))
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

// --- Tester ---

describe("API-klient", () => {
  describe("getOrganizations", () => {
    it("returnerar lista med organisationer", async () => {
      const result = await getOrganizations()
      expect(result).toHaveLength(1)
      expect(result[0].id).toBe("org-1")
      expect(result[0].name).toBe("Kommunen")
    })

    it("kastar fel vid 500", async () => {
      server.use(
        http.get("/api/v1/organizations/", () =>
          HttpResponse.json({}, { status: 500 })
        )
      )
      await expect(getOrganizations()).rejects.toThrow()
    })
  })

  describe("getSystems", () => {
    it("returnerar paginerat svar", async () => {
      const result = await getSystems()
      expect(result.items).toHaveLength(1)
      expect(result.total).toBe(1)
      expect(result.items[0].name).toBe("Testsystem")
    })

    it("skickar query-parametrar korrekt", async () => {
      let capturedParams: URLSearchParams | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          capturedParams = new URL(request.url).searchParams
          return HttpResponse.json({
            items: [mockSystem],
            total: 1,
            limit: 10,
            offset: 0,
          })
        })
      )
      await getSystems({
        q: "test",
        system_category: SystemCategory.VERKSAMHETSSYSTEM,
        limit: 10,
        offset: 0,
      })
      expect(capturedParams?.get("q")).toBe("test")
      expect(capturedParams?.get("system_category")).toBe("verksamhetssystem")
      expect(capturedParams?.get("limit")).toBe("10")
    })

    it("skickar lifecycle_status som query-parameter", async () => {
      let capturedStatus: string | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          capturedStatus = new URL(request.url).searchParams.get(
            "lifecycle_status"
          )
          return HttpResponse.json({ items: [], total: 0, limit: 25, offset: 0 })
        })
      )
      await getSystems({ lifecycle_status: LifecycleStatus.ACTIVE })
      expect(capturedStatus).toBe("i_drift")
    })

    it("skickar criticality som query-parameter", async () => {
      let capturedCrit: string | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          capturedCrit = new URL(request.url).searchParams.get("criticality")
          return HttpResponse.json({ items: [], total: 0, limit: 25, offset: 0 })
        })
      )
      await getSystems({ criticality: Criticality.HIGH })
      expect(capturedCrit).toBe("hög")
    })

    it("kastar fel vid nätverksfel", async () => {
      server.use(
        http.get("/api/v1/systems/", () =>
          HttpResponse.json({}, { status: 503 })
        )
      )
      await expect(getSystems()).rejects.toThrow()
    })
  })

  describe("getSystem", () => {
    it("returnerar systemdetalj med id", async () => {
      const result = await getSystem("sys-1")
      expect(result.id).toBe("sys-1")
      expect(result.name).toBe("Testsystem")
      expect(result.classifications).toEqual([])
      expect(result.owners).toEqual([])
    })

    it("kastar fel vid 404", async () => {
      await expect(getSystem("nonexistent")).rejects.toThrow()
    })

    it("anropar korrekt URL /systems/:id", async () => {
      let capturedUrl: string | null = null
      server.use(
        http.get("/api/v1/systems/:id", ({ request }) => {
          capturedUrl = new URL(request.url).pathname
          return HttpResponse.json(mockSystemDetail)
        })
      )
      await getSystem("sys-99")
      expect(capturedUrl).toBe("/api/v1/systems/sys-99")
    })
  })

  describe("getSystemStats", () => {
    it("returnerar statistik utan organization_id", async () => {
      const result = await getSystemStats()
      expect(result.total).toBe(42)
      expect(result.nis2_count).toBe(10)
    })

    it("skickar organization_id som query-param", async () => {
      let capturedParam: string | null = null
      server.use(
        http.get("/api/v1/systems/stats/overview", ({ request }) => {
          capturedParam = new URL(request.url).searchParams.get(
            "organization_id"
          )
          return HttpResponse.json(mockStats)
        })
      )
      await getSystemStats("org-1")
      expect(capturedParam).toBe("org-1")
    })

    it("skickar inte organization_id om undefined", async () => {
      let capturedParam: string | null = "initial"
      server.use(
        http.get("/api/v1/systems/stats/overview", ({ request }) => {
          capturedParam = new URL(request.url).searchParams.get(
            "organization_id"
          )
          return HttpResponse.json(mockStats)
        })
      )
      await getSystemStats(undefined)
      expect(capturedParam).toBeNull()
    })
  })

  describe("createSystem", () => {
    it("POST till /systems/ med korrekt body", async () => {
      let capturedBody: unknown = null
      server.use(
        http.post("/api/v1/systems/", async ({ request }) => {
          capturedBody = await request.json()
          return HttpResponse.json(
            { ...mockSystem, name: "Nytt" },
            { status: 201 }
          )
        })
      )
      const payload = {
        organization_id: "org-1",
        name: "Nytt",
        description: "Beskrivning",
        system_category: SystemCategory.VERKSAMHETSSYSTEM,
      }
      await createSystem(payload)
      expect(capturedBody).toMatchObject(payload)
    })

    it("returnerar det skapade systemet", async () => {
      const result = await createSystem({
        organization_id: "org-1",
        name: "Skapat",
        description: "Desc",
        system_category: SystemCategory.PLATTFORM,
      })
      expect(result.id).toBe("sys-1")
    })

    it("Content-Type är application/json", async () => {
      let contentType: string | null = null
      server.use(
        http.post("/api/v1/systems/", async ({ request }) => {
          contentType = request.headers.get("content-type")
          return HttpResponse.json(mockSystem, { status: 201 })
        })
      )
      await createSystem({
        organization_id: "org-1",
        name: "Test",
        description: "D",
        system_category: SystemCategory.IOT,
      })
      expect(contentType).toContain("application/json")
    })
  })

  describe("updateSystem", () => {
    it("PATCH till /systems/:id med korrekt body", async () => {
      let capturedBody: unknown = null
      server.use(
        http.patch("/api/v1/systems/:id", async ({ request }) => {
          capturedBody = await request.json()
          return HttpResponse.json(mockSystem)
        })
      )
      await updateSystem("sys-1", { name: "Uppdaterat" })
      expect(capturedBody).toMatchObject({ name: "Uppdaterat" })
    })

    it("anropar korrekt URL vid uppdatering", async () => {
      let url: string | null = null
      server.use(
        http.patch("/api/v1/systems/:id", ({ request }) => {
          url = new URL(request.url).pathname
          return HttpResponse.json(mockSystem)
        })
      )
      await updateSystem("sys-42", { name: "X" })
      expect(url).toBe("/api/v1/systems/sys-42")
    })
  })

  describe("deleteSystem", () => {
    it("DELETE till /systems/:id", async () => {
      let deleteCalled = false
      server.use(
        http.delete("/api/v1/systems/:id", () => {
          deleteCalled = true
          return new HttpResponse(null, { status: 204 })
        })
      )
      await deleteSystem("sys-1")
      expect(deleteCalled).toBe(true)
    })

    it("kastar fel vid 404", async () => {
      server.use(
        http.delete("/api/v1/systems/:id", () =>
          HttpResponse.json({ detail: "Not found" }, { status: 404 })
        )
      )
      await expect(deleteSystem("nonexistent")).rejects.toThrow()
    })
  })

  describe("getClassifications", () => {
    it("returnerar klassningslista för system", async () => {
      const result = await getClassifications("sys-1")
      expect(result).toHaveLength(1)
      expect(result[0].confidentiality).toBe(2)
    })

    it("anropar URL /systems/:id/classifications/", async () => {
      let url: string | null = null
      server.use(
        http.get("/api/v1/systems/:id/classifications/", ({ request }) => {
          url = new URL(request.url).pathname
          return HttpResponse.json([mockClassification])
        })
      )
      await getClassifications("sys-99")
      expect(url).toBe("/api/v1/systems/sys-99/classifications/")
    })
  })

  describe("createClassification", () => {
    it("POST klassning med korrekt data", async () => {
      let body: unknown = null
      server.use(
        http.post("/api/v1/systems/:id/classifications/", async ({ request }) => {
          body = await request.json()
          return HttpResponse.json(mockClassification, { status: 201 })
        })
      )
      await createClassification("sys-1", {
        system_id: "sys-1",
        confidentiality: 3,
        integrity: 2,
        availability: 4,
        classified_by: "admin",
      })
      expect(body).toMatchObject({ confidentiality: 3 })
    })
  })

  describe("getOwners", () => {
    it("returnerar ägarelista för system", async () => {
      const result = await getOwners("sys-1")
      expect(result).toHaveLength(1)
      expect(result[0].name).toBe("Test Person")
    })
  })

  describe("deleteOwner", () => {
    it("DELETE till /owners/:id", async () => {
      let deleteCalled = false
      server.use(
        http.delete("/api/v1/owners/:id", () => {
          deleteCalled = true
          return new HttpResponse(null, { status: 204 })
        })
      )
      await deleteOwner("own-1")
      expect(deleteCalled).toBe(true)
    })
  })

  describe("getIntegrations", () => {
    it("returnerar integrationslista", async () => {
      const result = await getIntegrations()
      expect(result).toHaveLength(1)
      expect(result[0].id).toBe("int-1")
    })

    it("skickar system_id query-param om angivet", async () => {
      let param: string | null = null
      server.use(
        http.get("/api/v1/integrations/", ({ request }) => {
          param = new URL(request.url).searchParams.get("system_id")
          return HttpResponse.json([mockIntegration])
        })
      )
      await getIntegrations({ system_id: "sys-1" })
      expect(param).toBe("sys-1")
    })
  })

  describe("getSystemIntegrations", () => {
    it("anropar /systems/:id/integrations/", async () => {
      let url: string | null = null
      server.use(
        http.get("/api/v1/systems/:id/integrations/", ({ request }) => {
          url = new URL(request.url).pathname
          return HttpResponse.json([mockIntegration])
        })
      )
      await getSystemIntegrations("sys-5")
      expect(url).toBe("/api/v1/systems/sys-5/integrations/")
    })
  })

  describe("createIntegration", () => {
    it("POST integration med korrekt body", async () => {
      let body: unknown = null
      server.use(
        http.post("/api/v1/integrations/", async ({ request }) => {
          body = await request.json()
          return HttpResponse.json(mockIntegration, { status: 201 })
        })
      )
      await createIntegration({
        source_system_id: "sys-1",
        target_system_id: "sys-2",
        integration_type: IntegrationType.API,
      })
      expect(body).toMatchObject({
        source_system_id: "sys-1",
        target_system_id: "sys-2",
        integration_type: "api",
      })
    })
  })

  describe("importFile", () => {
    it("POST till /import/systems med multipart/form-data", async () => {
      let contentType: string | null = null
      server.use(
        http.post("/api/v1/import/:type", ({ request }) => {
          contentType = request.headers.get("content-type")
          return HttpResponse.json({ imported: 5, errors: [] })
        })
      )
      const file = new File(["data"], "test.csv", { type: "text/csv" })
      await importFile("systems", file, "org-1")
      // multipart/form-data sätts automatiskt av axios
      expect(contentType).toContain("multipart/form-data")
    })

    it("skickar organization_id som query-param för system-import", async () => {
      let queryOrgId: string | null = null
      server.use(
        http.post("/api/v1/import/:type", ({ request }) => {
          queryOrgId = new URL(request.url).searchParams.get("organization_id")
          return HttpResponse.json({ imported: 3, errors: [] })
        })
      )
      const file = new File(["data"], "test.csv", { type: "text/csv" })
      await importFile("systems", file, "org-99")
      expect(queryOrgId).toBe("org-99")
    })

    it("returnerar ImportResult med imported och errors", async () => {
      const file = new File(["data"], "test.csv", { type: "text/csv" })
      const result = await importFile("classifications", file)
      expect(result.imported).toBe(3)
      expect(result.errors).toEqual([])
    })

    it("anropar korrekt path för owners-import", async () => {
      let url: string | null = null
      server.use(
        http.post("/api/v1/import/:type", ({ request }) => {
          url = new URL(request.url).pathname
          return HttpResponse.json({ imported: 2, errors: [] })
        })
      )
      const file = new File(["data"], "owners.csv", { type: "text/csv" })
      await importFile("owners", file)
      expect(url).toBe("/api/v1/import/owners")
    })
  })

  describe("GDPR-behandlingar", () => {
    it("getGDPRTreatments returnerar tom lista", async () => {
      const result = await getGDPRTreatments("sys-1")
      expect(result).toEqual([])
    })

    it("createGDPRTreatment POST till /systems/:id/gdpr/", async () => {
      let url: string | null = null
      server.use(
        http.post("/api/v1/systems/:id/gdpr/", ({ request }) => {
          url = new URL(request.url).pathname
          return HttpResponse.json(
            {
              id: "g-1",
              system_id: "sys-1",
              dpia_conducted: false,
              created_at: "",
              updated_at: "",
            },
            { status: 201 }
          )
        })
      )
      await createGDPRTreatment("sys-1", { dpia_conducted: false })
      expect(url).toBe("/api/v1/systems/sys-1/gdpr/")
    })

    it("deleteGDPRTreatment DELETE till /gdpr/:id", async () => {
      let deleteCalled = false
      server.use(
        http.delete("/api/v1/gdpr/:id", () => {
          deleteCalled = true
          return new HttpResponse(null, { status: 204 })
        })
      )
      await deleteGDPRTreatment("gdpr-1")
      expect(deleteCalled).toBe(true)
    })
  })

  describe("Avtal", () => {
    it("getContracts returnerar tom lista", async () => {
      const result = await getContracts("sys-1")
      expect(result).toEqual([])
    })

    it("createContract POST till /systems/:id/contracts/", async () => {
      let body: unknown = null
      server.use(
        http.post("/api/v1/systems/:id/contracts/", async ({ request }) => {
          body = await request.json()
          return HttpResponse.json(
            {
              id: "c-1",
              system_id: "sys-1",
              supplier_name: "Leverantör",
              auto_renewal: false,
              created_at: "",
              updated_at: "",
            },
            { status: 201 }
          )
        })
      )
      await createContract("sys-1", { supplier_name: "Leverantör" })
      expect(body).toMatchObject({ supplier_name: "Leverantör" })
    })

    it("deleteContract DELETE till /contracts/:id", async () => {
      let deleteCalled = false
      server.use(
        http.delete("/api/v1/contracts/:id", () => {
          deleteCalled = true
          return new HttpResponse(null, { status: 204 })
        })
      )
      await deleteContract("con-1")
      expect(deleteCalled).toBe(true)
    })
  })

  describe("Felhantering - HTTP-statuskoder", () => {
    it("getSystems kastar vid 401 Unauthorized", async () => {
      server.use(
        http.get("/api/v1/systems/", () =>
          HttpResponse.json({ detail: "Unauthorized" }, { status: 401 })
        )
      )
      await expect(getSystems()).rejects.toThrow()
    })

    it("getSystem kastar vid 403 Forbidden", async () => {
      server.use(
        http.get("/api/v1/systems/:id", () =>
          HttpResponse.json({ detail: "Forbidden" }, { status: 403 })
        )
      )
      await expect(getSystem("sys-1")).rejects.toThrow()
    })

    it("createSystem kastar vid 422 Validation Error", async () => {
      server.use(
        http.post("/api/v1/systems/", () =>
          HttpResponse.json(
            { detail: [{ loc: ["body", "name"], msg: "required" }] },
            { status: 422 }
          )
        )
      )
      await expect(
        createSystem({
          organization_id: "org-1",
          name: "",
          description: "",
          system_category: SystemCategory.VERKSAMHETSSYSTEM,
        })
      ).rejects.toThrow()
    })

    it("updateSystem kastar vid 404", async () => {
      server.use(
        http.patch("/api/v1/systems/:id", () =>
          HttpResponse.json({ detail: "Not found" }, { status: 404 })
        )
      )
      await expect(updateSystem("nonexistent", { name: "X" })).rejects.toThrow()
    })

    it("getOrganizations kastar vid nätverksfel", async () => {
      server.use(
        http.get("/api/v1/organizations/", () =>
          HttpResponse.error()
        )
      )
      await expect(getOrganizations()).rejects.toThrow()
    })
  })

  describe("Request-headers", () => {
    it("axios sätter Accept: application/json som standard", async () => {
      let acceptHeader: string | null = null
      server.use(
        http.get("/api/v1/organizations/", ({ request }) => {
          acceptHeader = request.headers.get("accept")
          return HttpResponse.json([mockOrg])
        })
      )
      await getOrganizations()
      expect(acceptHeader).toContain("application/json")
    })

    it("baseURL är /api/v1", async () => {
      let capturedPath: string | null = null
      server.use(
        http.get("/api/v1/systems/", ({ request }) => {
          capturedPath = new URL(request.url).pathname
          return HttpResponse.json({ items: [], total: 0, limit: 25, offset: 0 })
        })
      )
      await getSystems()
      expect(capturedPath).toMatch(/^\/api\/v1\//)
    })
  })

  describe("createOwner", () => {
    it("POST owner med korrekt body", async () => {
      let body: unknown = null
      server.use(
        http.post("/api/v1/systems/:id/owners/", async ({ request }) => {
          body = await request.json()
          return HttpResponse.json(mockOwner, { status: 201 })
        })
      )
      await createOwner("sys-1", {
        system_id: "sys-1",
        organization_id: "org-1",
        role: OwnerRole.SYSTEM_OWNER,
        name: "Ny Ägare",
        email: "ny@test.se",
      })
      expect(body).toMatchObject({ name: "Ny Ägare" })
    })

    it("returnerar skapad owner", async () => {
      const result = await createOwner("sys-1", {
        system_id: "sys-1",
        organization_id: "org-1",
        role: OwnerRole.INFORMATION_OWNER,
        name: "Test",
      })
      expect(result.id).toBe("own-1")
    })
  })

  describe("deleteIntegration", () => {
    it("DELETE integration korrekt", async () => {
      let deletedId: string | null = null
      server.use(
        http.delete("/api/v1/integrations/:id", ({ params }) => {
          deletedId = params.id as string
          return new HttpResponse(null, { status: 204 })
        })
      )
      await deleteIntegration("int-99")
      expect(deletedId).toBe("int-99")
    })
  })

  describe("importFile - felhantering", () => {
    it("kastar fel vid 400 Bad Request", async () => {
      server.use(
        http.post("/api/v1/import/:type", () =>
          HttpResponse.json({ detail: "Ogiltig fil" }, { status: 400 })
        )
      )
      const file = new File(["data"], "bad.txt", { type: "text/plain" })
      await expect(importFile("systems", file)).rejects.toThrow()
    })

    it("skickar utan organization_id om ej angiven", async () => {
      let queryOrgId: string | null = "initial"
      server.use(
        http.post("/api/v1/import/:type", ({ request }) => {
          queryOrgId = new URL(request.url).searchParams.get("organization_id")
          return HttpResponse.json({ imported: 0, errors: [] })
        })
      )
      const file = new File(["data"], "test.csv", { type: "text/csv" })
      await importFile("classifications", file)
      expect(queryOrgId).toBeNull()
    })
  })
})
