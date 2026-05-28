"use client";
import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Card, MetricRow, SeverityBadge } from "@/components/ui/Card";
import { clsx } from "clsx";
import { CloudLightning, Database, ExternalLink, CheckCircle, XCircle, Clock } from "lucide-react";

const ClimateDataCharts = dynamic(() => import("./ClimateDataCharts"), {
  ssr: false,
  loading: () => <div className="h-[280px] bg-lira-border/10 animate-pulse rounded-xl mb-6" />,
});

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const RISK_COLOR = (score: number) =>
  score > 0.7 ? "#c1121f" : score > 0.5 ? "#e07a2f" : score > 0.3 ? "#e9c46a" : "#2d6a4f";

const STATUS_ICON = (status: string) => {
  if (status.startsWith("REAL")) return <CheckCircle size={12} className="text-lira-green" />;
  if (status.startsWith("PENDING") || status.startsWith("CONNECTING")) return <Clock size={12} className="text-yellow-400" />;
  return <XCircle size={12} className="text-lira-muted" />;
};

export default function ClimateDataPage() {
  const [models, setModels]       = useState<Record<string, unknown> | null>(null);
  const [projections, setProj]    = useState<Record<string, unknown> | null>(null);
  const [risks, setRisks]         = useState<Record<string, unknown> | null>(null);
  const [sources, setSources]     = useState<Record<string, unknown> | null>(null);
  const [evidence, setEvidence]   = useState<Record<string, unknown> | null>(null);
  const [searchQ, setSearchQ]     = useState("Ethiopia landscape degradation");
  const [searchRes, setSearchRes] = useState<Record<string, unknown>[]>([]);
  const [searching, setSearching] = useState(false);
  const [activeScenario, setScenario] = useState("ssp245");
  const [error, setError]         = useState("");

  useEffect(() => {
    fetch(`${API}/climate-data/cmip6/models`).then(r => r.json()).then(setModels).catch(console.error);
    fetch(`${API}/climate-data/cmip6/projections`).then(r => r.json()).then(setProj).catch(console.error);
    fetch(`${API}/climate-data/cmip6/risk-indicators`).then(r => r.json()).then(setRisks).catch(console.error);
    fetch(`${API}/climate-data/sources/verified`).then(r => r.json()).then(setSources).catch(console.error);
    fetch(`${API}/climate-data/gardian/evidence`).then(r => r.json()).then(setEvidence).catch(console.error);
  }, []);

  const searchGardian = async () => {
    setSearching(true);
    try {
      const r = await fetch(`${API}/climate-data/gardian/search?q=${encodeURIComponent(searchQ)}&size=8`);
      const d = await r.json() as Record<string, unknown>;
      setSearchRes(d.results as Record<string, unknown>[] ?? []);
    } catch (e) { setError(String(e)); }
    finally { setSearching(false); }
  };

  // Build bar chart data for temperature + precipitation change
  const buildChartData = () => {
    if (!projections) return [];
    const scen = (projections.scenarios as Record<string, unknown> ?? {})[activeScenario] as Record<string, unknown> ?? {};
    return [2030, 2050, 2070].map(yr => {
      const d = scen[String(yr)] as Record<string, unknown> ?? {};
      const inds = d.indicators as Record<string, number> ?? {};
      const delta = d.deltas_vs_historical as Record<string, number> ?? {};
      return {
        year: String(yr),
        precip_mm: inds.annual_precip_mm ?? 0,
        heat_days: inds.heat_stress_days_35c ?? 0,
        delta_temp: delta["delta_temp_mean_c_c"] ?? 0,
        pct_precip: delta["pct_change_annual_precip_mm"] ?? 0,
        extreme_rain: inds.extreme_rain_days ?? 0,
        dry_days: inds.dry_days ?? 0,
        is_real: Boolean(d.is_real),
      };
    });
  };

  const buildRiskData = () => {
    if (!risks) return [];
    const scen = (risks.scenarios as Record<string, unknown> ?? {})[activeScenario] as Record<string, unknown> ?? {};
    return [2030, 2050, 2070].map(yr => {
      const r = scen[String(yr)] as Record<string, number> ?? {};
      return {
        year: String(yr),
        rainfall: Math.round((r.rainfall_intensity_risk ?? 0) * 100),
        drought:  Math.round((r.drought_dry_spell_risk  ?? 0) * 100),
        heat:     Math.round((r.heat_stress_risk        ?? 0) * 100),
        erosion:  Math.round((r.erosion_runoff_risk     ?? 0) * 100),
        overall:  Math.round((r.overall_climate_risk_score ?? 0) * 100),
        is_real:  Boolean(r.is_real),
      };
    });
  };

  const chartData = buildChartData();
  const riskData  = buildRiskData();
  const sourceList = Object.entries(sources?.sources as Record<string, Record<string, string>> ?? {});
  const evidenceCards = (evidence?.evidence_cards as Record<string, unknown>[] ?? []).slice(0, 12);

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <CloudLightning size={20} className="text-lira-sky" />
          <h1 className="text-2xl font-bold text-slate-100">CMIP6 Climate Projections + GARDIAN Evidence</h1>
        </div>
        <p className="text-lira-muted text-sm">
          NASA NEX GDDP CMIP6 · CIL GDPCIR · CGIAR CGSpace · Microsoft Planetary Computer · Omo-Ghibe Basin
        </p>
      </div>

      {error && <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-4 mb-6 text-red-400 text-sm">{error}</div>}

      {/* Data source status */}
      {sources && (
        <Card title="Data Sources Verification" className="mb-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {sourceList.map(([key, src]) => (
              <div key={key} className="border border-lira-border/40 rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  {STATUS_ICON(src.status ?? "")}
                  <span className="text-xs font-medium text-slate-200">{key.replace(/_/g," ")}</span>
                  <span className={clsx("text-[10px] px-1.5 py-0.5 rounded ml-auto",
                    src.status?.startsWith("REAL") ? "bg-lira-green/20 text-lira-green" :
                    "bg-yellow-900/20 text-yellow-400")}>
                    {src.status?.split(" ")[0]}
                  </span>
                </div>
                <div className="text-[10px] text-lira-muted">{src.description}</div>
                {src.url && (
                  <a href={src.url} target="_blank" rel="noopener noreferrer"
                    className="text-[10px] text-lira-sky flex items-center gap-1 mt-1 hover:opacity-70">
                    <ExternalLink size={9} /> {src.url.slice(8, 55)}…
                  </a>
                )}
              </div>
            ))}
          </div>
          <div className="mt-3 text-[10px] text-lira-muted">
            PC Examples: {" "}
            <a href="https://github.com/microsoft/PlanetaryComputerExamples/tree/main/datasets"
              target="_blank" className="text-lira-sky hover:underline">
              github.com/microsoft/PlanetaryComputerExamples
            </a>
          </div>
        </Card>
      )}

      {/* CMIP6 Models */}
      {models && (
        <Card title="CMIP6 Models — Omo-Ghibe Basin" className="mb-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mb-3">
            {Object.entries(models.models as Record<string, string>).map(([m, desc]) => (
              <div key={m} className="bg-lira-bg border border-lira-border rounded-lg px-3 py-2">
                <div className="text-xs font-medium text-lira-sky">{m}</div>
                <div className="text-[10px] text-lira-muted mt-0.5">{desc.slice(0,60)}</div>
              </div>
            ))}
          </div>
          <div className="flex gap-3 text-[10px] text-lira-muted">
            <span>Collection: nasa-nex-gddp-cmip6</span>
            <span>·</span>
            <a href="https://planetarycomputer.microsoft.com/dataset/nasa-nex-gddp-cmip6"
              target="_blank" className="text-lira-sky hover:underline flex items-center gap-1">
              <ExternalLink size={9} /> Planetary Computer
            </a>
            <span>·</span>
            <a href="https://github.com/microsoft/PlanetaryComputerExamples/blob/main/quickstarts/reading-stac.ipynb"
              target="_blank" className="text-lira-sky hover:underline flex items-center gap-1">
              <ExternalLink size={9} /> STAC reading guide
            </a>
          </div>
        </Card>
      )}

      {/* Scenario selector */}
      <div className="flex gap-3 mb-6">
        {["ssp245","ssp585"].map(sc => (
          <button key={sc} onClick={() => setScenario(sc)}
            className={clsx("px-4 py-2 rounded-lg text-sm font-medium border transition-all",
              activeScenario === sc
                ? "bg-lira-sky text-white border-lira-sky"
                : "border-lira-border text-lira-muted hover:border-lira-sky/40")}>
            {sc.toUpperCase()} {sc === "ssp245" ? "(Middle-of-road)" : "(High-end)"}
          </button>
        ))}
      </div>

      {/* Charts — lazy loaded */}
      {chartData.length > 0 && (
        <ClimateDataCharts
          chartData={chartData}
          riskData={riskData}
          activeScenario={activeScenario}
        />
      )}

      {/* GARDIAN Evidence */}
      <Card title="CGIAR Evidence Library — CGSpace / GARDIAN" className="mb-6">
        <div className="flex gap-3 mb-4">
          <input value={searchQ} onChange={e => setSearchQ(e.target.value)}
            className="flex-1 bg-lira-bg border border-lira-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-lira-green/60"
            placeholder="Search CGIAR CGSpace..." />
          <button onClick={searchGardian} disabled={searching}
            className="px-4 py-2 bg-lira-green text-white rounded-lg text-sm hover:bg-lira-green/80 disabled:opacity-50">
            {searching ? "Searching…" : "Search"}
          </button>
        </div>

        {searchRes.length > 0 && (
          <div className="grid gap-2 mb-4">
            {searchRes.map((r) => (
              <div key={String(r.id)} className="border border-lira-border/40 rounded-lg p-3">
                <div className="text-xs font-medium text-slate-200">{String(r.title ?? "").slice(0,90)}</div>
                <div className="text-[10px] text-lira-muted mt-0.5">
                  {String(r.author ?? "").slice(0,40)} · {String(r.year ?? "")}
                </div>
                {!!r.cgspace_url && (
                  <a href={String(r.cgspace_url)} target="_blank" className="text-[10px] text-lira-sky hover:underline mt-1 flex items-center gap-1">
                    <ExternalLink size={9}/> CGSpace
                  </a>
                )}
              </div>
            ))}
          </div>
        )}

        {evidence && (
          <>
            <div className="text-xs font-medium text-lira-muted uppercase mb-3">
              Pre-harvested evidence cards ({Number((evidence?.meta as Record<string,unknown>)?.total_cards ?? 0)} total)
            </div>
            <div className="grid gap-2 max-h-80 overflow-y-auto pr-1">
              {evidenceCards.map((card) => (
                <div key={String(card.source_id)} className="border border-lira-border/30 rounded-lg p-3">
                  <div className="text-xs font-medium text-slate-200">{String(card.title ?? "").slice(0,80)}</div>
                  <div className="flex gap-2 mt-1 flex-wrap">
                    <span className="text-[10px] text-lira-muted">{String(card.year ?? "")}</span>
                    {(card.lira_ai_agents as string[] ?? []).slice(0,2).map((a) => (
                      <span key={a} className="text-[10px] bg-lira-green/10 text-lira-green px-1.5 py-0.5 rounded">{a.replace("Agent","")}</span>
                    ))}
                    <span className="text-[10px] text-lira-muted ml-auto">{String(card.lira_ai_topic ?? "").replace(/_/g," ")}</span>
                  </div>
                  {Boolean(card.cgspace_url) && (
                    <a href={String(card.cgspace_url)} target="_blank"
                      className="text-[10px] text-lira-sky hover:underline flex items-center gap-1 mt-1">
                      <ExternalLink size={9}/> View on CGSpace
                    </a>
                  )}
                </div>
              ))}
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
