"use client";
import dynamic from "next/dynamic";
import { useState, useEffect } from "react";
import { clsx } from "clsx";
import { Layers, Activity, AlertTriangle, CheckCircle, MapPin } from "lucide-react";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { useTranslations } from "next-intl";
import { fetchAggregateStats, fetchGeotiff } from "@/lib/api";

// Single dynamic import for ALL Leaflet code — the only correct Next.js pattern
const LeafletMap = dynamic(() => import("@/components/map/LeafletMap"), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full bg-lira-bg">
      <div className="flex items-center gap-2 text-lira-muted-aa-aa text-sm">
        <Activity size={16} className="animate-pulse text-lira-green" />
        Loading map…
      </div>
    </div>
  ),
});

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const LHII_COLORS: Record<string, string> = {
  severely_degraded: "#c1121f",
  degraded:          "#e07a2f",
  fair:              "#e9c46a",
  good:              "#52796f",
  excellent:         "#2d6a4f",
};

const LAYER_OPTIONS = [
  { id: "lhii",      label: "LHII Score",  desc: "Landscape Health Index (0–1)" },
  { id: "syndrome",  label: "Syndrome",    desc: "Primary degradation syndrome" },
  { id: "ndvi",      label: "NDVI",        desc: "Vegetation index — Sentinel-2" },
  { id: "soil_loss", label: "Erosion",     desc: "t/ha/yr — Enhanced RUSLE" },
  { id: "rainfall",  label: "Rainfall",   desc: "Annual mm — CHIRPS" },
];

function fmt(v: unknown, unit = "") {
  if (v == null) return "—";
  const n = Number(v);
  return isNaN(n) ? String(v) : `${n.toFixed(1)}${unit}`;
}

// Aggregate panel — shown when 2+ zones are selected
function AggregatePanel({
  stats,
  loading,
  t,
}: {
  stats: Record<string, unknown> | null;
  loading: boolean;
  t: ReturnType<typeof useTranslations>;
}) {
  const zoneCount = stats ? Number(stats.zone_count ?? 0) : 0;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-bold text-slate-100">{t("map.aggregateZones")}</h2>
        {zoneCount > 0 && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-lira-green/20 text-lira-green font-medium">
            {zoneCount} zones
          </span>
        )}
      </div>

      {loading ? (
        <div className="space-y-2 animate-pulse">
          {[80, 90, 70].map((w) => (
            <div key={w} className="h-6 bg-lira-border/40 rounded" style={{ width: `${w}%` }} />
          ))}
        </div>
      ) : stats ? (
        <>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-lira-bg rounded-lg p-2 border border-lira-border/30">
              <div className="text-xs text-lira-muted-aa">Mean LHII</div>
              <div className="text-xs font-semibold text-slate-200">
                {Number(stats.mean_lhii ?? 0).toFixed(4)}
              </div>
            </div>
            <div className="bg-lira-bg rounded-lg p-2 border border-lira-border/30">
              <div className="text-xs text-lira-muted-aa">Mean NDVI</div>
              <div className="text-xs font-semibold text-slate-200">
                {Number(stats.mean_ndvi ?? 0).toFixed(3)}
              </div>
            </div>
            <div className="bg-lira-bg rounded-lg p-2 border border-lira-border/30">
              <div className="text-xs text-lira-muted-aa">Mean Erosion</div>
              <div className="text-xs font-semibold text-slate-200">
                {Number(stats.mean_soil_loss_t_ha_yr ?? 0).toFixed(1)} t/ha/yr
              </div>
            </div>
            <div className="bg-lira-bg rounded-lg p-2 border border-lira-border/30">
              <div className="text-xs text-lira-muted-aa">Mean Rainfall</div>
              <div className="text-xs font-semibold text-slate-200">
                {Math.round(Number(stats.mean_rainfall_mm ?? 0))} mm
              </div>
            </div>
          </div>

          <div className="bg-lira-bg border border-lira-border/50 rounded-lg p-3">
            <div className="text-xs text-lira-muted-aa uppercase mb-1">{t("map.aggregateStats")}</div>
            <div className="text-xs font-semibold text-slate-200">
              {String(stats.dominant_syndrome ?? "—").replace(/_/g, " ")}
            </div>
          </div>

          {Array.isArray(stats.zones) && (stats.zones as Record<string, unknown>[]).length > 0 && (
            <div className="space-y-1">
              {(stats.zones as Record<string, unknown>[]).map((z) => (
                <div key={String(z.zone_id)} className="flex items-center justify-between text-xs text-lira-muted-aa border-b border-lira-border/20 pb-1">
                  <span>{String(z.zone_name ?? z.zone_id)}</span>
                  <span className="text-slate-300 font-medium">{Number(z.lhii_score ?? 0).toFixed(3)}</span>
                </div>
              ))}
            </div>
          )}

          <p className="text-xs text-lira-muted-aa italic">{t("map.ndviSimulated")}</p>
        </>
      ) : (
        <p className="text-xs text-lira-muted-aa italic">Loading aggregate data…</p>
      )}
    </div>
  );
}

