"use client";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getSyndromes, generatePathways, runTradeoffs } from "@/lib/api";
import { Card, SeverityBadge, AssumptionNote } from "@/components/ui/Card";
import { clsx } from "clsx";
import AIInsight from "@/components/ui/AIInsight";

const PATHWAY_COLORS: Record<string, string> = {
  low_cost:               "border-lira-green/40 bg-lira-green/5",
  climate_robust:         "border-lira-sky/40 bg-lira-sky/5",
  food_feed_security:     "border-yellow-600/40 bg-yellow-900/5",
  water_sediment_reduction:"border-blue-600/40 bg-blue-900/5",
  biodiversity_carbon:    "border-emerald-600/40 bg-emerald-900/5",
  community_preferred:    "border-purple-600/40 bg-purple-900/5",
  investment_ready:       "border-lira-sand/40 bg-lira-sand/5",
};

function PathwaysContent() {
  const params = useSearchParams();
  const projectId = params.get("project") ?? "MOCK-ETH-001";
  const [pathwaySet, setPathwaySet] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const run = async () => {
    setLoading(true);
    setError("");
    try {
      const syn = await getSyndromes(projectId) as Record<string, unknown>;
      const ps = await generatePathways(projectId, syn) as Record<string, unknown>;
      setPathwaySet(ps);
      setSelected(ps.recommended_primary as string);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const pathways = (pathwaySet?.pathways as Record<string, unknown>[] ?? []);
  const selectedPathway = pathways.find((p) => p.pathway_type === selected);

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:justify-between items-start gap-4 mb-6 lg:mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Regeneration Pathways</h1>
          <p className="text-lira-muted text-sm mt-1">Seven alternative pathway packages — {projectId}</p>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="px-4 py-2 bg-lira-green text-white rounded-lg text-sm font-medium hover:bg-lira-green/80 disabled:opacity-50"
        >
          {loading ? "Generating..." : "Generate Pathways"}
        </button>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-4 mb-6 text-red-400 text-sm">
          {error} — Make sure you have run the diagnosis and syndrome classification first.
        </div>
      )}

      {pathwaySet && (
        <>
          <div className="bg-lira-green/10 border border-lira-green/30 rounded-xl p-4 mb-6 text-sm text-slate-300">
            <strong className="text-lira-green">Recommended Primary:</strong>{" "}
            {String(pathwaySet.recommended_primary).replace(/_/g, " ")} — {String(pathwaySet.rationale)}
          </div>

          {/* Pathway selector tabs */}
          <div className="flex gap-2 flex-wrap mb-6">
            {pathways.map((p) => {
              const type = String(p.pathway_type);
              const isRecommended = type === pathwaySet.recommended_primary;
              return (
                <button
                  key={type}
                  onClick={() => setSelected(type)}
                  className={clsx(
                    "px-3 py-1.5 rounded-lg text-xs font-medium border transition-all",
                    selected === type
                      ? "bg-lira-green text-white border-lira-green"
                      : "border-lira-border text-lira-muted hover:border-lira-green/40",
                    isRecommended && selected !== type && "border-lira-green/40 text-lira-green"
                  )}
                >
                  {type.replace(/_/g, " ")}
                  {isRecommended && " ★"}
                </button>
              );
            })}
          </div>

          {/* Selected pathway detail */}
          {selectedPathway && (
            <div className={clsx("border rounded-xl p-6", PATHWAY_COLORS[String(selectedPathway.pathway_type)] ?? "")}>
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-base font-semibold text-slate-100 capitalize">
                    {String(selectedPathway.pathway_type).replace(/_/g, " ")} Pathway
                  </h2>
                  <p className="text-sm text-lira-muted mt-1 italic">{String(selectedPathway.why_it_fits)}</p>
                </div>
                <div className="flex gap-2">
                  <span className="text-xs bg-lira-surface border border-lira-border rounded px-2 py-1">
                    Cost: {String(selectedPathway.cost_category)}
                  </span>
                  <span className="text-xs bg-lira-surface border border-lira-border rounded px-2 py-1">
                    Labor: {String(selectedPathway.labor_burden)}
                  </span>
                  <span className="text-xs bg-lira-surface border border-lira-border rounded px-2 py-1">
                    Confidence: {String(selectedPathway.confidence_level)}
                  </span>
                </div>
              </div>

              {/* Recommended package */}
              <div className="mb-5">
                <h3 className="text-xs font-medium text-lira-muted uppercase mb-3">Intervention Package</h3>
                <div className="grid gap-3">
                  {(selectedPathway.recommended_package as Record<string, unknown>[] ?? []).map((opt) => (
                    <div key={String(opt.option_name)} className="bg-lira-surface border border-lira-border rounded-lg p-4">
                      <div className="font-medium text-sm text-slate-100 mb-1">{String(opt.option_name)}</div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-xs text-lira-muted mt-2">
                        <span>Slope: {String(opt.slope_range)}</span>
                        <span>Rainfall: {String(opt.rainfall_range)}</span>
                        <span>Labor: {String(opt.labor_requirements)}</span>
                        <span>Confidence: {String(opt.confidence_level)}</span>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {(opt.benefits as string[] ?? []).slice(0, 2).map((b) => (
                          <span key={b} className="text-xs bg-lira-green/10 text-lira-green border border-lira-green/20 px-2 py-0.5 rounded">
                            {b}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                  <h3 className="text-xs font-medium text-lira-muted uppercase mb-2">Expected Benefits</h3>
                  <ul className="space-y-1">
                    {(selectedPathway.expected_benefits as string[] ?? []).map((b) => (
                      <li key={b} className="text-xs text-slate-300 flex gap-2">
                        <span className="text-lira-green">✓</span>{b}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="text-xs font-medium text-lira-muted uppercase mb-2">Tradeoffs</h3>
                  <ul className="space-y-1">
                    {(selectedPathway.tradeoffs as string[] ?? []).map((t) => (
                      <li key={t} className="text-xs text-slate-300 flex gap-2">
                        <span className="text-yellow-400">!</span>{t}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {(selectedPathway.maladaptation_risks as string[] ?? []).length > 0 && (
                <div className="mt-4">
                  <h3 className="text-xs font-medium text-red-400 uppercase mb-2">Maladaptation Risks</h3>
                  {(selectedPathway.maladaptation_risks as string[]).map((r) => (
                    <div key={r} className="text-xs text-orange-300 border-l-2 border-lira-warning pl-3 py-1 mb-1">{r}</div>
                  ))}
                </div>
              )}

              {/* AI Pathway Rationale */}
              <AIInsight
                narrativeType="pathway"
                label="Summary"
                compact
                context={{
                  pathway_type:   selectedPathway.pathway_type,
                  syndrome_name:  selectedPathway.diagnosis_summary,
                  interventions:  (selectedPathway.recommended_package as {option_name:string}[])?.map((o) => o.option_name) ?? [],
                  why_it_fits:    selectedPathway.why_it_fits,
                  cost_category:  selectedPathway.cost_category,
                  tradeoffs:      selectedPathway.tradeoffs ?? [],
                }}
                className="mt-4"
              />

              <div className="mt-4 space-y-1">
                {(selectedPathway.assumptions as string[] ?? []).map((a) => (
                  <AssumptionNote key={String(a)} text={String(a)} />
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function PathwaysPage() {
  return <Suspense fallback={<div className="p-8 text-lira-muted">Loading...</div>}><PathwaysContent /></Suspense>;
}
