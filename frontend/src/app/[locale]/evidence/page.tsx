"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Card, MetricRow } from "@/components/ui/Card";
import { CheckCircle, XCircle, Clock, ExternalLink, Database } from "lucide-react";
import { clsx } from "clsx";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { useMutationQueue } from "@/hooks/useMutationQueue";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const SAMPLE_BOUNDARY = {
  type: "Feature",
  geometry: {
    type: "Polygon",
    coordinates: [[[38.45,11.55],[38.52,11.55],[38.52,11.61],[38.45,11.61],[38.45,11.55]]]
  },
  properties: { name: "Mock Amhara Kebele" }
};

const SOURCE_COLORS: Record<string, string> = {
  sentinel: "text-blue-400",
  dem: "text-purple-400",
  land_cover: "text-green-400",
  soil: "text-yellow-600",
  rainfall: "text-sky-400",
  climate: "text-orange-400",
  productivity: "text-lira-green",
};

function EvidenceContent() {
  const params = useSearchParams();
  const projectId = params.get("project") ?? "MOCK-ETH-001";

  const { isOnline } = useOnlineStatus();
  const { enqueue }  = useMutationQueue();

  const [evidence, setEvidence] = useState<Record<string, unknown> | null>(null);
  const [catalog, setCatalog]   = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");
  const [status, setStatus]     = useState<"idle" | "queued">("idle");

  // Auto-load catalog on mount
  useEffect(() => {
    fetch(`${API}/evidence/sources/catalog`)
      .then(r => r.json()).then(setCatalog).catch(console.error);
  }, []);

  const fetchEvidence = async () => {
    setLoading(true); setError(""); setStatus("idle");

    const body = {
      project_id: projectId,
      geojson_boundary: SAMPLE_BOUNDARY,
      date_range: "2022-01-01/2024-01-01",
    };

    if (!isOnline) {
      await enqueue("/evidence/fetch", "POST", body);
      setStatus("queued");
      setLoading(false);
      return;
    }

    try {
      const res = await fetch(`${API}/evidence/fetch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      setEvidence(await res.json());
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  const loadCatalog = async () => {
    const res = await fetch(`${API}/evidence/sources/catalog`);
    setCatalog(await res.json());
  };

  const layers = (evidence?.evidence as Record<string, unknown> | undefined)?.evidence_layers as Record<string, Record<string, unknown>> | undefined;

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:justify-between items-start gap-4 mb-6 lg:mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Evidence Cloud</h1>
          <p className="text-lira-muted text-sm mt-1">
            Fetch real data from Planetary Computer, SoilGrids, CHIRPS & ERA5 — {projectId}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={loadCatalog}
            className="px-4 py-2 bg-lira-surface border border-lira-border text-slate-200 rounded-lg text-sm hover:border-lira-sky/40">
            View Data Catalog
          </button>
          <button onClick={fetchEvidence} disabled={loading}
            className="px-4 py-2 bg-lira-sky text-white rounded-lg text-sm font-medium hover:bg-lira-sky/80 disabled:opacity-50">
            {loading ? "Fetching data…" : "Fetch All Evidence Layers"}
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-4 mb-6 text-red-400 text-sm">
          {error} — Ensure the backend is running on port 8000.
        </div>
      )}

      {status === "queued" && (
        <div className="flex items-center gap-2 bg-amber-900/10 border border-amber-900/30 rounded-xl p-4 mb-6 text-amber-400 text-sm">
          <Clock size={14} className="shrink-0" />
          <span>Queued — will sync when you reconnect.</span>
        </div>
      )}

      {/* Data source catalog */}
      {catalog && (
        <Card title="Integrated Data Sources" className="mb-6">
          <div className="grid gap-3">
            {(catalog.sources as Record<string, unknown>[]).map((s) => (
              <div key={String(s.name)} className="border border-lira-border/50 rounded-lg p-3 flex justify-between items-start">
                <div>
                  <div className="text-sm font-medium text-slate-200">{String(s.name)}</div>
                  <div className="text-xs text-lira-muted mt-0.5">{String(s.variables)}</div>
                  <div className="text-xs text-lira-muted">{String(s.provider)} · {String(s.temporal)}</div>
                </div>
                {(Boolean(s.catalog_url) || Boolean(s.api_url)) && (
                  <a href={String(s.catalog_url ?? s.api_url)} target="_blank" rel="noopener noreferrer"
                    className="text-lira-sky hover:text-lira-sky/70 flex items-center gap-1 text-xs mt-1">
                    <ExternalLink size={11} /> Catalog
                  </a>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Evidence results */}
      {evidence && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {[
              { label: "Real Data Layers", value: `${evidence.real_data_layers} / ${evidence.total_layers}` },
              { label: "Data Completeness", value: `${evidence.data_completeness_pct}%` },
              { label: "Project ID", value: String(evidence.project_id) },
            ].map(({ label, value }) => (
              <div key={label} className="bg-lira-surface border border-lira-border rounded-xl p-4">
                <div className="text-xs text-lira-muted mb-1">{label}</div>
                <div className="text-base font-semibold text-slate-100">{value}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">
            {layers && Object.entries(layers).map(([key, layer]) => {
              const isReal = Boolean(layer.is_real);
              return (
                <Card key={key} title={key.replace(/_/g, " ").toUpperCase()}>
                  <div className="flex items-center gap-2 mb-3">
                    {isReal
                      ? <CheckCircle size={14} className="text-lira-green" />
                      : <XCircle size={14} className="text-lira-muted" />}
                    <span className={clsx("text-xs", isReal ? "text-lira-green" : "text-lira-muted")}>
                      {isReal ? "Real data fetched" : "Mock fallback"}
                    </span>
                  </div>
                  {Object.entries(layer)
                    .filter(([k]) => !["source","is_real","note","bbox","period","class_fractions_pct","annual_totals_mm","annual_ndvi","years"].includes(k))
                    .map(([k, v]) => (
                      <MetricRow key={k} label={k.replace(/_/g, " ")}
                        value={typeof v === "number" ? v.toFixed(3) : String(v)}
                        color={isReal ? "text-slate-200" : "text-lira-muted"} />
                    ))
                  }
                  <div className="text-[10px] text-lira-muted mt-2 border-t border-lira-border/40 pt-1.5">
                    {String(layer.source ?? "unknown")}
                  </div>
                  {Boolean(layer.note) && (
                    <div className="text-[10px] text-yellow-400 mt-1">{String(layer.note)}</div>
                  )}
                </Card>
              );
            })}
          </div>

          {/* Indicators extracted */}
          {(evidence.evidence as Record<string, unknown> | undefined)?.indicators && (
            <Card title="Extracted Indicators (ready for diagnosis engine)">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8">
                {Object.entries((evidence.evidence as Record<string, unknown>).indicators as Record<string, unknown>)
                  .filter(([, v]) => v !== null)
                  .map(([k, v]) => (
                    <MetricRow key={k} label={k.replace(/_/g, " ")}
                      value={typeof v === "number" ? v.toFixed(4) : String(v)} />
                  ))}
              </div>
            </Card>
          )}
        </>
      )}

      {!evidence && !loading && (
        <div className="bg-lira-surface border border-lira-border rounded-xl p-12 text-center">
          <Database size={32} className="text-lira-muted mx-auto mb-4" />
          <p className="text-slate-300 mb-2">Evidence Cloud not yet populated</p>
          <p className="text-sm text-lira-muted mb-4">
            Click "Fetch All Evidence Layers" to pull real data from Planetary Computer.
            Falls back to clearly-labelled mock data if network is unavailable.
          </p>
          <div className="text-xs text-lira-muted">
            Sources: Sentinel-2 · Copernicus DEM · ESA WorldCover · SoilGrids · CHIRPS · ERA5 · MODIS
          </div>
        </div>
      )}
    </div>
  );
}

export default function EvidencePage() {
  return <Suspense fallback={<div className="p-8 text-lira-muted">Loading…</div>}><EvidenceContent /></Suspense>;
}
