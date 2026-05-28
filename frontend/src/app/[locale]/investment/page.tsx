"use client";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getDiagnostic, createPassport, listPassports, runInvestmentAgent } from "@/lib/api";
import { Card, MetricRow, AssumptionNote } from "@/components/ui/Card";
import AIInsight from "@/components/ui/AIInsight";
import { clsx } from "clsx";

function InvestmentContent() {
  const params = useSearchParams();
  const projectId = params.get("project") ?? "MOCK-ETH-001";
  const [passports, setPassports] = useState<Record<string, unknown>[]>([]);
  const [agentResult, setAgentResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const generate = async () => {
    setLoading(true);
    setError("");
    try {
      const diag = await getDiagnostic(projectId) as Record<string, unknown>;
      const passport = await createPassport(projectId, {
        package_name: "Integrated Highland Restoration Package",
        target_geography: `${projectId} — Priority degraded zones`,
        pathway_components: [
          "Soil and Stone Bunds",
          "Native Species Reforestation",
          "Area Closure",
          "Compost Application",
        ],
        diagnostic: diag,
        climate: null,
        community: null,
        policy: null,
      }) as Record<string, unknown>;
      setPassports([passport]);

      // Also run Investment Planning Agent for full analysis
      try {
        const agentRes = await runInvestmentAgent({
          project_id:         projectId,
          package_name:       "Integrated Landscape Restoration Package",
          target_geography:   `${projectId} — Priority degraded zones`,
          pathway_components: ["Soil bunds","Native reforestation","Area closure","Compost"],
          area_ha:            15000,
          diagnostic:         diag,
        }) as Record<string, unknown>;
        setAgentResult(agentRes);
      } catch { /* agent result is bonus — don't fail on error */ }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  };

  const scoreColor = (v: number) =>
    v > 0.7 ? "text-lira-green" : v > 0.4 ? "text-yellow-400" : "text-red-400";

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:justify-between items-start gap-4 mb-6 lg:mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Investment Passports</h1>
          <p className="text-lira-muted text-sm mt-1">Investment-ready restoration packages — {projectId}</p>
        </div>
        <button
          onClick={generate}
          disabled={loading}
          className="px-4 py-2 bg-lira-sand text-lira-bg rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50"
        >
          {loading ? "Generating..." : "Generate Investment Passport"}
        </button>
      </div>

      {error && <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-4 mb-6 text-red-400 text-sm">{error}</div>}

      {passports.map((p) => (
        <div key={String(p.passport_id)} className="space-y-5">
          {/* Header */}
          <div className="bg-lira-surface border border-lira-sand/30 rounded-xl p-6">
            <div className="flex justify-between items-start mb-3">
              <div>
                <div className="text-xs text-lira-muted mb-1 uppercase tracking-wide">Investment Passport</div>
                <h2 className="text-xl font-bold text-slate-100">{String(p.package_name)}</h2>
                <p className="text-sm text-lira-muted mt-1">{String(p.target_geography)}</p>
              </div>
              <div className="text-right">
                <div className="text-xs text-lira-muted">Passport ID</div>
                <div className="text-xs font-mono text-lira-muted">{String(p.passport_id).slice(0, 12)}…</div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="bg-lira-bg rounded-lg p-3">
                <div className="text-xs text-lira-muted mb-1">Investment Readiness</div>
                <div className={`text-2xl font-bold ${scoreColor(p.investment_readiness_score as number)}`}>
                  {Math.round((p.investment_readiness_score as number) * 100)}%
                </div>
              </div>
              <div className="bg-lira-bg rounded-lg p-3">
                <div className="text-xs text-lira-muted mb-1">Climate Robustness</div>
                <div className={`text-2xl font-bold ${scoreColor(p.climate_robustness_score as number)}`}>
                  {Math.round((p.climate_robustness_score as number) * 100)}%
                </div>
              </div>
              <div className="bg-lira-bg rounded-lg p-3">
                <div className="text-xs text-lira-muted mb-1">Confidence</div>
                <div className={`text-2xl font-bold ${scoreColor(p.confidence_score as number)}`}>
                  {Math.round((p.confidence_score as number) * 100)}%
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Diagnosis */}
            <Card title="Problem Diagnosis">
              <p className="text-sm text-slate-300 leading-relaxed">{String(p.problem_diagnosis)}</p>
            </Card>

            {/* Climate rationale */}
            <Card title="Climate Rationale">
              <p className="text-sm text-slate-300 leading-relaxed">{String(p.future_climate_rationale)}</p>
            </Card>

            {/* Intervention components */}
            <Card title="Intervention Components">
              <ul className="space-y-1.5">
                {(p.intervention_components as string[]).map((c) => (
                  <li key={c} className="text-sm text-slate-300 flex gap-2">
                    <span className="text-lira-green">▸</span>{c}
                  </li>
                ))}
              </ul>
            </Card>

            {/* Partners */}
            <Card title="Implementation Partners">
              <ul className="space-y-1.5">
                {(p.implementation_partners as string[]).map((c) => (
                  <li key={c} className="text-sm text-slate-300 flex gap-2">
                    <span className="text-lira-sky">▸</span>{c}
                  </li>
                ))}
              </ul>
              <div className="mt-3 text-xs text-lira-muted border-t border-lira-border pt-3">
                Community acceptance: {String(p.community_acceptance_status)}
              </div>
            </Card>

            {/* Ecosystem + livelihood benefits */}
            <Card title="Ecosystem Benefits">
              <ul className="space-y-1">
                {(p.expected_ecosystem_benefits as string[]).map((b) => (
                  <li key={b} className="text-xs text-slate-300 flex gap-2"><span className="text-lira-green">✓</span>{b}</li>
                ))}
              </ul>
            </Card>
            <Card title="Livelihood Benefits">
              <ul className="space-y-1">
                {(p.expected_livelihood_benefits as string[]).map((b) => (
                  <li key={b} className="text-xs text-slate-300 flex gap-2"><span className="text-yellow-400">✓</span>{b}</li>
                ))}
              </ul>
            </Card>
          </div>

          {/* AI Investment Narrative */}
          <AIInsight
            narrativeType="investment"
            label="Summary"
            context={{
              package_name:       p.package_name,
              target_geography:   p.target_geography,
              problem_diagnosis:  p.problem_diagnosis,
              interventions:      p.intervention_components ?? [],
              readiness_score:    `${Math.round((p.investment_readiness_score as number)*100)}%`,
              climate_score:      `${Math.round((p.climate_robustness_score as number)*100)}%`,
              policy_hooks:       p.policy_alignment ?? [],
            }}
            className="mb-5"
          />

          {/* Maladaptation alerts */}
          {(p.maladaptation_alerts as string[]).length > 0 && (
            <Card title="Maladaptation Alerts" badge="Review Required" badgeColor="bg-red-900/30 text-red-400">
              {(p.maladaptation_alerts as string[]).map((a) => (
                <div key={a} className="text-sm text-orange-300 border-l-2 border-lira-warning pl-3 py-1 mb-1">{a}</div>
              ))}
            </Card>
          )}

          {/* Assumptions */}
          <Card title="Assumptions & Evidence Trail">
            <div className="space-y-1 mb-4">
              {(p.assumptions as string[]).map((a) => (
                <AssumptionNote key={String(a)} text={String(a)} />
              ))}
            </div>
            <div className="border-t border-lira-border pt-3 space-y-1">
              {(p.evidence_trail as string[]).map((e) => (
                <div key={e} className="text-xs text-lira-muted">{e}</div>
              ))}
            </div>
          </Card>
        </div>
      ))}

      {/* Investment Planning Agent results */}
      {agentResult && (
        <div className="space-y-5 mt-6">
          <h2 className="text-base font-semibold text-slate-100">Investment Planning Agent</h2>

          {/* Finance windows */}
          <Card title="Finance Window Screening" badge="GCF · LDCF · AF · CGIAR" badgeColor="bg-lira-sky/20 text-lira-sky">
            <div className="grid gap-2">
              {(agentResult.finance_windows as Record<string,unknown>[] ?? []).map((w) => (
                <div key={String(w.name)} className={clsx(
                  "flex items-start justify-between gap-3 p-3 rounded-lg border",
                  w.eligibility === "likely"   ? "border-lira-green/30 bg-lira-green/5" :
                  w.eligibility === "possible" ? "border-yellow-600/30 bg-yellow-900/5" :
                  "border-lira-border/40 opacity-60"
                )}>
                  <div>
                    <div className="text-xs font-medium text-slate-200">{String(w.name)}</div>
                    <div className="text-[10px] text-lira-muted mt-0.5">{String(w.eligibility_note)}</div>
                  </div>
                  <span className={clsx("text-[10px] px-2 py-0.5 rounded-full font-medium shrink-0",
                    w.eligibility === "likely"   ? "bg-lira-green/20 text-lira-green" :
                    w.eligibility === "possible" ? "bg-yellow-900/30 text-yellow-400" :
                    "bg-lira-border/30 text-lira-muted")}>
                    {String(w.eligibility)}
                  </span>
                </div>
              ))}
            </div>
            <div className="mt-3 text-xs text-lira-sky border-t border-lira-border pt-3">
              Recommended: {String(agentResult.recommended_window ?? "")}
            </div>
          </Card>

          {/* Cost + scalability */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            <Card title="Cost Estimate">
              <div className="text-2xl font-bold text-lira-green mb-1">{String(agentResult.cost_estimate_usd_ha)}</div>
              <div className="text-xs text-lira-muted mb-2">per hectare</div>
              <div className="text-xs text-slate-300">{String(agentResult.total_cost_estimate)}</div>
            </Card>
            <Card title="Scalability">
              <div className="text-2xl font-bold text-lira-sky mb-1">
                {Math.round((agentResult.scalability_score as number ?? 0)*100)}%
              </div>
              <div className="text-xs text-lira-muted mb-2">scalability score</div>
              <div className="text-xs text-slate-300 leading-relaxed">{String(agentResult.scalability_notes ?? "")}</div>
            </Card>
          </div>

          {/* MRV */}
          {Boolean(agentResult.mrv_framework) && (
            <Card title="MRV Framework" badge="Monitoring · Reporting · Verification" badgeColor="bg-purple-900/30 text-purple-400">
              <div className="text-xs text-lira-muted mb-2">{String((agentResult.mrv_framework as Record<string,unknown>).reporting_frequency)}</div>
              <div className="grid gap-1">
                {((agentResult.mrv_framework as Record<string,unknown>).monitoring_indicators as string[] ?? []).map((ind: string) => (
                  <div key={ind} className="text-[11px] text-slate-300 flex gap-2">
                    <span className="text-lira-green shrink-0">▸</span>{ind}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

export default function InvestmentPage() {
  return <Suspense fallback={<div className="p-8 text-lira-muted">Loading...</div>}><InvestmentContent /></Suspense>;
}
