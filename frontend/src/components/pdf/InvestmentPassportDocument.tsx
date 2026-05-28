"use client"
import "@/lib/pdf-fonts"
import { Document, Page, View, Text, StyleSheet } from "@react-pdf/renderer"

interface InvestmentPassportDocumentProps {
  passport: Record<string, unknown>
  agentResult: Record<string, unknown>
  locale: "en" | "am" | "om"
  date: string
}

function scoreColor(v: number): string {
  if (v >= 0.7) return "#2d7d4f"
  if (v >= 0.4) return "#b8860b"
  return "#c1121f"
}

function pct(v: unknown): string {
  const n = typeof v === "number" ? v : parseFloat(String(v ?? 0))
  return isNaN(n) ? "N/A" : `${Math.round(n * 100)}%`
}

const styles = StyleSheet.create({
  page: {
    size: "A4",
    paddingTop: "20mm",
    paddingRight: "20mm",
    paddingBottom: "20mm",
    paddingLeft: "20mm",
    backgroundColor: "#ffffff",
    fontFamily: "Inter",
    fontSize: 10,
  },
  gcfHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 3,
    paddingBottom: 3,
    borderBottom: "1pt solid #00a651",
  },
  gcfLabel: {
    fontSize: 10,
    fontWeight: 600,
    color: "#00a651",
  },
  gcfSubtitle: {
    fontSize: 8,
    color: "#555555",
  },
  projectTitle: {
    fontSize: 18,
    fontWeight: 600,
    color: "#1a1a1a",
    lineHeight: 1.25,
    marginBottom: 2,
  },
  projectGeo: {
    fontSize: 10,
    color: "#555555",
    marginBottom: 1,
  },
  passportId: {
    fontSize: 8,
    color: "#888888",
    marginBottom: 6,
  },
  scorecardRow: {
    flexDirection: "row",
    gap: 4,
    marginBottom: 6,
  },
  scorecardBox: {
    flex: 1,
    border: "0.5pt solid #dddddd",
    padding: 4,
    alignItems: "center",
  },
  scorecardLabel: {
    fontSize: 7,
    fontWeight: 600,
    textTransform: "uppercase",
    color: "#555555",
    marginBottom: 2,
  },
  sectionLabel: {
    fontSize: 10,
    fontWeight: 600,
    textTransform: "uppercase",
    color: "#00a651",
    marginBottom: 3,
  },
  bodyText: {
    fontSize: 10,
    lineHeight: 1.5,
    color: "#1a1a1a",
    marginBottom: 4,
  },
  listItem: {
    flexDirection: "row",
    marginBottom: 2.5,
    fontSize: 10,
  },
  listMarker: {
    color: "#00a651",
    marginRight: 4,
  },
  benefitsRow: {
    flexDirection: "row",
    gap: 6,
    marginBottom: 6,
  },
  benefitsCol: {
    flex: 1,
  },
  benefitsLabel: {
    fontSize: 9,
    fontWeight: 600,
    color: "#555555",
    marginBottom: 2,
  },
  benefitItem: {
    fontSize: 9,
    color: "#1a1a1a",
    marginBottom: 2,
  },
  tableHeaderRow: {
    flexDirection: "row",
    backgroundColor: "#f5f5f5",
  },
  tableBodyRow: {
    flexDirection: "row",
  },
  tableAltRow: {
    flexDirection: "row",
    backgroundColor: "#fafafa",
  },
  tableCell: {
    paddingHorizontal: 2,
    paddingVertical: 1.5,
    borderRight: "0.5pt solid #dddddd",
    borderBottom: "0.5pt solid #dddddd",
    fontSize: 8,
  },
  tableHeaderCell: {
    fontWeight: 600,
  },
  alertBox: {
    border: "1pt solid #e07a2f",
    padding: 4,
    marginBottom: 6,
  },
  alertHeader: {
    fontSize: 8,
    fontWeight: 600,
    color: "#e07a2f",
    marginBottom: 2,
  },
  alertItem: {
    fontSize: 9,
    color: "#333333",
    marginBottom: 1.5,
  },
  assumptionItem: {
    fontSize: 8,
    color: "#555555",
    marginBottom: 1.5,
  },
  evidenceItem: {
    fontSize: 8,
    color: "#888888",
    fontStyle: "italic",
    marginBottom: 1,
  },
  footer: {
    position: "absolute",
    bottom: "20mm",
    left: "20mm",
    right: "20mm",
    borderTop: "0.5pt solid #dddddd",
    paddingTop: 3,
    flexDirection: "row",
    justifyContent: "space-between",
  },
  footerText: {
    fontSize: 7,
    color: "#888888",
  },
  sectionView: {
    marginBottom: 6,
  },
})

