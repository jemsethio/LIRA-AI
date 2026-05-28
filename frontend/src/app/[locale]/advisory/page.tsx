"use client";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { Card } from "@/components/ui/Card";
import { getSyndromes } from "@/lib/api";
import { clsx } from "clsx";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TABS = ["farmer", "pastoralist", "planner", "investor", "extension"] as const;
type Tab = typeof TABS[number];

function AdvisoryContent() {
  const t = useTranslations("advisory");
  const params = useSearchParams();
  const projectId = params.get("project") ?? "MOCK-ETH-001";
  const [advisory, setAdvisory] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [tab, setTab]           = useState<Tab>("farmer");

  const generate = async () => {
    setLoading(true); setError("");
    try {
      const syndrome = await getSyndromes(projectId);
      const res = await fetch(`${API}/advisory/${projectId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ syndrome, degradation_severity: "severe" }),
      });
      if (!res.ok) throw new Error(await res.text());
      setAdvisory(await res.json());
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  const farmerAdv  = advisory?.farmer_advisory   as Record<string, unknown> | undefined;
  const pastAdv    = advisory?.pastoralist_advisory as Record<string, unknown> | undefined;
  const plannerBrief = advisory?.planner_brief   as Record<string, unknown> | undefined;
  const investorNote = advisory?.investor_note   as Record<string, unknown> | undefined;
  const extension  = advisory?.extension_messages as string[] | undefined;
  const equity     = advisory?.equity_notes       as string[] | undefined;

  const renderAdvisory = (adv: Record<string, unknown> | undefined) => {
    if (!adv) return null;
    return (
      <div className="space-y-4">
        <div className="text-xs text-lira-muted bg-lira-border/20 rounded px-3 py-1.5">
          {String(adv.language_note ?? "")}
        </div>
        <div className="text-lg font-semibold text-slate-100">{String(adv.headline ?? "")}</div>
        <div>
          <div className="text-xs font-medium text-lira-muted uppercase mb-2">Key Messages</div>
          <ul className="space-y-1.5">
            {(adv.key_messages as string[] ?? []).map((m) => (
              <li key={m} className="text-sm text-slate-300 flex gap-2"><span className="text-lira-green mt-0.5">▸</span>{m}</li>
            ))}
          </ul>
        </div>
        <div>
          <div className="text-xs font-medium text-lira-muted uppercase mb-2">Recommended Actions</div>
          <ul className="space-y-1.5">
            {(adv.recommended_actions as string[] ?? []).map((a) => (
              <li key={a} className="text-sm text-slate-300 flex gap-2"><span className="text-yellow-400 mt-0.5">✓</span>{a}</li>
            ))}
          </ul>
        </div>
        <div>
          <div className="text-xs font-medium text-lira-muted uppercase mb-2">Seasonal Guidance</div>
          <ul className="space-y-1">
            {(adv.seasonal_guidance as string[] ?? []).map((g) => (
              <li key={g} className="text-xs text-lira-muted border-l-2 border-lira-border pl-3 py-0.5">{g}</li>
            ))}
          </ul>
        </div>
        {(adv.warning_flags as string[] ?? []).length > 0 && (
          <div>
            <div className="text-xs font-medium text-red-400 uppercase mb-2">Warning Flags</div>
            {(adv.warning_flags as string[]).map((w) => (
              <div key={w} className="text-xs text-orange-300 border-l-2 border-lira-warning pl-3 py-1 mb-1">{w}</div>
            ))}
          </div>
        )}
        <div>
          <div className="text-xs font-medium text-lira-muted uppercase mb-2">Monitoring Tasks</div>
          {(adv.monitoring_tasks as string[] ?? []).map((t) => (
            <div key={t} className="text-xs text-lira-muted pl-3 py-0.5">— {t}</div>
          ))}
        </div>
      </div>
    );
  };

  const renderBrief = (brief: Record<string, unknown> | undefined) => {
    if (!brief) return null;
    return (
      <div className="space-y-4">
        <div className="text-base font-semibold text-slate-100">{String(brief.title ?? "")}</div>
        <p className="text-sm text-slate-300 leading-relaxed italic border-l-2 border-lira-green pl-3">
          {String(brief.executive_summary ?? "")}
        </p>
        {[
          { label: "Diagnosis", items: brief.diagnosis_highlights as string[] },
          { label: "Climate Context", items: brief.climate_context as string[] },
          { label: "Recommended Package", items: brief.recommended_package as string[] },
          { label: "Policy Hooks", items: brief.policy_hooks as string[] },
          { label: "Next Steps", items: brief.next_steps as string[] },
        ].map(({ label, items }) => (
          <div key={label}>
            <div className="text-xs font-medium text-lira-muted uppercase mb-1.5">{label}</div>
            <ul className="space-y-1">
              {(items ?? []).map((i) => (
                <li key={i} className="text-sm text-slate-300 flex gap-2">
                  <span className="text-lira-sky mt-0.5">▸</span>{i}
                </li>
              ))}
            </ul>
          </div>
        ))}
        <div className="border border-lira-sand/30 bg-lira-sand/5 rounded-lg px-4 py-3">
          <div className="text-xs text-lira-muted uppercase mb-1">Investment Ask</div>
          <div className="text-sm text-slate-200">{String(brief.investment_ask ?? "")}</div>
        </div>
      </div>
    );
  };

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-4xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:justify-between items-start gap-4 mb-6 lg:mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">{t("title")}</h1>
          <p className="text-lira-muted text-sm mt-1">
            Role-specific advisories for farmers, pastoralists, planners, and investors
          </p>
        </div>
        <button onClick={generate} disabled={loading}
          className="px-4 py-2 bg-lira-green text-white rounded-lg text-sm font-medium hover:bg-lira-green/80 disabled:opacity-50">
          {loading ? t("loading") : t("generateButton")}
        </button>
      </div>

      {error && <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-4 mb-6 text-red-400 text-sm">{t("error")}</div>}

      {advisory && (
        <>
          {/* Tabs */}
          <div className="flex gap-2 mb-6 flex-wrap">
            {TABS.map((t) => (
              <button key={t} onClick={() => setTab(t)}
                className={clsx("px-3 py-1.5 rounded-lg text-xs font-medium border transition-all", {
                  "bg-lira-green text-white border-lira-green": tab === t,
                  "border-lira-border text-lira-muted hover:border-lira-green/40": tab !== t,
                })}>
                {t.charAt(0).toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>

          <Card title={tab.charAt(0).toUpperCase() + tab.slice(1) + " Advisory"} className="mb-6">
            {tab === "farmer"      && renderAdvisory(farmerAdv)}
            {tab === "pastoralist" && renderAdvisory(pastAdv)}
            {tab === "planner"     && renderBrief(plannerBrief)}
            {tab === "investor"    && renderBrief(investorNote)}
            {tab === "extension"   && (
              <div className="space-y-2">
                <p className="text-xs text-lira-muted mb-3">Short field messages suitable for SMS / extension worker cards</p>
                {(extension ?? []).map((msg, i) => (
                  <div key={i} className="bg-lira-bg border border-lira-border rounded-lg px-4 py-3 text-sm text-slate-200 font-mono">
                    {msg}
                  </div>
                ))}
              </div>
            )}
          </Card>

          {equity && equity.length > 0 && (
            <Card title="Equity & Inclusion Notes" badge="Review Required" badgeColor="bg-purple-900/30 text-purple-400">
              {equity.map((note) => (
                <div key={note} className="text-sm text-slate-300 border-l-2 border-purple-600/40 pl-3 py-1.5 mb-1">{note}</div>
              ))}
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function AdvisoryFallback() {
  const t = useTranslations("advisory");
  return <div className="p-8 text-lira-muted">{t("loading")}</div>;
}

export default function AdvisoryPage() {
  return <Suspense fallback={<AdvisoryFallback />}><AdvisoryContent /></Suspense>;
}
