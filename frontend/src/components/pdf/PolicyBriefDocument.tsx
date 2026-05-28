"use client";
import "@/lib/pdf-fonts";
import { Document, Page, View, Text, StyleSheet } from "@react-pdf/renderer";

interface PolicyBriefDocumentProps {
  title: string;
  zone: string;
  date: string;
  executiveSummary: string;
  diagnosisHighlights: string[];
  climateContext: string[];
  recommendedPackage: string[];
  policyHooks: string[];
  investmentAsk: string;
  nextSteps: string[];
  locale: "en" | "am" | "om";
}

const styles = StyleSheet.create({
  page: {
    backgroundColor: "#ffffff",
    fontFamily: "Inter",
    fontSize: 10,
    paddingTop: "20mm",
    paddingBottom: "20mm",
    paddingLeft: "20mm",
    paddingRight: "20mm",
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    paddingBottom: "3mm",
    marginBottom: "5mm",
    borderBottom: "0.5pt solid #2d6a4f",
  },
  headerLeft: {
    fontSize: 8,
    fontWeight: 400,
    color: "#555555",
    maxWidth: "70mm",
  },
  headerRight: {
    fontSize: 8,
    fontWeight: 400,
    color: "#555555",
    textAlign: "right",
  },
  badge: {
    border: "0.75pt solid #2d6a4f",
    color: "#2d6a4f",
    fontSize: 8,
    fontWeight: 600,
    textTransform: "uppercase",
    paddingLeft: "3mm",
    paddingRight: "3mm",
    paddingTop: "1mm",
    paddingBottom: "1mm",
    alignSelf: "flex-start",
    marginBottom: "4mm",
  },
  docTitle: {
    fontSize: 18,
    fontWeight: 600,
    color: "#1a1a1a",
    lineHeight: 1.25,
    marginBottom: "3mm",
  },
  metadata: {
    fontSize: 8,
    color: "#555555",
    marginBottom: "6mm",
  },
  execSummaryContainer: {
    marginBottom: "5mm",
  },
  execSummaryLabel: {
    fontSize: 7,
    fontWeight: 600,
    textTransform: "uppercase",
    color: "#2d6a4f",
    marginBottom: "2mm",
  },
  execSummaryText: {
    fontSize: 11,
    lineHeight: 1.6,
    borderLeft: "2pt solid #2d6a4f",
    paddingLeft: "4mm",
    color: "#1a1a1a",
  },
  sectionBlock: {
    marginBottom: "4mm",
  },
  sectionHeading: {
    fontSize: 12,
    fontWeight: 600,
    color: "#1a1a1a",
    marginBottom: "2mm",
    marginTop: "4mm",
  },
  bulletItem: {
    flexDirection: "row",
    marginBottom: "1.5mm",
    fontSize: 10,
  },
  bulletMarker: {
    color: "#2d6a4f",
    marginRight: "2mm",
    fontSize: 10,
  },
  bulletText: {
    fontSize: 10,
    color: "#1a1a1a",
    flex: 1,
  },
  numberedMarker: {
    color: "#2d6a4f",
    marginRight: "2mm",
    fontSize: 10,
    minWidth: "5mm",
  },
  investmentBox: {
    border: "0.75pt solid #b7a57a",
    backgroundColor: "#fdfbf6",
    padding: "4mm",
    marginTop: "5mm",
  },
  investmentLabel: {
    fontSize: 7,
    fontWeight: 600,
    textTransform: "uppercase",
    color: "#8b4513",
    marginBottom: "2mm",
  },
  investmentText: {
    fontSize: 12,
    fontWeight: 600,
    color: "#1a1a1a",
  },
  footerStrip: {
    borderTop: "0.5pt solid #dddddd",
    paddingTop: "2mm",
    marginTop: "auto",
  },
  footerText: {
    fontSize: 7,
    color: "#555555",
  },
  sectionRule: {
    borderTop: "0.3pt solid #dddddd",
    marginBottom: "2mm",
  },
});

