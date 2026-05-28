"use client";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { runCommunityAgent, runPolicyAgent, saveCommunityIntelligence } from "@/lib/api";
import { Card, SeverityBadge } from "@/components/ui/Card";
import AIInsight from "@/components/ui/AIInsight";
import { clsx } from "clsx";
import { Users, ShieldCheck, AlertTriangle, CheckCircle, Clock } from "lucide-react";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { useMutationQueue } from "@/hooks/useMutationQueue";

function CommunityContent() {
  const params    = useSearchParams();
  const projectId = params.get("project") ?? "MOCK-ETH-001";

  const { isOnline } = useOnlineStatus();
  const { enqueue }  = useMutationQueue();

  const [saved,      setSaved]      = useState(false);
  const [loading,    setLoading]    = useState(false);
  const [commResult, setCommResult] = useState<Record<string, unknown> | null>(null);
  const [polResult,  setPolResult]  = useState<Record<string, unknown> | null>(null);
  const [error,      setError]      = useState("");
  const [status,     setStatus]     = useState<"idle" | "queued">("idle");

  const [form, setForm] = useState({
    community_preferred_future: "",
    local_degradation_memory:   "",
    grazing_rules:              "",
    labor_constraints:          "",
    gendered_burdens:           "",
    youth_opportunities:        "",
    local_conflict_risks:       "",
    tenure_constraints:         "",
    restoration_preferences:    "",
    adoption_barriers:          "",
    local_success_indicators:   "",
    notes:                      "",
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true); setError(""); setStatus("idle");

    const communityData = {
      project_id: projectId,
      ...form,
      restoration_preferences: form.restoration_preferences.split(",").map(s => s.trim()).filter(Boolean),
      adoption_barriers:        form.adoption_barriers.split(",").map(s => s.trim()).filter(Boolean),
      local_success_indicators: form.local_success_indicators.split(",").map(s => s.trim()).filter(Boolean),
    };

    if (!isOnline) {
      await enqueue("/agents/community-intelligence", "POST", communityData);
      setStatus("queued");
      setLoading(false);
      return;
    }

    try {
      // Save raw data
      await saveCommunityIntelligence(projectId, communityData);

      // Run Community Intelligence Agent
      const cRes = await runCommunityAgent({ project_id: projectId, community: communityData }) as Record<string, unknown>;
      setCommResult(cRes);

      // Run Policy Alignment Agent
      const pRes = await runPolicyAgent({ project_id: projectId }) as Record<string, unknown>;
      setPolResult(pRes);

      setSaved(true);
    } catch (err) { setError(String(err)); }
    finally { setLoading(false); }
  };

  const equity = commResult?.equity as Record<string, unknown> | undefined;
  const scores = polResult?.scores_detail as Record<string, unknown>[] | undefined;

  const RISK_COLOR = (level: string) => ({
    low: "text-lira-green", medium: "text-yellow-400",
    high: "text-orange-400", very_high: "text-red-400", critical: "text-red-500",
  })[level] ?? "text-lira-muted";

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-100 mb-1">Community & Policy Intelligence</h1>
      <p className="text-lira-muted text-sm mb-6">
        Community knowledge as a core decision layer — equity, tenure, conflict, and policy alignment
      </p>

      {error && <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-4 mb-6 text-red-400 text-sm">{error}</div>}

      {status === "queued" && (
        <div className="flex items-center gap-2 bg-amber-900/10 border border-amber-900/30 rounded-xl p-4 mb-6 text-amber-400 text-sm">
          <Clock size={14} className="shrink-0" />
          <span>Queued — will sync when you reconnect.</span>
        </div>
      )}

      {saved && commResult && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-8">
          {/* Community Intelligence Results */}
          <div className="space-y-4">
            <Card title="Community Intelligence" badge="Agent result" badgeColor="bg-lira-green/20 text-lira-green">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
                {[
                  { label: "Community Priority", value: `${Math.round((commResult.community_priority_score as number) * 100)}%` },
                  { label: "Labor Constraint",   value: commResult.labor_constraint_level },
                  { label: "Tenure Risk",        value: commResult.tenure_risk_level },
                  { label: "Conflict Risk",      value: commResult.conflict_risk_level },
                ].map(({ label, value }) => (
                  <div key={label} className="bg-lira-bg rounded-lg p-3">
                    <div className="text-[10px] text-lira-muted">{label}</div>
                    <div className={clsx("text-sm font-semibold mt-0.5",
                      RISK_COLOR(String(value)))}>{String(value)}</div>
                  </div>
                ))}
              </div>

              {/* Equity scores */}
              {equity && (
                <div className="border-t border-lira-border/40 pt-3 mb-3">
                  <div className="text-[10px] font-medium text-lira-muted uppercase mb-2">Equity & Inclusion</div>
                  <div className="space-y-1.5">
                    {[
                      ["Gender inclusion",    equity.gender_inclusion_score],
                      ["Youth opportunity",   equity.youth_opportunity_score],
                      ["Tenure security",     equity.tenure_security_score],
                      ["Adoption feasibility",equity.adoption_feasibility_score],
                    ].map(([label, score]) => (
                      <div key={String(label)} className="flex items-center gap-2">
                        <span className="text-[11px] text-lira-muted w-36">{String(label)}</span>
                        <div className="flex-1 bg-lira-border rounded-full h-1.5">
                          <div className="h-1.5 rounded-full bg-lira-green"
                            style={{ width: `${Math.round((score as number)*100)}%` }} />
                        </div>
                        <span className="text-[10px] text-slate-300 w-8 text-right">
                          {Math.round((score as number)*100)}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Equity flags */}
              {(equity?.equity_flags as string[] ?? []).length > 0 && (
                <div>
                  <div className="text-[10px] font-medium text-red-400 uppercase mb-1.5">Equity Flags</div>
                  {(equity!.equity_flags as string[]).map((f: string) => (
                    <div key={f} className="text-[11px] text-orange-300 border-l-2 border-red-500/40 pl-2 py-0.5 mb-1">{f}</div>
                  ))}
                </div>
              )}

              {/* Advisories */}
              <div className="border-t border-lira-border/40 pt-3 mt-3 space-y-2">
                <div className="text-[11px] text-slate-300 leading-relaxed">
                  <span className="text-lira-muted text-[10px] uppercase font-medium">Gender advisory: </span>
                  {String(commResult.gender_advisory ?? "")}
                </div>
                <div className="text-[11px] text-slate-300 leading-relaxed">
                  <span className="text-lira-muted text-[10px] uppercase font-medium">Youth advisory: </span>
                  {String(commResult.youth_advisory ?? "")}
                </div>
              </div>

              <AIInsight
                narrativeType="advisory"
                label="Summary"
                compact
                context={{
                  audience: "community facilitators",
                  zone_name: projectId,
                  syndrome_name: "landscape degradation",
                  degradation_severity: "moderate",
                  priorities: commResult.preferred_interventions ?? [],
                  constraints: commResult.adoption_barriers ?? [],
                }}
                className="mt-3"
              />
            </Card>

            {/* Negotiation requirements */}
            {(commResult.negotiation_requirements as string[] ?? []).length > 0 && (
              <Card title="Negotiation Requirements">
                {(commResult.negotiation_requirements as string[]).map((r: string) => (
                  <div key={r} className="text-xs text-slate-300 flex gap-2 py-1.5 border-b border-lira-border/30 last:border-0">
                    <CheckCircle size={11} className="text-lira-sky shrink-0 mt-0.5" />{r}
                  </div>
                ))}
              </Card>
            )}
          </div>

          {/* Policy Alignment Results */}
          {polResult && (
            <div className="space-y-4">
              <Card title="Policy Alignment" badge={`Score: ${polResult.overall_policy_score}`} badgeColor="bg-lira-sky/20 text-lira-sky">
                <div className="space-y-1.5 mb-4">
                  {(scores ?? []).map((s) => (
                    <div key={String(s.framework)} className="flex items-center gap-2">
                      <span className="text-[10px] text-lira-muted w-40 truncate">{String(s.framework)}</span>
                      <div className="flex-1 bg-lira-border rounded-full h-1.5">
                        <div className="h-1.5 rounded-full"
                          style={{
                            width: `${Math.round((s.score as number)*100)}%`,
                            background: (s.score as number) > 0.7 ? "#2d6a4f" : (s.score as number) > 0.5 ? "#e9c46a" : "#e07a2f",
                          }} />
                      </div>
                      <span className="text-[10px] text-slate-300 w-8 text-right">{Math.round((s.score as number)*100)}%</span>
                    </div>
                  ))}
                </div>

                {/* Policy gap alerts */}
                {(polResult.policy_gap_alerts as string[] ?? []).length > 0 && (
                  <div className="border-t border-lira-border/40 pt-3 mb-3">
                    <div className="text-[10px] font-medium text-yellow-400 uppercase mb-1.5">Policy Gap Alerts</div>
                    {(polResult.policy_gap_alerts as string[]).map((a: string) => (
                      <div key={a} className="text-[11px] text-yellow-300 border-l-2 border-yellow-500/40 pl-2 py-0.5 mb-1">{a}</div>
                    ))}
                  </div>
                )}

                <AIInsight
                  narrativeType="advisory"
                  label="Summary"
                  compact
                  context={{
                    audience: "policy planners",
                    zone_name: projectId,
                    syndrome_name: "landscape degradation",
                    degradation_severity: "moderate",
                    priorities: polResult.aligned_policies ?? [],
                    constraints: polResult.misalignment_risks ?? [],
                  }}
                  className="mt-2"
                />
              </Card>

              {/* Investment justification */}
              <Card title="Investment Justification">
                <p className="text-xs text-slate-300 leading-relaxed">{String(polResult.investment_justification ?? "")}</p>
              </Card>

              {/* Institutional responsibility */}
              <Card title="Institutional Responsibility">
                {(polResult.institutional_responsibility as string[] ?? []).map((r: string) => (
                  <div key={r} className="text-[11px] text-slate-300 flex gap-2 py-1 border-b border-lira-border/30 last:border-0">
                    <ShieldCheck size={10} className="text-lira-sky shrink-0 mt-0.5" />{r}
                  </div>
                ))}
              </Card>
            </div>
          )}
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-5">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {[
            { key: "community_preferred_future", label: "Community Preferred Future *", multi: true },
            { key: "local_degradation_memory",   label: "Local Degradation Memory",    multi: true },
            { key: "grazing_rules",              label: "Existing Grazing Rules",       multi: false },
            { key: "labor_constraints",          label: "Labor Constraints",            multi: false },
            { key: "gendered_burdens",           label: "Gendered Burdens",             multi: false },
            { key: "youth_opportunities",        label: "Youth Opportunities",          multi: false },
            { key: "local_conflict_risks",       label: "Local Conflict Risks",         multi: false },
            { key: "tenure_constraints",         label: "Land Tenure Constraints",      multi: false },
            { key: "restoration_preferences",    label: "Restoration Preferences (comma-separated)", multi: false },
            { key: "adoption_barriers",          label: "Adoption Barriers (comma-separated)",       multi: false },
            { key: "local_success_indicators",   label: "Success Indicators (comma-separated)",      multi: false },
            { key: "notes",                      label: "Additional Notes",             multi: true },
          ].map(({ key, label, multi }) => (
            <div key={key} className="flex flex-col">
              <label className="block text-[10px] font-medium text-lira-muted mb-1.5 uppercase tracking-wide">{label}</label>
              {multi ? (
                <textarea rows={2} value={form[key as keyof typeof form]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  className="w-full bg-lira-surface border border-lira-border rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-lira-muted focus:outline-none focus:border-lira-green/60 resize-none" />
              ) : (
                <input type="text" value={form[key as keyof typeof form]}
                  onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                  className="w-full bg-lira-surface border border-lira-border rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-lira-muted focus:outline-none focus:border-lira-green/60" />
              )}
            </div>
          ))}
        </div>

        <button type="submit" disabled={loading}
          className="w-full bg-lira-green text-white py-3 rounded-lg font-medium text-sm hover:bg-lira-green/80 transition disabled:opacity-50">
          {loading ? "Running Community Intelligence + Policy Alignment Agents…" : "Save & Run Agents"}
        </button>
      </form>
    </div>
  );
}

export default function CommunityPage() {
  return <Suspense fallback={<div className="p-8 text-lira-muted">Loading…</div>}><CommunityContent /></Suspense>;
}
