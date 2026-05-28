"use client";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import { runClimateFutures } from "@/lib/api";
import { Card, MetricRow, SeverityBadge } from "@/components/ui/Card";
import AIInsight from "@/components/ui/AIInsight";
import SAMPLE from "../diagnosis/sample_indicators.json";

const RISK_COLOR = (score: number) =>
  score > 0.7 ? "#c1121f" : score > 0.5 ? "#e07a2f" : score > 0.3 ? "#e9c46a" : "#2d6a4f";

const ClimateChart = dynamic(() => import("./ClimateChart"), {
  ssr: false,
  loading: () => <div className="h-[240px] bg-lira-border/10 animate-pulse rounded-xl" />,
});

function ClimateContent() {
  const params = useSearchParams();
  const projectId = params.get("project") ?? "MOCK-ETH-001";
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    setLoading(true);
    setError("");
    try {
      const indicators = { ...SAMPLE.indicators, project_id: projectId };
      const r = await runClimateFutures(projectId, indicators) as Record<string, unknown>;
      setReport(r);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const riskFields = report ? [
    "rainfall_intensity_risk", "drought_dry_spell_risk", "heat_stress_risk",
    "soil_moisture_stress", "erosion_runoff_risk", "vegetation_stress",
    "restoration_suitability_stress",
  ] : [];

  const barData = riskFields.map((k) => {
    const v = report?.[k] as Record<string, unknown>;
    return {
      name: v?.name as string ?? k,
      score: Math.round((v?.risk_score as number) * 100),
    };
  });

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:justify-between items-start gap-4 mb-6 lg:mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Climate Futures</h1>
          <p className="text-lira-muted text-sm mt-1">Projected climate risk indicators — {projectId}</p>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="px-4 py-2 bg-lira-sky text-white rounded-lg text-sm font-medium hover:bg-lira-sky/80 disabled:opacity-50"
        >
          {loading ? "Analysing..." : "Run Climate Futures"}
        </button>
      </div>

      {!report && !loading && (
        <div className="bg-lira-surface border border-lira-border rounded-xl p-8 text-center text-lira-muted">
          <p className="mb-2 text-base">Climate Futures not yet run</p>
          <p className="text-sm">Click the button to run placeholder scenario analysis</p>
          <div className="mt-4 text-xs bg-yellow-900/20 border border-yellow-900/30 rounded-lg px-4 py-2 text-yellow-400 inline-block">
            MVP Tier 1: Uses placeholder climate scenarios. CMIP6/CORDEX integration in Tier 2.
          </div>
        </div>
      )}

      {error && <div className="text-red-400 text-sm bg-red-900/20 border border-red-900/40 rounded-xl p-4 mb-6">{error}</div>}

      {report && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <div className="bg-lira-surface border border-lira-border rounded-xl p-4">
              <div className="text-xs text-lira-muted mb-1">Overall Climate Risk</div>
              <div className="text-2xl font-bold" style={{ color: RISK_COLOR(report.overall_climate_risk_score as number) }}>
                {Math.round((report.overall_climate_risk_score as number) * 100)}/100
              </div>
            </div>
            <div className="bg-lira-surface border border-lira-border rounded-xl p-4">
              <div className="text-xs text-lira-muted mb-1">Scenario</div>
              <div className="text-sm font-semibold text-slate-200">{String(report.scenario)}</div>
            </div>
            <div className="bg-lira-surface border border-lira-border rounded-xl p-4">
              <div className="text-xs text-lira-muted mb-1">Restoration Window Narrowing</div>
              <div className={`text-sm font-semibold ${report.restoration_window_narrowing ? "text-red-400" : "text-lira-green"}`}>
                {report.restoration_window_narrowing ? "YES — plan early" : "No — stable window"}
              </div>
            </div>
          </div>

          <Card title="Risk Profile by Indicator" className="mb-6">
            <ClimateChart data={barData} />
          </Card>

          <Card title="Maladaptation Climate Alerts" badge="Action Required" badgeColor="bg-red-900/30 text-red-400" className="mb-6">
            {(report.maladaptation_climate_alerts as string[]).length === 0 ? (
              <p className="text-sm text-lira-muted">No specific maladaptation alerts triggered</p>
            ) : (
              <ul className="space-y-2">
                {(report.maladaptation_climate_alerts as string[]).map((alert, i) => (
                  <li key={i} className="text-sm text-orange-300 border-l-2 border-lira-warning pl-3 py-1">
                    {alert}
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card title="Summary Narrative">
            <p className="text-sm text-slate-300 leading-relaxed mb-4">{String(report.summary_narrative)}</p>
            <AIInsight
              narrativeType="climate"
              label="Summary"
              context={{
                zone_name: projectId,
                scenario:  report.scenario,
                horizon:   report.horizon,
                rainfall_mm: (report as Record<string,unknown>).rainfall_mm_annual,
                temp_c:    (report as Record<string,unknown>).temperature_mean_c,
                risk_scores: {
                  rainfall_intensity_risk: (report.rainfall_intensity_risk as Record<string,unknown>)?.risk_score,
                  drought_dry_spell_risk:  (report.drought_dry_spell_risk  as Record<string,unknown>)?.risk_score,
                  heat_stress_risk:        (report.heat_stress_risk        as Record<string,unknown>)?.risk_score,
                  erosion_runoff_risk:     (report.erosion_runoff_risk     as Record<string,unknown>)?.risk_score,
                  restoration_suitability_stress: (report.restoration_suitability_stress as Record<string,unknown>)?.risk_score,
                },
              }}
            />
            <div className="mt-4 text-xs bg-yellow-900/20 border border-yellow-900/30 rounded px-3 py-2 text-yellow-400">
              ASSUMPTION: Risk scores are Tier 1 placeholder values without downscaled GCM output.
            </div>
          </Card>
        </>
      )}
    </div>
  );
}

export default function ClimatePage() {
  return <Suspense fallback={<div className="p-8 text-lira-muted">Loading...</div>}><ClimateContent /></Suspense>;
}
