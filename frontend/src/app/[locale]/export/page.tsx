"use client";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useLocale } from "next-intl";
import { pdf } from "@react-pdf/renderer";
import { getDiagnostic, getSyndromes, bootstrapSyndrome, getClimateReport, getPathways, listPassports, exportMarkdown, exportJson, createPassport, runInvestmentAgent } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { DownloadButton } from "@/components/ui/DownloadButton";
import { AdvisoryCardDocument } from "@/components/pdf/AdvisoryCardDocument";
import { PolicyBriefDocument } from "@/components/pdf/PolicyBriefDocument";
import { InvestmentPassportDocument } from "@/components/pdf/InvestmentPassportDocument";
import { Download, FileText, FileJson } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function ExportContent() {
  const params = useSearchParams();
  const projectId = params.get("project") ?? "MOCK-ETH-001";
  const t = useTranslations("export");
  const locale = useLocale() as "en" | "am" | "om";
  const [loading, setLoading] = useState(false);
  const [mdContent, setMdContent] = useState("");
  const [error, setError] = useState("");
  const [advisoryPdfLoading, setAdvisoryPdfLoading] = useState(false);
  const [policyPdfLoading, setPolicyPdfLoading] = useState(false);
  const [passportPdfLoading, setPassportPdfLoading] = useState(false);

  const buildBundle = async () => {
    setLoading(true);
    setError("");
    try {
      const [diagnostic, syndrome, pathways, passports] = await Promise.allSettled([
        getDiagnostic(projectId),
        getSyndromes(projectId),
        getPathways(projectId),
        listPassports(projectId),
      ]);

      let climate = null;
      try { climate = await getClimateReport(projectId); } catch { /* optional */ }

      return {
        project_id: projectId,
        project_name: `LIRA-AI Export — ${projectId}`,
        diagnostic: diagnostic.status === "fulfilled" ? diagnostic.value : null,
        syndrome: syndrome.status === "fulfilled" ? syndrome.value : null,
        climate,
        pathways: pathways.status === "fulfilled" ? pathways.value : null,
        tradeoffs: null,
        passports: passports.status === "fulfilled" ? passports.value as Record<string, unknown>[] : [],
        priority_index: [],
      };
    } finally {
      setLoading(false);
    }
  };

  const handleMarkdown = async () => {
    const bundle = await buildBundle();
    const md = await exportMarkdown(bundle);
    setMdContent(md);
  };

  const handleJsonDownload = async () => {
    const bundle = await buildBundle();
    const data = await exportJson(bundle);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `lira-ai-${projectId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleMdDownload = () => {
    const blob = new Blob([mdContent], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `lira-ai-${projectId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  async function getOrBootstrapSyndrome(): Promise<Record<string, unknown>> {
    const raw = await getSyndromes(projectId) as Record<string, unknown>;
    if (raw.detail) {
      // No diagnosis cached — bootstrap from Omo-Ghibe highland zone real data
      return bootstrapSyndrome("highland") as unknown as Record<string, unknown>;
    }
    return raw;
  }

  async function buildAdvisoryData() {
    const syndrome = await getOrBootstrapSyndrome();
    const advisoryProjectId = (syndrome.project_id as string | undefined) ?? projectId;
    const res = await fetch(`${API}/advisory/${advisoryProjectId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ syndrome, degradation_severity: "severe" }),
    });
    if (!res.ok) throw new Error(await res.text());
    const advisory = await res.json();
    const farmerAdv = advisory.farmer_advisory as Record<string, unknown>;
    return {
      zone: String(syndrome.zone_name ?? syndrome.project_id ?? projectId),
      syndrome: String((syndrome.primary_syndrome as Record<string,unknown>)?.name ?? ""),
      priorityAction: String(farmerAdv?.headline ?? ""),
      keyMessages: (farmerAdv?.key_messages as string[]) ?? [],
      recommendedActions: (farmerAdv?.recommended_actions as string[]) ?? [],
      seasonalGuidance: (farmerAdv?.seasonal_guidance as string[]) ?? [],
      warningFlags: (farmerAdv?.warning_flags as string[]) ?? [],
      monitoringTasks: (farmerAdv?.monitoring_tasks as string[]) ?? [],
    };
  }

  async function buildPolicyBriefData() {
    const syndrome = await getOrBootstrapSyndrome();
    const advisoryProjectId = (syndrome.project_id as string | undefined) ?? projectId;
    const res = await fetch(`${API}/advisory/${advisoryProjectId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ syndrome, degradation_severity: "severe" }),
    });
    if (!res.ok) throw new Error(await res.text());
    const advisory = await res.json();
    const brief = advisory.planner_brief as Record<string, unknown>;
    return {
      title: String(brief?.title ?? `Landscape Policy Brief — ${projectId}`),
      zone: String(syndrome.zone_name ?? syndrome.project_id ?? projectId),
      date: new Date().toLocaleDateString("en-GB"),
      executiveSummary: String(brief?.executive_summary ?? ""),
      diagnosisHighlights: (brief?.diagnosis_highlights as string[]) ?? [],
      climateContext: (brief?.climate_context as string[]) ?? [],
      recommendedPackage: (brief?.recommended_package as string[]) ?? [],
      policyHooks: (brief?.policy_hooks as string[]) ?? [],
      investmentAsk: String(brief?.investment_ask ?? ""),
      nextSteps: (brief?.next_steps as string[]) ?? [],
    };
  }

  const handleAdvisoryPdf = async () => {
    setAdvisoryPdfLoading(true);
    try {
      const data = await buildAdvisoryData();
      const blob = await pdf(<AdvisoryCardDocument {...data} locale={locale} />).toBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `lira-ai-advisory-${projectId}-${locale}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { console.error("[advisory-pdf]", e); setError(t("pdfError")); }
    finally { setAdvisoryPdfLoading(false); }
  };

  const handlePolicyPdf = async () => {
    setPolicyPdfLoading(true);
    try {
      const data = await buildPolicyBriefData();
      const blob = await pdf(<PolicyBriefDocument {...data} locale={locale} />).toBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `lira-ai-policy-brief-${projectId}-${locale}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { console.error("[policy-pdf]", e); setError(t("pdfError")); }
    finally { setPolicyPdfLoading(false); }
  };

  async function buildPassportData() {
    const diag = await getDiagnostic(projectId) as Record<string, unknown>;
    const passport = await createPassport(projectId, {
      package_name: "Integrated Highland Restoration Package",
      target_geography: `${projectId} — Priority degraded zones`,
      pathway_components: ["Soil and Stone Bunds", "Native Species Reforestation", "Area Closure", "Compost Application"],
      diagnostic: diag, climate: null, community: null, policy: null,
    }) as Record<string, unknown>;
    const agentResult = await runInvestmentAgent({
      project_id: projectId,
      package_name: "Integrated Landscape Restoration Package",
      target_geography: `${projectId} — Priority degraded zones`,
      pathway_components: ["Soil bunds", "Native reforestation", "Area closure", "Compost"],
      area_ha: 15000, diagnostic: diag,
    }) as Record<string, unknown>;
    return { passport, agentResult };
  }

  const handlePassportPdf = async () => {
    setPassportPdfLoading(true);
    try {
      const { passport, agentResult } = await buildPassportData();
      const blob = await pdf(
        <InvestmentPassportDocument passport={passport} agentResult={agentResult} locale={locale} date={new Date().toLocaleDateString("en-GB")} />
      ).toBlob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `lira-ai-investment-passport-${projectId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) { console.error("[passport-pdf]", e); setError(t("pdfError")); }
    finally { setPassportPdfLoading(false); }
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-100 mb-1">Export & Report</h1>
      <p className="text-lira-muted text-sm mb-8">Generate reports from all available analysis — {projectId}</p>

      {error && <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-4 mb-6 text-red-400 text-sm">{error}</div>}

      <div className="grid grid-cols-2 gap-5 mb-8">
        <Card title="Markdown Report" className="flex flex-col">
          <p className="text-sm text-lira-muted mb-4">
            Generates a structured policy-ready report including diagnosis, syndromes,
            climate futures, pathways, and investment passports.
          </p>
          <div className="flex gap-3 mt-auto">
            <button
              onClick={handleMarkdown}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-lira-surface border border-lira-border text-slate-200 rounded-lg text-sm hover:border-lira-green/40 disabled:opacity-50"
            >
              <FileText size={14} />
              Preview
            </button>
            {mdContent && (
              <button
                onClick={handleMdDownload}
                className="flex items-center gap-2 px-4 py-2 bg-lira-green text-white rounded-lg text-sm hover:bg-lira-green/80"
              >
                <Download size={14} />
                Download .md
              </button>
            )}
          </div>
        </Card>

        <Card title="JSON Export">
          <p className="text-sm text-lira-muted mb-4">
            Full structured JSON export of all LIRA-AI outputs — diagnosis, syndromes,
            pathways, and investment passports.
          </p>
          <button
            onClick={handleJsonDownload}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-lira-sky/20 border border-lira-sky/40 text-lira-sky rounded-lg text-sm hover:bg-lira-sky/30 disabled:opacity-50"
          >
            <FileJson size={14} />
            Download JSON
          </button>
        </Card>
      </div>

      <div className="mt-8">
        <h2 className="text-lg font-semibold text-slate-100 mb-4">{t("pdfSectionHeading")}</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <Card title={t("advisoryCardTitle")}>
            <p className="text-sm text-lira-muted mb-4">{t("advisoryCardDescription")}</p>
            <DownloadButton label={t("downloadAdvisoryCard")} onClick={handleAdvisoryPdf} isLoading={advisoryPdfLoading} />
          </Card>
          <Card title={t("policyBriefTitle")}>
            <p className="text-sm text-lira-muted mb-4">{t("policyBriefDescription")}</p>
            <DownloadButton label={t("downloadPolicyBrief")} onClick={handlePolicyPdf} isLoading={policyPdfLoading} />
          </Card>
          <Card title={t("investmentPassportTitle")}>
            <p className="text-sm text-lira-muted mb-4">{t("investmentPassportDescription")}</p>
            <DownloadButton label={t("downloadInvestmentPassport")} onClick={handlePassportPdf} isLoading={passportPdfLoading} />
          </Card>
        </div>
      </div>

      {mdContent && (
        <Card title="Report Preview">
          <pre className="text-xs text-slate-300 whitespace-pre-wrap font-mono max-h-[60vh] overflow-y-auto leading-relaxed">
            {mdContent}
          </pre>
        </Card>
      )}
    </div>
  );
}

export default function ExportPage() {
  return <Suspense fallback={<div className="p-8 text-lira-muted">Loading...</div>}><ExportContent /></Suspense>;
}
