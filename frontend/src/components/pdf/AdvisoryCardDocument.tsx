"use client";
import "@/lib/pdf-fonts";
import { Document, Page, View, Text, StyleSheet } from "@react-pdf/renderer";

interface AdvisoryCardDocumentProps {
  zone: string;
  syndrome: string;
  priorityAction: string;
  keyMessages: string[];
  recommendedActions: string[];
  seasonalGuidance: string[];
  warningFlags: string[];
  monitoringTasks: string[];
  locale: "en" | "am" | "om";
  zone_am?: string;
  priorityAction_am?: string;
  keyMessages_am?: string[];
  recommendedActions_am?: string[];
}

const styles = StyleSheet.create({
  page: {
    size: "A5",
    backgroundColor: "#ffffff",
    fontFamily: "Inter",
    fontSize: 10,
    paddingTop: "12mm",
    paddingBottom: "12mm",
    paddingLeft: "12mm",
    paddingRight: "12mm",
  },
  headerStrip: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    paddingBottom: "3mm",
    marginBottom: "4mm",
    borderBottom: "0.5pt solid #2d6a4f",
  },
  headerLeft: {
    fontSize: 11,
    fontWeight: 600,
    color: "#1a1a1a",
  },
  headerRight: {
    fontSize: 8,
    fontWeight: 400,
    color: "#555555",
    textAlign: "right",
    maxWidth: "60mm",
  },
  zoneBlock: {
    marginBottom: "4mm",
  },
  zoneName: {
    fontSize: 16,
    fontWeight: 600,
    color: "#1a1a1a",
    marginBottom: "1mm",
  },
  syndromeText: {
    fontSize: 10,
    fontStyle: "italic",
    color: "#555555",
  },
  sectionBlock: {
    marginBottom: "4mm",
  },
  sectionLabel: {
    fontSize: 7,
    fontWeight: 600,
    textTransform: "uppercase",
    color: "#555555",
    marginBottom: "2mm",
  },
  sectionLabelWarning: {
    fontSize: 7,
    fontWeight: 600,
    textTransform: "uppercase",
    color: "#e07a2f",
    marginBottom: "2mm",
  },
  priorityText: {
    fontSize: 14,
    fontWeight: 600,
    color: "#2d6a4f",
  },
  bodyText: {
    fontSize: 10,
    fontWeight: 400,
    color: "#1a1a1a",
  },
  bulletItem: {
    flexDirection: "row",
    marginBottom: "1.5mm",
  },
  bulletMarker: {
    color: "#2d6a4f",
    marginRight: "2mm",
    fontSize: 10,
  },
  checkMarker: {
    color: "#2d6a4f",
    marginRight: "2mm",
    fontSize: 10,
  },
  dashMarker: {
    color: "#555555",
    marginRight: "2mm",
    fontSize: 10,
  },
  warningText: {
    fontSize: 9,
    color: "#e07a2f",
  },
  amharicText: {
    fontFamily: "NotoSerifEthiopic",
    fontSize: 10,
    color: "#1a1a1a",
  },
  amharicMuted: {
    fontFamily: "NotoSerifEthiopic",
    fontSize: 10,
    color: "#555555",
  },
  hairline: {
    borderTop: "0.3pt solid #cccccc",
    marginTop: "1mm",
    marginBottom: "1mm",
  },
  footerStrip: {
    borderTop: "0.5pt solid #cccccc",
    paddingTop: "2mm",
    flexDirection: "row",
    justifyContent: "center",
    marginTop: "auto",
  },
  footerText: {
    fontSize: 7,
    color: "#555555",
  },
});