// Zone detail panel — used by both desktop side panel and mobile BottomSheet
function ZoneDetailPanel({
  data,
  narrative,
  narLoading,
}: {
  data: Record<string, unknown>;
  narrative: string;
  narLoading: boolean;
}) {
  return (
    <div className="p-4 space-y-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-bold text-slate-100">{String(data.zone_name ?? "")}</h2>
          <div className="text-xs text-lira-muted-aa mt-0.5">{String(data.primary_land_use ?? "")}</div>
        </div>
        <span className="text-xs px-2 py-0.5 rounded-full font-medium shrink-0"
          style={{
            background: (LHII_COLORS[String(data.lhii_class)] ?? "#7a9ab0") + "22",
            color:       LHII_COLORS[String(data.lhii_class)] ?? "#7a9ab0",
          }}>
          LHII {fmt(data.lhii_score)}
        </span>
      </div>

      <div className="bg-lira-bg border border-lira-border/50 rounded-lg p-3">
        <div className="text-xs text-lira-muted-aa uppercase mb-1">Primary Syndrome</div>
        <div className="text-xs font-semibold text-slate-200">{String(data.syndrome_name ?? "")}</div>
        <div className="text-xs mt-0.5 text-orange-400">Risk: {String(data.syndrome_risk ?? "")}</div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        {([
          ["NDVI",    fmt(data.ndvi),                    "Sentinel-2"],
          ["SOC",     fmt(data.soc_g_per_kg, " g/kg"),   "SoilGrids"],
          ["Rain",    fmt(data.rainfall_mm, " mm"),      "CHIRPS"],
          ["Temp",    fmt(data.temp_c, "°C"),            "ERA5"],
          ["Slope",   fmt(data.slope_deg, "°"),          "DEM"],
          ["Forest",  fmt(data.forest_pct, "%"),         "WorldCover"],
          ["Erosion", fmt(data.soil_loss_t_ha_yr, " t/ha/yr"), "RUSLE"],
          ["Health",  fmt(Number(data.health_score)*100, "%"),  "LHII"],
        ] as [string,string,string][]).map(([label, value, source]) => (
          <div key={label} className="bg-lira-bg rounded-lg p-2 border border-lira-border/30">
            <div className="text-xs text-lira-muted-aa">{label}</div>
            <div className="text-xs font-semibold text-slate-200">{value}</div>
            <div className="text-xs text-lira-border">{source}</div>
          </div>
        ))}
      </div>

      {Array.isArray(data.hotspots) && (data.hotspots as string[]).length > 0 && (
        <div>
          <div className="text-xs font-medium text-red-400 uppercase mb-1 flex items-center gap-1">
            <AlertTriangle size={10}/> Hotspots
          </div>
          {(data.hotspots as string[]).map((h, i) => (
            <div key={i} className="text-xs text-orange-300 border-l-2 border-red-500/40 pl-2 py-0.5 mb-1">{h}</div>
          ))}
        </div>
      )}

      {Array.isArray(data.green_spots) && (data.green_spots as string[]).length > 0 && (
        <div>
          <div className="text-xs font-medium text-lira-green uppercase mb-1 flex items-center gap-1">
            <CheckCircle size={10}/> Green Spots
          </div>
          {(data.green_spots as string[]).map((g, i) => (
            <div key={i} className="text-xs text-green-300 border-l-2 border-lira-green/40 pl-2 py-0.5 mb-1">{g}</div>
          ))}
        </div>
      )}

      <div className="border-t border-lira-border/40 pt-3">
        <div className="text-xs font-medium text-lira-sky uppercase mb-2 flex items-center gap-1">
          <Activity size={10}/>
          AI Narrative {narLoading && <span className="text-lira-muted-aa">(generating…)</span>}
        </div>
        {narLoading ? (
          <div className="space-y-1.5 animate-pulse">
            {[85,95,70,88].map(w => (
              <div key={w} className="h-2 bg-lira-border/40 rounded" style={{width:`${w}%`}}/>
            ))}
          </div>
        ) : narrative ? (
          <p className="text-xs text-slate-300 leading-relaxed">{narrative}</p>
        ) : (
          <p className="text-xs text-lira-muted-aa italic">Generating after zone loads…</p>
        )}
      </div>

      <div className="text-xs text-lira-border border-t border-lira-border/30 pt-2">
        Real data: {String(data.real_data_layers)}/7 · Completeness: {fmt(data.data_completeness)}%
      </div>
    </div>
  );
}

