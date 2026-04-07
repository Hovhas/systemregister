import { Criticality } from "@/types"
import { categoryLabels, lifecycleLabels, criticalityLabels } from "@/lib/labels"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { InfoRow } from "./helpers"

export function OversiktTab({ system }: { system: NonNullable<any> }) {
  if (!system) return null
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Grundinformation</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col">
          <InfoRow label="Kategori" value={categoryLabels[system.system_category]} />
          <InfoRow label="Verksamhetsområde" value={system.business_area} />
          <InfoRow label="Alias" value={system.aliases} />
          <InfoRow label="Beskrivning" value={system.description} />
          <InfoRow
            label="Kritikalitet"
            value={
              <span className={`inline-flex items-center text-xs font-medium ${
                system.criticality === Criticality.CRITICAL
                  ? "text-red-700"
                  : system.criticality === Criticality.HIGH
                  ? "text-orange-700"
                  : system.criticality === Criticality.MEDIUM
                  ? "text-yellow-700"
                  : "text-green-700"
              }`}>
                {criticalityLabels[system.criticality]}
              </span>
            }
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Driftmiljö</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col">
          <InfoRow label="Driftsättningsmodell" value={system.hosting_model} />
          <InfoRow label="Molnleverantör" value={system.cloud_provider} />
          <InfoRow label="Dataplacering" value={system.data_location_country} />
          <InfoRow label="Produktnamn" value={system.product_name} />
          <InfoRow label="Version" value={system.product_version} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Livscykel</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col">
          <InfoRow label="Status" value={lifecycleLabels[system.lifecycle_status]} />
          <InfoRow label="Driftsatt" value={system.deployment_date} />
          <InfoRow label="Planerad avveckling" value={system.planned_decommission_date} />
          <InfoRow label="Supportslut" value={system.end_of_support_date} />
          <InfoRow label="Senaste riskbedömning" value={system.last_risk_assessment_date} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Compliance</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col">
          <InfoRow
            label="NIS2-tillämplig"
            value={
              <Badge variant={system.nis2_applicable ? "default" : "outline"}>
                {system.nis2_applicable ? "Ja" : "Nej"}
              </Badge>
            }
          />
          {system.nis2_classification && (
            <InfoRow label="NIS2-klassning" value={system.nis2_classification} />
          )}
          <InfoRow
            label="Behandlar personuppgifter"
            value={system.treats_personal_data ? "Ja" : "Nej"}
          />
          <InfoRow
            label="Behandlar känsliga uppgifter"
            value={system.treats_sensitive_data ? "Ja" : "Nej"}
          />
          <InfoRow
            label="Tredjelandsöverföring"
            value={system.third_country_transfer ? "Ja" : "Nej"}
          />
          <InfoRow
            label="Förhöjt skyddsbehov"
            value={system.has_elevated_protection ? "Ja" : "Nej"}
          />
          <InfoRow label="KLASSA-referens" value={system.klassa_reference_id} />
        </CardContent>
      </Card>
    </div>
  )
}