export function InvestmentPassportDocument({
  passport,
  agentResult,
  locale,
  date,
}: InvestmentPassportDocumentProps) {
  const packageName = String(passport.package_name ?? "Investment Package")
  const targetGeo = String(passport.target_geography ?? "")
  const passportId = String(passport.passport_id ?? "")
  const financingWindows =
    (passport.financing_windows as Array<Record<string, unknown>>) ?? []
  const readiness = (agentResult.investment_readiness_score as number) ?? 0
  const robustness = (agentResult.climate_robustness_score as number) ?? 0
  const confidence = (agentResult.confidence as number) ?? 0
  const problemDiagnosis = String(agentResult.problem_diagnosis ?? "")
  const climateRationale = String(agentResult.climate_rationale ?? "")
  const interventions = (agentResult.intervention_components as string[]) ?? []
  const partners = (agentResult.implementation_partners as string[]) ?? []
  const ecosystemBenefits = (agentResult.ecosystem_benefits as string[]) ?? []
  const livelihoodBenefits = (agentResult.livelihood_benefits as string[]) ?? []
  const mrvIndicators = (agentResult.mrv_indicators as string[]) ?? []
  const reportingFreq = String(agentResult.reporting_frequency ?? "")
  const maladaptationAlerts =
    (agentResult.maladaptation_alerts as string[]) ?? []
  const assumptions = (agentResult.assumptions as string[]) ?? []
  const evidenceTrail = (agentResult.evidence_trail as string[]) ?? []

  function eligibilityColor(e: unknown): string {
    const val = String(e ?? "").toLowerCase()
    if (val === "likely") return "#2d7d4f"
    if (val === "possible") return "#b8860b"
    if (val === "unlikely") return "#888888"
    return "#555555"
  }

  return (
    <Document title={packageName} language={locale}>
      <Page size="A4" style={styles.page}>
        {/* Zone 1 — GCF Header */}
        <View style={styles.gcfHeader}>
          <View>
            <Text style={styles.gcfLabel}>GREEN CLIMATE FUND</Text>
            <Text style={styles.gcfSubtitle}>
              Concept Note — Investment Passport
            </Text>
          </View>
          <Text
            style={{ fontSize: 8, color: "#555555", textAlign: "right" }}
          >
            {`LIRA-AI · Alliance of Bioversity\nInternational and CIAT`}
          </Text>
        </View>

        {/* Zone 2 — Project Title Block */}
        <Text style={styles.projectTitle}>{packageName}</Text>
        <Text style={styles.projectGeo}>{targetGeo}</Text>
        {passportId ? (
          <Text style={styles.passportId}>Passport ID: {passportId}</Text>
        ) : null}

        {/* Zone 3 — Scorecard Row */}
        <View style={styles.scorecardRow}>
          {[
            { label: "Investment Readiness", value: readiness },
            { label: "Climate Robustness", value: robustness },
            { label: "Confidence", value: confidence },
          ].map(({ label, value }) => (
            <View key={label} style={styles.scorecardBox}>
              <Text style={styles.scorecardLabel}>{label}</Text>
              <Text
                style={{
                  fontSize: 20,
                  fontWeight: 600,
                  color: scoreColor(value),
                }}
              >
                {pct(value)}
              </Text>
            </View>
          ))}
        </View>

        {/* Section 1 — Problem Diagnosis */}
        <View break style={styles.sectionView}>
          <Text style={styles.sectionLabel}>PROBLEM DIAGNOSIS</Text>
          <Text style={styles.bodyText}>{problemDiagnosis}</Text>
        </View>

        {/* Section 2 — Climate Rationale */}
        <View break style={styles.sectionView}>
          <Text style={styles.sectionLabel}>CLIMATE RATIONALE</Text>
          <Text style={styles.bodyText}>{climateRationale}</Text>
        </View>

        {/* Section 3 — Intervention Components */}
        <View break style={styles.sectionView}>
          <Text style={styles.sectionLabel}>INTERVENTION COMPONENTS</Text>
          {interventions.map((item, index) => (
            <View key={item} style={styles.listItem}>
              <Text style={styles.listMarker}>{index + 1}.</Text>
              <Text style={{ fontSize: 10, color: "#1a1a1a", flex: 1 }}>
                {item}
              </Text>
            </View>
          ))}
        </View>

        {/* Section 4 — Financing Plan */}
        <View break style={styles.sectionView}>
          <Text style={styles.sectionLabel}>FINANCING PLAN</Text>
          <View style={{ border: "0.5pt solid #dddddd" }}>
            {/* Header row */}
            <View style={styles.tableHeaderRow}>
              {[
                { label: "Finance Window", width: "40%" },
                { label: "Eligibility", width: "20%" },
                { label: "Cost / ha", width: "20%" },
                { label: "Note", width: "20%" },
              ].map(({ label, width }) => (
                <Text
                  key={label}
                  style={[styles.tableCell, styles.tableHeaderCell, { width }]}
                >
                  {label}
                </Text>
              ))}
            </View>
            {/* Body rows */}
            {financingWindows.map((fw, idx) => {
              const RowStyle =
                idx % 2 === 0 ? styles.tableBodyRow : styles.tableAltRow
              return (
                <View key={idx} style={RowStyle}>
                  <Text style={[styles.tableCell, { width: "40%" }]}>
                    {String(fw.window ?? "")}
                  </Text>
                  <Text
                    style={[
                      styles.tableCell,
                      {
                        width: "20%",
                        color: eligibilityColor(fw.eligibility),
                      },
                    ]}
                  >
                    {String(fw.eligibility ?? "")}
                  </Text>
                  <Text style={[styles.tableCell, { width: "20%" }]}>
                    ${String(fw.cost_per_ha_usd ?? "")}
                  </Text>
                  <Text style={[styles.tableCell, { width: "20%" }]}>
                    {String(fw.eligibility_note ?? "")}
                  </Text>
                </View>
              )
            })}
          </View>
        </View>

        {/* Section 5 — Implementation Partners */}
        <View break style={styles.sectionView}>
          <Text style={styles.sectionLabel}>IMPLEMENTATION PARTNERS</Text>
          {partners.map((p) => (
            <View key={p} style={styles.listItem}>
              <Text style={styles.listMarker}>•</Text>
              <Text style={{ fontSize: 10, color: "#1a1a1a", flex: 1 }}>
                {p}
              </Text>
            </View>
          ))}
        </View>

        {/* Section 6 — Expected Benefits */}
        <View break style={styles.sectionView}>
          <Text style={styles.sectionLabel}>EXPECTED BENEFITS</Text>
          <View style={styles.benefitsRow}>
            <View style={styles.benefitsCol}>
              <Text style={styles.benefitsLabel}>Ecosystem Benefits</Text>
              {ecosystemBenefits.map((b) => (
                <Text key={b} style={styles.benefitItem}>
                  {"▸"} {b}
                </Text>
              ))}
            </View>
            <View style={styles.benefitsCol}>
              <Text style={styles.benefitsLabel}>Livelihood Benefits</Text>
              {livelihoodBenefits.map((b) => (
                <Text key={b} style={styles.benefitItem}>
                  {"▸"} {b}
                </Text>
              ))}
            </View>
          </View>
        </View>

        {/* Section 7 — MRV Framework */}
        <View break style={styles.sectionView}>
          <Text style={styles.sectionLabel}>MRV FRAMEWORK</Text>
          {reportingFreq ? (
            <Text style={styles.bodyText}>
              Reporting frequency: {reportingFreq}
            </Text>
          ) : null}
          {mrvIndicators.map((ind) => (
            <View key={ind} style={styles.listItem}>
              <Text style={styles.listMarker}>•</Text>
              <Text style={{ fontSize: 10, color: "#1a1a1a", flex: 1 }}>
                {ind}
              </Text>
            </View>
          ))}
        </View>

        {/* Maladaptation Alerts — only if present */}
        {maladaptationAlerts.length > 0 ? (
          <View break style={styles.alertBox}>
            <Text style={styles.alertHeader}>
              MALADAPTATION ALERTS — REVIEW REQUIRED
            </Text>
            {maladaptationAlerts.map((alert) => (
              <Text key={alert} style={styles.alertItem}>
                • {alert}
              </Text>
            ))}
          </View>
        ) : null}

        {/* Assumptions & Evidence Trail */}
        <View break style={styles.sectionView}>
          <Text
            style={{
              fontSize: 10,
              fontWeight: 600,
              textTransform: "uppercase",
              color: "#888888",
              marginBottom: 3,
            }}
          >
            ASSUMPTIONS & EVIDENCE TRAIL
          </Text>
          {assumptions.map((a) => (
            <Text key={a} style={styles.assumptionItem}>
              • {a}
            </Text>
          ))}
          {evidenceTrail.map((e) => (
            <Text key={e} style={styles.evidenceItem}>
              — {e}
            </Text>
          ))}
        </View>

        {/* Footer */}
        <View style={styles.footer} fixed>
          <Text style={styles.footerText}>
            Investment Passport generated by LIRA-AI · Alliance of Bioversity
            International and CIAT · CGIAR MFL · {date}
          </Text>
          <Text style={styles.footerText}>GCF Concept Note Format</Text>
        </View>
      </Page>
    </Document>
  )
}