export function AdvisoryCardDocument({
  zone,
  syndrome,
  priorityAction,
  keyMessages,
  recommendedActions,
  seasonalGuidance,
  warningFlags,
  monitoringTasks,
  locale,
  zone_am,
  priorityAction_am,
  keyMessages_am,
  recommendedActions_am,
}: AdvisoryCardDocumentProps) {
  const showAmharic = locale === "am";

  return (
    <Document title="Community Advisory Card" language={locale}>
      <Page size="A5" style={styles.page}>

        {/* 1. Header strip */}
        <View style={styles.headerStrip}>
          <Text style={styles.headerLeft}>LIRA-AI</Text>
          <Text style={styles.headerRight}>Alliance of Bioversity International and CIAT · CGIAR MFL</Text>
        </View>

        {/* 2. Zone + Syndrome */}
        <View style={styles.zoneBlock}>
          <Text style={styles.zoneName}>{zone}</Text>
          {showAmharic && zone_am ? (
            <>
              <View style={styles.hairline} />
              <Text style={styles.amharicText}>{zone_am}</Text>
            </>
          ) : null}
          <Text style={styles.syndromeText}>{syndrome}</Text>
        </View>

        {/* 3. Priority Action */}
        <View style={styles.sectionBlock}>
          <Text style={styles.sectionLabel}>PRIORITY ACTION</Text>
          <Text style={styles.priorityText}>{priorityAction}</Text>
          {showAmharic && priorityAction_am ? (
            <>
              <View style={styles.hairline} />
              <Text style={styles.amharicText}>{priorityAction_am}</Text>
            </>
          ) : null}
        </View>

        {/* 4. Key Messages */}
        {keyMessages.length > 0 && (
          <View style={styles.sectionBlock}>
            <Text style={styles.sectionLabel}>KEY MESSAGES</Text>
            {keyMessages.map((msg, i) => (
              <View key={i} style={styles.bulletItem}>
                <Text style={styles.bulletMarker}>▸</Text>
                <Text style={styles.bodyText}>{msg}</Text>
              </View>
            ))}
            {showAmharic && keyMessages_am && keyMessages_am.length > 0 ? (
              <>
                <View style={styles.hairline} />
                {keyMessages_am.map((msg, i) => (
                  <View key={i} style={styles.bulletItem}>
                    <Text style={styles.bulletMarker}>▸</Text>
                    <Text style={styles.amharicText}>{msg}</Text>
                  </View>
                ))}
              </>
            ) : null}
          </View>
        )}

        {/* 5. Recommended Actions */}
        {recommendedActions.length > 0 && (
          <View style={styles.sectionBlock}>
            <Text style={styles.sectionLabel}>RECOMMENDED ACTIONS</Text>
            {recommendedActions.map((action, i) => (
              <View key={i} style={styles.bulletItem}>
                <Text style={styles.checkMarker}>✓</Text>
                <Text style={styles.bodyText}>{action}</Text>
              </View>
            ))}
            {showAmharic && recommendedActions_am && recommendedActions_am.length > 0 ? (
              <>
                <View style={styles.hairline} />
                {recommendedActions_am.map((action, i) => (
                  <View key={i} style={styles.bulletItem}>
                    <Text style={styles.checkMarker}>✓</Text>
                    <Text style={styles.amharicText}>{action}</Text>
                  </View>
                ))}
              </>
            ) : null}
          </View>
        )}

        {/* 6. Seasonal Guidance */}
        {seasonalGuidance.length > 0 && (
          <View style={styles.sectionBlock}>
            <Text style={styles.sectionLabel}>SEASONAL GUIDANCE</Text>
            {seasonalGuidance.map((item, i) => (
              <View key={i} style={styles.bulletItem}>
                <Text style={styles.bulletMarker}>▸</Text>
                <Text style={styles.bodyText}>{item}</Text>
              </View>
            ))}
          </View>
        )}

        {/* 7. Warning Flags */}
        {warningFlags.length > 0 && (
          <View style={styles.sectionBlock}>
            <Text style={styles.sectionLabelWarning}>WARNING FLAGS</Text>
            {warningFlags.map((flag, i) => (
              <View key={i} style={styles.bulletItem}>
                <Text style={[styles.warningText, { marginRight: "2mm" }]}>!</Text>
                <Text style={styles.warningText}>{flag}</Text>
              </View>
            ))}
          </View>
        )}

        {/* 8. Monitoring Tasks */}
        {monitoringTasks.length > 0 && (
          <View style={styles.sectionBlock}>
            <Text style={styles.sectionLabel}>MONITORING TASKS</Text>
            {monitoringTasks.map((task, i) => (
              <View key={i} style={styles.bulletItem}>
                <Text style={styles.dashMarker}>—</Text>
                <Text style={styles.bodyText}>{task}</Text>
              </View>
            ))}
          </View>
        )}

        {/* 9. Footer strip */}
        <View style={styles.footerStrip}>
          <Text style={styles.footerText}>LIRA-AI · CGIAR MFL · Ethiopia</Text>
        </View>

      </Page>
    </Document>
  );
}