export function PolicyBriefDocument({
  title,
  zone,
  date,
  executiveSummary,
  diagnosisHighlights,
  climateContext,
  recommendedPackage,
  policyHooks,
  investmentAsk,
  nextSteps,
  locale,
}: PolicyBriefDocumentProps) {
  return (
    <Document title={title} language={locale}>
      <Page size="A4" style={styles.page}>

        {/* 1. Header rule */}
        <View style={styles.headerRow}>
          <Text style={styles.headerLeft}>Alliance of Bioversity International and CIAT</Text>
          <Text style={styles.headerRight}>CGIAR Multifunctional Landscapes</Text>
        </View>

        {/* 2. Badge */}
        <Text style={styles.badge}>POLICY BRIEF</Text>

        {/* 3. Title */}
        <Text style={styles.docTitle}>{title}</Text>

        {/* 4. Metadata row */}
        <Text style={styles.metadata}>{zone} · {date} · LIRA-AI v0.1</Text>

        {/* 5. Executive Summary */}
        <View style={styles.execSummaryContainer}>
          <Text style={styles.execSummaryLabel}>EXECUTIVE SUMMARY</Text>
          <Text style={styles.execSummaryText}>{executiveSummary}</Text>
        </View>

        {/* 6. Sections */}
        {diagnosisHighlights.length > 0 && (
          <View break style={styles.sectionBlock}>
            <Text style={styles.sectionHeading}>Diagnosis Highlights</Text>
            {diagnosisHighlights.map((item, i) => (
              <View key={i} style={styles.bulletItem}>
                <Text style={styles.bulletMarker}>▸</Text>
                <Text style={styles.bulletText}>{item}</Text>
              </View>
            ))}
          </View>
        )}

        {climateContext.length > 0 && (
          <View break style={styles.sectionBlock}>
            <Text style={styles.sectionHeading}>Climate Context</Text>
            {climateContext.map((item, i) => (
              <View key={i} style={styles.bulletItem}>
                <Text style={styles.bulletMarker}>▸</Text>
                <Text style={styles.bulletText}>{item}</Text>
              </View>
            ))}
          </View>
        )}

        {recommendedPackage.length > 0 && (
          <View break style={styles.sectionBlock}>
            <Text style={styles.sectionHeading}>Recommended Package</Text>
            {recommendedPackage.map((item, i) => (
              <View key={i} style={styles.bulletItem}>
                <Text style={styles.bulletMarker}>▸</Text>
                <Text style={styles.bulletText}>{item}</Text>
              </View>
            ))}
          </View>
        )}

        {policyHooks.length > 0 && (
          <View break style={styles.sectionBlock}>
            <Text style={styles.sectionHeading}>Policy Hooks</Text>
            {policyHooks.map((item, i) => (
              <View key={i} style={styles.bulletItem}>
                <Text style={styles.bulletMarker}>▸</Text>
                <Text style={styles.bulletText}>{item}</Text>
              </View>
            ))}
          </View>
        )}

        {nextSteps.length > 0 && (
          <View break style={styles.sectionBlock}>
            <Text style={styles.sectionHeading}>Next Steps</Text>
            {nextSteps.map((item, i) => (
              <View key={i} style={styles.bulletItem}>
                <Text style={styles.numberedMarker}>{i + 1}.</Text>
                <Text style={styles.bulletText}>{item}</Text>
              </View>
            ))}
          </View>
        )}

        {/* 7. Investment Ask box */}
        {investmentAsk && (
          <View style={styles.investmentBox}>
            <Text style={styles.investmentLabel}>INVESTMENT ASK</Text>
            <Text style={styles.investmentText}>{investmentAsk}</Text>
          </View>
        )}

        {/* 8. Footer */}
        <View style={styles.footerStrip}>
          <Text style={styles.footerText}>
            LIRA-AI · Alliance of Bioversity International and CIAT · CGIAR MFL Programme · Omo-Ghibe Basin, Ethiopia
          </Text>
        </View>

      </Page>
    </Document>
  );
}