function EmptyZonePanel({ t }: { t: ReturnType<typeof useTranslations> }) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-5 py-8">
      <MapPin size={28} className="mb-3 text-lira-border" />
      <p className="text-sm font-medium text-slate-300 mb-1">Click a zone on the map</p>
      <p className="text-xs text-lira-muted-aa leading-relaxed mb-1">
        View LHII, indicators, soil erosion, and AI narrative
      </p>
      <p className="text-xs text-lira-muted-aa mt-1 mb-4">{t("map.multiSelectHint")}</p>
      <div className="space-y-1.5 text-left w-full">
        {Object.entries(LHII_COLORS).map(([k, c]) => (
          <div key={k} className="flex items-center gap-2 text-xs text-lira-muted-aa">
            <span className="w-3 h-3 rounded-sm shrink-0" style={{ background: c }} />
            {k.replace(/_/g," ")}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function MapPage() {
  const t = useTranslations();
  const [geojson, setGeojson]           = useState<object | null>(null);
  const [activeLayer, setLayer]         = useState("lhii");
  const [selected, setSelected]         = useState<Record<string, unknown> | null>(null);
  const [narrative, setNarr]            = useState<string>("");
  const [narLoading, setNarLoading]     = useState(false);
  const [error, setError]               = useState("");
  const [selectedZones, setSelectedZones] = useState<string[]>([]);
  const [aggregateStats, setAggregateStats] = useState<Record<string, unknown> | null>(null);
  const [aggLoading, setAggLoading]     = useState(false);
  const [ndviYear, setNdviYear]           = useState<number>(2023);
  const [ndviHistory, setNdviHistory]     = useState<{ year: number; ndvi: number }[]>([]);
  const [exporting, setExporting]         = useState(false);

  useEffect(() => {
    fetch(`${API}/spatial/basin/geojson`)
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status} — backend may be offline`); return r.json(); })
      .then(setGeojson)
      .catch(e => setError(String(e)));
  }, []);

  // Fetch aggregate stats when 2+ zones are selected
  useEffect(() => {
    if (selectedZones.length < 2) { setAggregateStats(null); return; }
    setAggLoading(true);
    fetchAggregateStats(selectedZones)
      .then(setAggregateStats)
      .catch(() => setAggregateStats(null))
      .finally(() => setAggLoading(false));
  }, [selectedZones]);

  const handleZoneShiftClick = (zoneId: string) => {
    setSelectedZones(prev =>
      prev.includes(zoneId) ? prev.filter(id => id !== zoneId) : [...prev, zoneId]
    );
  };

  const handleNdviYear = async (year: number) => {
    setNdviYear(year);
    if (!selected?.zone_id || activeLayer !== "ndvi") return;
    try {
      const r = await fetch(`${API}/spatial/zone/${selected.zone_id}/ndvi-history?start_year=2020&end_year=2025`);
      const d = await r.json() as { series: { year: number; ndvi: number }[] };
      setNdviHistory(d.series ?? []);
    } catch { /* non-critical */ }
  };

  useEffect(() => {
    if (activeLayer !== "ndvi" || !selected?.zone_id) return;
    handleNdviYear(ndviYear);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeLayer, selected?.zone_id]);

  const handleExportGeoTiff = async () => {
    const zoneIds = selectedZones.length > 0
      ? selectedZones
      : selected?.zone_id
      ? [String(selected.zone_id)]
      : ["highland"];
    setExporting(true);
    try {
      const blob = await fetchGeotiff(activeLayer, zoneIds);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `lira_${activeLayer}_${zoneIds.join("_")}.tif`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("GeoTIFF export failed:", err);
    } finally {
      setExporting(false);
    }
  };

  const loadNarrative = async (zoneId: string) => {
    setNarLoading(true); setNarr("");
    try {
      const r = await fetch(`${API}/spatial/zone/${zoneId}/narrative?narrative_type=syndrome`, { method: "POST" });
      const d = await r.json() as Record<string, unknown>;
      setNarr(String(d.text ?? ""));
    } catch { setNarr(""); }
    finally { setNarLoading(false); }
  };

  // Helper to render the sidebar/panel content
  function renderPanelContent() {
    if (selectedZones.length >= 2) {
      return <AggregatePanel stats={aggregateStats} loading={aggLoading} t={t} />;
    }
    if (selected) {
      const selectedYearNdvi = ndviHistory.find(s => s.year === ndviYear)?.ndvi ?? selected.ndvi;
      return (
        <ZoneDetailPanel
          data={{ ...selected, ndvi: activeLayer === "ndvi" && ndviHistory.length > 0 ? selectedYearNdvi : selected.ndvi }}
          narrative={narrative}
          narLoading={narLoading}
        />
      );
    }
    return <EmptyZonePanel t={t} />;
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">

      {/* Toolbar */}
      <div className="px-5 py-2.5 border-b border-lira-border bg-lira-surface flex items-center gap-3 shrink-0 sm:flex-wrap">
        <div className="flex items-center gap-2">
          <Layers size={15} className="text-lira-green" />
          <span className="text-sm font-semibold text-slate-200">Spatial Analysis</span>
          <span className="text-xs text-lira-muted-aa">Omo-Ghibe Basin · Ethiopia</span>
        </div>
        <div className="flex gap-2 overflow-x-auto">
          {LAYER_OPTIONS.map(opt => (
            <button key={opt.id} onClick={() => setLayer(opt.id)} title={opt.desc}
              aria-pressed={activeLayer === opt.id}
              className={clsx("min-h-[44px] px-4 py-2 text-xs rounded border transition-all shrink-0",
                activeLayer === opt.id
                  ? "bg-lira-green text-white border-lira-green"
                  : "border-lira-border text-lira-muted-aa-aa hover:border-lira-green/50")}>
              {opt.label}
            </button>
          ))}
        </div>
        {selectedZones.length > 0 && (
          <button
            onClick={() => { setSelectedZones([]); setAggregateStats(null); }}
            className="min-h-[44px] px-3 py-2 text-xs rounded border border-lira-border text-lira-muted-aa hover:border-red-400/50 hover:text-red-400 transition-all shrink-0">
            {t("map.clearSelection")} ({selectedZones.length})
          </button>
        )}
        {activeLayer === "ndvi" && (
          <div className="flex items-center gap-2 ml-2 shrink-0">
            <label htmlFor="ndvi-year-slider" className="text-xs text-lira-muted-aa whitespace-nowrap">
              {t("map.ndviYear")}: <span className="text-slate-200 font-semibold">{ndviYear}</span>
            </label>
            <input
              id="ndvi-year-slider"
              type="range"
              min={2020}
              max={2025}
              step={1}
              value={ndviYear}
              aria-label={t("map.ndviSlider")}
              onChange={e => handleNdviYear(Number(e.target.value))}
              className="w-28 accent-lira-green"
            />
          </div>
        )}
        <button
          onClick={handleExportGeoTiff}
          disabled={exporting}
          className="min-h-[44px] px-3 py-2 text-xs rounded border border-lira-border text-lira-muted-aa hover:border-lira-green/50 hover:text-lira-green transition-all shrink-0 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5">
          {exporting ? <Activity size={12} className="animate-pulse" /> : null}
          {t("map.exportGeoTiff")}
        </button>
        {activeLayer === "lhii" && (
          <ul aria-label={t('map.legend')} className="ml-auto flex items-center gap-2 text-xs text-lira-muted-aa-aa flex-wrap">
            {Object.entries(LHII_COLORS).map(([k, c]) => (
              <li key={k} className="flex items-center gap-1">
                <span className="w-3 h-3 rounded-sm inline-block" style={{ background: c }} aria-hidden="true" />
                {k.replace(/_/g, " ")}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Map + panel */}
      <div className="flex flex-1 overflow-hidden min-h-0">

        {/* MAP area */}
        <div className="flex-1 relative min-h-0">
          {error ? (
            <div className="absolute inset-0 flex items-center justify-center bg-lira-bg/90 z-10">
              <div className="text-red-400 text-sm bg-red-900/20 border border-red-900/40 rounded-xl px-6 py-5 max-w-sm text-center">
                <AlertTriangle size={20} className="mx-auto mb-2" />
                <div className="font-medium mb-1">Failed to load map data</div>
                <div className="text-xs text-lira-muted-aa">{error}</div>
                <div className="text-xs text-lira-muted-aa mt-2">Ensure backend is running on port 8000</div>
              </div>
            </div>
          ) : !geojson ? (
            <div className="absolute inset-0 flex items-center justify-center bg-lira-bg">
              <div className="flex items-center gap-2 text-lira-muted-aa-aa text-sm">
                <Activity size={16} className="animate-pulse text-lira-green" />
                Loading spatial data…
              </div>
            </div>
          ) : (
            <div role="img" aria-label={t('map.leafletRegion')} className="absolute inset-0">
              <LeafletMap
                geojson={geojson as object}
                activeLayer={activeLayer}
                selectedZones={selectedZones}
                onZoneClick={(props) => {
                  setSelected(props);
                  setNdviHistory([]);
                  if (props.zone_id) loadNarrative(String(props.zone_id));
                }}
                onZoneShiftClick={handleZoneShiftClick}
              />
            </div>
          )}
        </div>

        {/* Desktop side panel — hidden below md */}
        <div role="complementary" aria-label={t('map.zoneDetail')} className="hidden md:block w-72 shrink-0 border-l border-lira-border bg-lira-surface overflow-y-auto">
          {renderPanelContent()}
        </div>
      </div>

      {/* Mobile BottomSheet — shown below md only (md:hidden via component) */}
      <BottomSheet open={true}>
        {renderPanelContent()}
      </BottomSheet>
    </div>
  );
}
