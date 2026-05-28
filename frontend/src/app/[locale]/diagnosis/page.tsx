"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import { runDiagnosis, classifySyndromes } from "@/lib/api";
import { Card, MetricRow, SeverityBadge, AssumptionNote } from "@/components/ui/Card";
import AIInsight from "@/components/ui/AIInsight";
import SAMPLE from "./sample_indicators.json";
import Link from "next/link";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";

const DIAG_CACHE_KEY = "lira-diagnosis-last";

function formatRelativeTime(ms: number): string {
  const secs = Math.floor(ms / 1000);
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  return `${Math.floor(hrs / 24)} days ago`;
}

const DiagnosisChart = dynamic(() => import("./DiagnosisChart"), {
  ssr: false,
  loading: () => <div className="h-[280px] bg-lira-border/10 animate-pulse rounded-xl" />,
});

function DiagnosisContent() {
  const params = useSearchParams();
  const projectId = params.get("project") ?? "MOCK-ETH-001";

  const { isOnline } = useOnlineStatus();

  const [diagnostic, setDiagnostic] = useState<Record<string, unknown> | null>(null);
  const [syndrome, setSyndrome] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [cacheAge, setCacheAge] = useState<number | null>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError("");
    try {
      const indicators = { ...SAMPLE.indicators, project_id: projectId };
      const diag = await runDiagnosis(indicators) as Record<string, unknown>;
      setDiagnostic(diag);
      const syn = await classifySyndromes(projectId) as Record<string, unknown>;
      setSyndrome(syn);
      setCacheAge(null);

      // Persist to localStorage for offline access (T-09-03-01: values rendered via JSX, auto-escaped)
      try {
        localStorage.setItem(DIAG_CACHE_KEY, JSON.stringify({
          data: diag,
          syndrome: syn,
          projectId,
          cachedAt: Date.now(),
        }));
      } catch {
        // localStorage may be unavailable (private browsing, storage quota) — non-fatal
      }
    } catch (err) {
      setError(String(err));
      // On failure, attempt to load from localStorage cache
      try {
        const raw = localStorage.getItem(DIAG_CACHE_KEY);
        if (raw) {
          const parsed = JSON.parse(raw) as { data: Record<string, unknown>; syndrome: Record<string, unknown>; cachedAt: number };
          if (parsed.data && parsed.syndrome) {
            setDiagnostic(parsed.data);
            setSyndrome(parsed.syndrome);
            setCacheAge(Date.now() - parsed.cachedAt);
          }
        }
      } catch {
        // Corrupt cache — discard silently (T-09-03-01: parse failure handled)
      }
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { runAnalysis(); }, [projectId]);

  const indicators = diagnostic?.indicators as Record<string, Record<string, unknown>> | undefined;

  const radarData = indicators
    ? Object.entries(indicators)
        .filter(([, v]) => !v.data_gap)
        .map(([key, v]) => ({
          subject: key.replace(/_/g, " ").slice(0, 18),
          severity: Math.round((v.severity_score as number) * 100),
        }))
    : [];

  const primary = (syndrome?.primary_syndrome as Record<string, unknown>) ?? {};

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:justify-between items-start gap-4 mb-6 lg:mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Landscape Diagnosis</h1>
          <div className="flex items-center gap-3 mt-1 flex-wrap">
            <p className="text-lira-muted text-sm">Project: {projectId}</p>
            {cacheAge !== null && (
              <div
                className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
                style={{ background: "rgba(82,121,111,0.15)", color: "#52796f", border: "1px solid rgba(82,121,111,0.4)" }}
              >
                <span>Cached snapshot · {formatRelativeTime(cacheAge)}</span>
              </div>
            )}
          </div>
          {!isOnline && cacheAge !== null && (
            <p className="text-xs text-amber-400 mt-1">
              Showing the last diagnostic saved on this device. New changes will sync when you reconnect.
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={runAnalysis}
            disabled={loading}
            className="px-4 py-2 bg-lira-green text-white rounded-lg text-sm font-medium hover:bg-lira-green/80 disabled:opacity-50"
          >
            {loading ? "Running..." : "Re-run Diagnosis"}
          </button>
          {syndrome && (
            <Link
              href={`/syndromes?project=${projectId}`}
              className="px-4 py-2 bg-lira-surface border border-lira-border text-slate-200 rounded-lg text-sm hover:border-lira-green/40"
            >
              View Syndromes →
            </Link>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-4 mb-6 text-red-400 text-sm">
          {error} — Make sure the backend is running on port 8000.
        </div>
      )}

      {diagnostic && (
        <>
          {/* Summary row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {[
              { label: "Degradation Severity", value: <SeverityBadge level={String(diagnostic.degradation_severity ?? "")} /> },
              { label: "Health Score", value: `${Math.round((diagnostic.composite_health_score as number) * 100)}%` },
              { label: "Data Completeness", value: `${diagnostic.data_completeness_pct}%` },
              { label: "Data Gaps", value: (diagnostic.data_gaps as string[]).length },
            ].map(({ label, value }) => (
              <div key={label} className="bg-lira-surface border border-lira-border rounded-xl p-4">
                <div className="text-xs text-lira-muted mb-2">{label}</div>
                <div className="text-lg font-semibold text-slate-100">{value}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Indicator table */}
            <Card title="Indicator Results">
              {indicators && Object.entries(indicators).map(([key, v]) => (
                <MetricRow
                  key={key}
                  label={key.replace(/_/g, " ")}
                  value={v.data_gap ? "— data gap" : `${v.category} (${v.value ?? "proxy"})`}
                  color={
                    v.data_gap ? "text-lira-muted" :
                    (v.severity_score as number) > 0.7 ? "text-red-400" :
                    (v.severity_score as number) > 0.4 ? "text-yellow-400" :
                    "text-lira-green"
                  }
                />
              ))}
            </Card>

            {/* Radar chart — lazy loaded */}
            <Card title="Severity Profile">
              <DiagnosisChart data={radarData} />
              <p className="text-xs text-lira-muted mt-2 text-center">0 = healthy · 100 = most degraded</p>
            </Card>
          </div>

          {/* Data gaps */}
          {(diagnostic.data_gaps as string[]).length > 0 && (
            <Card title="Data Gaps" badge="Needs Field Verification" badgeColor="bg-yellow-900/30 text-yellow-400" className="mb-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                {(diagnostic.data_gaps as string[]).map((gap) => (
                  <div key={gap} className="text-xs text-lira-muted bg-lira-border/20 rounded px-3 py-1.5">
                    {gap.replace(/_/g, " ")}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}

      {syndrome && (
        <Card title="Primary Syndrome Detected" badge={String(primary.risk_level ?? "")} badgeColor="bg-red-900/30 text-red-400">
          <div className="text-base font-semibold text-slate-100 mb-2">{String(primary.name ?? "")}</div>
          <p className="text-sm text-lira-muted mb-4">{String(syndrome.causal_narrative ?? "")}</p>
          <div className="flex gap-2 flex-wrap mb-4">
            {(primary.main_symptoms as string[] ?? []).map((s: string) => (
              <span key={s} className="text-xs bg-lira-border/40 text-slate-300 px-2 py-1 rounded">{s}</span>
            ))}
          </div>

          {/* AI Narrative */}
          <AIInsight
            narrativeType="syndrome"
            label="Summary"
            context={{
              zone_name: projectId,
              degradation_severity: diagnostic?.degradation_severity,
              lhii_score: diagnostic?.composite_health_score,
              lhii_class: (diagnostic?.composite_health_score as number) > 0.6 ? "good" : "degraded",
              syndrome_name: primary.name,
              drivers:  primary.likely_drivers ?? [],
              symptoms: primary.main_symptoms  ?? [],
            }}
            className="mb-4"
          />

          <div className="space-y-1">
            {(syndrome.assumptions as string[] ?? []).map((a) => (
              <AssumptionNote key={String(a)} text={String(a)} />
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

export default function DiagnosisPage() {
  return (
    <Suspense fallback={<div className="p-8 text-lira-muted">Loading...</div>}>
      <DiagnosisContent />
    </Suspense>
  );
}
