"use client";
import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Card, MetricRow, SeverityBadge } from "@/components/ui/Card";
import { clsx } from "clsx";
import AIInsight from "@/components/ui/AIInsight";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from "recharts";
import { Clock } from "lucide-react";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { useMutationQueue } from "@/hooks/useMutationQueue";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ETHIOPIA_BBOX = [38.45, 11.55, 38.52, 11.61];

function MonitoringContent() {
  const params = useSearchParams();
  const projectId = params.get("project") ?? "MOCK-ETH-001";

  const { isOnline } = useOnlineStatus();
  const { enqueue }  = useMutationQueue();

  const [monitoring, setMonitoring] = useState<Record<string, unknown> | null>(null);
  const [melia, setMelia]           = useState<Record<string, unknown> | null>(null);
  const [lhii, setLhii]             = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading]       = useState<string | null>(null);
  const [error, setError]           = useState("");
  const [status, setStatus]         = useState<"idle" | "queued">("idle");

  const post = async (path: string, body: unknown) => {
    const res = await fetch(`${API}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  };

  const runMonitoring = async () => {
    setLoading("monitoring"); setError(""); setStatus("idle");

    const body = {
      project_id: projectId,
      bbox: ETHIOPIA_BBOX,
      baseline_date_range: "2020-01-01/2021-01-01",
      current_date_range:  "2023-01-01/2024-01-01",
    };

    if (!isOnline) {
      await enqueue(`/monitoring/run/${projectId}`, "POST", body);
      setStatus("queued");
      setLoading(null);
      return;
    }

    try {
      const data = await post(`/monitoring/run/${projectId}`, body);
      setMonitoring(data);
    } catch (e) { setError(String(e)); }
    finally { setLoading(null); }
  };

  const runMelia = async () => {
    setLoading("melia"); setError("");
    try {
      const data = await post(`/monitoring/melia/${projectId}`, {
        project_id: projectId,
        syndromes_classified: 1,
        pathways_generated: 7,
        passports_created: 1,
        field_validation_done: false,
        policy_briefs_generated: 1,
        re_prescriptions: 0,
      });
      setMelia(data);
    } catch (e) { setError(String(e)); }
    finally { setLoading(null); }
  };

  const alerts = monitoring?.alerts as Record<string, unknown>[] ?? [];
  const melaInds = melia?.indicators as Record<string, unknown>[] ?? [];

  const radarData = lhii
    ? (lhii.components as Record<string, unknown>[]).map((c) => ({
        subject: String(c.name).replace(/_/g, " "),
        score: Math.round((c.score as number) * 100),
      }))
    : [];

  const trajectoryColor = {
    improving: "text-lira-green",
    stable: "text-yellow-400",
    declining: "text-red-400",
    insufficient_data: "text-lira-muted",
  }[String(monitoring?.recovery_trajectory ?? "insufficient_data")] ?? "text-lira-muted";

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:justify-between items-start gap-4 mb-6 lg:mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Monitoring & MELIA</h1>
          <p className="text-lira-muted text-sm mt-1">
            Before-after tracking, NDVI trends, re-prescription alerts, and MELIA framework
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={runMelia} disabled={!!loading}
            className="px-4 py-2 bg-lira-surface border border-lira-border text-slate-200 rounded-lg text-sm hover:border-lira-green/40 disabled:opacity-50">
            {loading === "melia" ? "Generating…" : "Generate MELIA Report"}
          </button>
          <button onClick={runMonitoring} disabled={!!loading}
            className="px-4 py-2 bg-lira-green text-white rounded-lg text-sm font-medium hover:bg-lira-green/80 disabled:opacity-50">
            {loading === "monitoring" ? "Running…" : "Run Monitoring (Sentinel-2)"}
          </button>
        </div>
      </div>

      {error && <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-4 mb-6 text-red-400 text-sm">{error}</div>}

      {status === "queued" && (
        <div className="flex items-center gap-2 bg-amber-900/10 border border-amber-900/30 rounded-xl p-4 mb-6 text-amber-400 text-sm">
          <Clock size={14} className="shrink-0" />
          <span>Queued — will sync when you reconnect.</span>
        </div>
      )}

      {/* Monitoring results */}
      {monitoring && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {[
              { label: "Recovery Trajectory", value: <span className={trajectoryColor}>{String(monitoring.recovery_trajectory).replace(/_/g, " ")}</span> },
              { label: "Baseline NDVI", value: monitoring.baseline_ndvi != null ? (monitoring.baseline_ndvi as number).toFixed(3) : "N/A" },
              { label: "Current NDVI", value: monitoring.current_ndvi != null ? (monitoring.current_ndvi as number).toFixed(3) : "N/A" },
              { label: "NDVI Change", value: monitoring.ndvi_change_absolute != null
                ? `${(monitoring.ndvi_change_absolute as number) >= 0 ? "+" : ""}${(monitoring.ndvi_change_absolute as number).toFixed(4)}`
                : "N/A" },
            ].map(({ label, value }) => (
              <div key={label} className="bg-lira-surface border border-lira-border rounded-xl p-4">
                <div className="text-xs text-lira-muted mb-1">{label}</div>
                <div className="text-base font-semibold text-slate-100">{value}</div>
              </div>
            ))}
          </div>

          {/* Alerts */}
          {alerts.length > 0 && (
            <Card title="Monitoring Alerts" badge={`${alerts.length} alert${alerts.length !== 1 ? "s" : ""}`}
              badgeColor="bg-red-900/30 text-red-400" className="mb-6">
              {alerts.map((a, i) => (
                <div key={i} className={clsx("border-l-2 pl-4 py-2 mb-3 last:mb-0 rounded-r", {
                  "border-red-500 bg-red-900/10": a.severity === "critical" || a.severity === "high",
                  "border-yellow-500 bg-yellow-900/10": a.severity === "medium",
                  "border-lira-border": a.severity === "low",
                })}>
                  <div className="text-xs font-semibold text-slate-200 mb-0.5">{String(a.alert_type).replace(/_/g, " ").toUpperCase()}</div>
                  <div className="text-sm text-slate-300">{String(a.message)}</div>
                  <div className="text-xs text-lira-sky mt-1">Action: {String(a.recommended_action)}</div>
                </div>
              ))}
            </Card>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">
            <Card title="Before–After Summary">
              <p className="text-sm text-slate-300 leading-relaxed">{String(monitoring.before_after_summary)}</p>
              <div className="mt-3 text-xs text-yellow-400 border border-yellow-900/30 bg-yellow-900/10 rounded px-3 py-2">
                {String(monitoring.treated_control_status)}
              </div>
            </Card>
            <Card title="Re-prescription Status">
              <div className={clsx("text-2xl font-bold mb-3",
                monitoring.re_prescription_needed ? "text-red-400" : "text-lira-green")}>
                {monitoring.re_prescription_needed ? "⚠ Required" : "✓ Not needed"}
              </div>
              <MetricRow label="Next monitoring date" value={String(monitoring.next_monitoring_date)} />
              <MetricRow label="Data confidence" value={String(monitoring.confidence)} />
              <MetricRow label="Real satellite data" value={monitoring.is_mock ? "No (mock)" : "Yes"} />
            </Card>
          </div>

          {/* AI Monitoring Interpretation */}
          <AIInsight
            narrativeType="monitoring"
            label="Summary"
            context={{
              monitoring_period:     monitoring.monitoring_period,
              baseline_ndvi:         monitoring.baseline_ndvi,
              current_ndvi:          monitoring.current_ndvi,
              ndvi_change_pct:       monitoring.ndvi_change_pct,
              recovery_trajectory:   monitoring.recovery_trajectory,
              alerts:                alerts,
              re_prescription_needed:monitoring.re_prescription_needed,
            }}
          />
        </>
      )}

      {/* MELIA report */}
      {melia && (
        <Card title="MELIA Framework Report" className="mb-6">
          <div className="flex items-center gap-4 mb-5">
            <div className={clsx("text-sm font-bold px-3 py-1 rounded-full", {
              "bg-lira-green/20 text-lira-green": melia.overall_progress === "on_track",
              "bg-yellow-900/20 text-yellow-400": melia.overall_progress === "partial",
              "bg-red-900/20 text-red-400": melia.overall_progress === "lagging",
            })}>
              {String(melia.overall_progress).replace(/_/g, " ").toUpperCase()}
            </div>
            <p className="text-xs text-lira-muted">{String(melia.summary)}</p>
          </div>

          <div className="space-y-2">
            {melaInds.map((ind) => (
              <div key={String(ind.result_area)}
                className="grid grid-cols-[1fr_1fr_auto] gap-4 items-center border border-lira-border/40 rounded-lg px-4 py-2.5">
                <div>
                  <div className="text-xs font-medium text-slate-200">{String(ind.result_area)}</div>
                  <div className="text-[10px] text-lira-muted mt-0.5">{String(ind.indicator)}</div>
                </div>
                <div className="text-xs text-lira-muted">
                  Target: {String(ind.target).slice(0, 50)}
                </div>
                <div className={clsx("text-xs font-semibold px-2 py-0.5 rounded", {
                  "bg-lira-green/20 text-lira-green": ind.status === "on_track",
                  "bg-yellow-900/20 text-yellow-400": ind.status === "partial",
                  "bg-lira-border text-lira-muted": ind.status === "not_started",
                  "bg-blue-900/20 text-blue-400": ind.status === "exceeded",
                })}>
                  {String(ind.status).replace(/_/g, " ")}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

export default function MonitoringPage() {
  return <Suspense fallback={<div className="p-8 text-lira-muted">Loading…</div>}><MonitoringContent /></Suspense>;
}
