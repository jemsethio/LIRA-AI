"use client";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import { getSyndromes, generatePathways, runTradeoffs } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { clsx } from "clsx";
import AIInsight from "@/components/ui/AIInsight";

const TradeoffsChart = dynamic(() => import("./TradeoffsChart"), {
  ssr: false,
  loading: () => <div className="h-[300px] bg-lira-border/10 animate-pulse rounded-xl" />,
});

const LEVEL_COLOR: Record<string, string> = {
  low_risk:                  "text-lira-green",
  medium_risk:               "text-yellow-400",
  high_risk:                 "text-orange-400",
  mitigation_needed:         "text-red-400",
  field_validation_required: "text-red-500",
};

function TradeoffsContent() {
  const params = useSearchParams();
  const projectId = params.get("project") ?? "MOCK-ETH-001";
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(0);

  const run = async () => {
    setLoading(true);
    setError("");
    try {
      const syn = await getSyndromes(projectId) as Record<string, unknown>;
      await generatePathways(projectId, syn);
      const tr = await runTradeoffs(projectId) as Record<string, unknown>;
      setReport(tr);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const radars = (report?.radars as Record<string, unknown>[] ?? []);
  const current = radars[selected];

  const radarData = current
    ? Object.entries(current.scores as Record<string, number>).map(([k, v]) => ({
        dimension: k.replace(/_/g, " "),
        score: Math.round(v * 100),
      }))
    : [];

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:justify-between items-start gap-4 mb-6 lg:mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Tradeoff & Maladaptation Radar</h1>
          <p className="text-lira-muted text-sm mt-1">Risk profile across 13 dimensions for each pathway</p>
        </div>
        <button onClick={run} disabled={loading}
          className="px-4 py-2 bg-lira-warning text-white rounded-lg text-sm font-medium hover:bg-lira-warning/80 disabled:opacity-50">
          {loading ? "Analysing..." : "Run Tradeoff Analysis"}
        </button>
      </div>

      {error && <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-4 mb-6 text-red-400 text-sm">{error}</div>}

      {report && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            <div className="bg-lira-surface border border-lira-border rounded-xl p-4">
              <div className="text-xs text-lira-muted mb-1">Lowest Risk Pathway</div>
              <div className="text-sm font-semibold text-lira-green">
                {String(report.lowest_risk_pathway).replace(/_/g, " ")}
              </div>
            </div>
            <div className="bg-lira-surface border border-lira-border rounded-xl p-4">
              <div className="text-xs text-lira-muted mb-1">Highest Risk Pathway</div>
              <div className="text-sm font-semibold text-red-400">
                {String(report.highest_risk_pathway).replace(/_/g, " ")}
              </div>
            </div>
            <div className="bg-lira-surface border border-lira-border rounded-xl p-4">
              <div className="text-xs text-lira-muted mb-1">Cross-Cutting Risks</div>
              <div className="text-sm font-semibold text-yellow-400">
                {(report.cross_cutting_risks as string[] ?? []).join(", ").replace(/_/g, " ") || "None identified"}
              </div>
            </div>
          </div>

          {/* Pathway selector */}
          <div className="flex gap-2 flex-wrap mb-6">
            {radars.map((r, i) => (
              <button
                key={String(r.pathway_type)}
                onClick={() => setSelected(i)}
                className={clsx(
                  "px-3 py-1.5 rounded-lg text-xs font-medium border transition-all",
                  selected === i
                    ? "bg-lira-warning text-white border-lira-warning"
                    : "border-lira-border text-lira-muted hover:border-lira-warning/40"
                )}
              >
                {String(r.pathway_type).replace(/_/g, " ")}
                <span className={clsx("ml-1.5", RISK_LABEL_COLOR(r.overall_risk as number))}>
                  {Math.round((r.overall_risk as number) * 100)}
                </span>
              </button>
            ))}
          </div>

          {current && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Radar chart — lazy loaded */}
              <Card title={`${String(current.pathway_type).replace(/_/g, " ")} — Risk Radar`}>
                <TradeoffsChart data={radarData} />
                <p className="text-xs text-lira-muted text-center">0 = low risk · 100 = high risk</p>
              </Card>

              {/* Risk breakdown */}
              <Card title="Risk Dimension Breakdown">
                <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                  {Object.entries(current.risk_levels as Record<string, string>).map(([dim, level]) => (
                    <div key={dim} className="flex justify-between items-center py-1.5 border-b border-lira-border/40 last:border-0">
                      <span className="text-xs text-lira-muted">{dim.replace(/_/g, " ")}</span>
                      <span className={clsx("text-xs font-medium", LEVEL_COLOR[level] ?? "text-slate-300")}>
                        {level.replace(/_/g, " ")}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="mt-3">
                  <p className="text-xs text-lira-muted mb-3">{String(current.summary)}</p>
                  <AIInsight
                    narrativeType="tradeoffs"
                    label="Summary"
                    compact
                    context={{
                      zone_name:            projectId,
                      lowest_risk:          report.lowest_risk_pathway,
                      highest_risk:         report.highest_risk_pathway,
                      cross_cutting_risks:  report.cross_cutting_risks ?? [],
                      recommended:          report.lowest_risk_pathway,
                    }}
                  />
                </div>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function RISK_LABEL_COLOR(score: number) {
  return score > 0.6 ? "text-red-400" : score > 0.4 ? "text-yellow-400" : "text-lira-green";
}

export default function TradeoffsPage() {
  return <Suspense fallback={<div className="p-8 text-lira-muted">Loading...</div>}><TradeoffsContent /></Suspense>;
}
