"use client";
import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Card, MetricRow, SeverityBadge, AssumptionNote } from "@/components/ui/Card";
import { clsx } from "clsx";
import AIInsight from "@/components/ui/AIInsight";
import { MapPin, Database, Activity, Users, CheckCircle, XCircle } from "lucide-react";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";

const OMO_CACHE_KEY = "lira-omo-ghibe-last";

function formatRelativeTime(ms: number): string {
  const secs = Math.floor(ms / 1000);
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  return `${Math.floor(hrs / 24)} days ago`;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ZONE_COLORS: Record<string, string> = {
  highland:        "border-emerald-600/40 bg-emerald-900/5",
  midland:         "border-yellow-600/40 bg-yellow-900/5",
  lowland_pastoral:"border-orange-600/40 bg-orange-900/5",
  riverine:        "border-blue-600/40 bg-blue-900/5",
};

const SYNDROME_COLORS: Record<string, string> = {
  very_high: "text-red-400", high: "text-orange-400",
  medium: "text-yellow-400", low: "text-lira-green",
};

interface Zone {
  zone_id: string; zone_name: string; area_ha: number;
  dominant_syndrome: string; real_data_layers: number; bbox: number[];
}

interface Diagnosis {
  zone_name: string;
  diagnostic: Record<string, unknown>;
  syndromes: Record<string, unknown>;
  lhii: Record<string, unknown>;
  community_intelligence: Record<string, string | string[]>;
  data_quality: Record<string, unknown>;
}

export default function OmoGhibePage() {
  const t = useTranslations("omo");
  const { isOnline } = useOnlineStatus();

  const [zones, setZones]         = useState<Zone[]>([]);
  const [selected, setSelected]   = useState<string>("lowland_pastoral");
  const [diagnosis, setDiagnosis] = useState<Diagnosis | null>(null);
  const [loading, setLoading]     = useState(false);
  const [compareData, setCompare] = useState<Record<string, unknown> | null>(null);
  const [cacheAge, setCacheAge]   = useState<number | null>(null);

  useEffect(() => {
    fetch(`${API}/omo-ghibe/zones`)
      .then(r => r.json()).then(setZones).catch(console.error);

    fetch(`${API}/omo-ghibe/compare`)
      .then(r => r.json())
      .then((data) => {
        setCompare(data);
        // Cache the compare data for offline use
        try {
          localStorage.setItem(OMO_CACHE_KEY, JSON.stringify({
            compareData: data,
            cachedAt: Date.now(),
          }));
        } catch {
          // localStorage unavailable — non-fatal
        }
        setCacheAge(null);
      })
      .catch(() => {
        // On failure, try to load from localStorage cache
        try {
          const raw = localStorage.getItem(OMO_CACHE_KEY);
          if (raw) {
            const parsed = JSON.parse(raw) as { compareData: Record<string, unknown>; cachedAt: number };
            if (parsed.compareData) {
              setCompare(parsed.compareData);
              setCacheAge(Date.now() - parsed.cachedAt);
            }
          }
        } catch {
          // Corrupt cache — discard silently (T-09-03-01: parse failure handled)
        }
      });
  }, []);

  const runDiagnosis = async (zoneId: string) => {
    setLoading(true); setSelected(zoneId); setDiagnosis(null);
    try {
      const res = await fetch(`${API}/omo-ghibe/zones/${zoneId}/diagnose`, { method: "POST" });
      setDiagnosis(await res.json());
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  const diag    = diagnosis?.diagnostic as Record<string, unknown> | undefined;
  const synd    = diagnosis?.syndromes  as Record<string, unknown> | undefined;
  const lhii    = diagnosis?.lhii       as Record<string, unknown> | undefined;
  const primary = synd?.primary_syndrome as Record<string, unknown> | undefined;
  const comps   = lhii?.components      as Record<string, unknown>[] | undefined;
  const dq      = diagnosis?.data_quality as Record<string, unknown> | undefined;
  const ci      = diagnosis?.community_intelligence as Record<string, string | string[]> | undefined;

  const compareZones = compareData
    ? Object.entries((compareData as Record<string, unknown>).zones as Record<string, unknown>)
    : [];

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2 flex-wrap">
          <MapPin size={20} className="text-lira-green" />
          <h1 className="text-2xl font-bold text-slate-100">{t("title")}</h1>
          {cacheAge !== null && (
            <div
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium"
              style={{ background: "rgba(82,121,111,0.15)", color: "#52796f", border: "1px solid rgba(82,121,111,0.4)" }}
            >
              <span>Cached snapshot · {formatRelativeTime(cacheAge)}</span>
            </div>
          )}
        </div>
        <p className="text-lira-muted text-sm">
          Primary Ethiopia pilot landscape · CGIAR MFL, CASP · lon 33–42°E / lat 3–10°N · ~7.9 million ha
        </p>
        {!isOnline && cacheAge !== null && (
          <p className="text-xs text-amber-400 mt-1">
            Showing the last diagnostic saved on this device. New changes will sync when you reconnect.
          </p>
        )}
        <div className="flex gap-4 mt-2 text-xs text-lira-muted">
          <span className="flex items-center gap-1"><Database size={11} /> SoilGrids v2.0 (real)</span>
          <span className="flex items-center gap-1"><Database size={11} /> Sentinel-2 / Copernicus DEM / ESA WorldCover</span>
          <span className="flex items-center gap-1"><Database size={11} /> CHIRPS rainfall / ERA5</span>
        </div>
      </div>

      {/* Zone selector cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {zones.map((z) => (
          <button key={z.zone_id} onClick={() => runDiagnosis(z.zone_id)}
            className={clsx("text-left rounded-xl border p-4 transition-all hover:scale-[1.02]",
              ZONE_COLORS[z.zone_id] ?? "",
              selected === z.zone_id ? "ring-2 ring-lira-green" : "")}>
            <div className="text-sm font-semibold text-slate-100 mb-1">{z.zone_name}</div>
            <div className="text-xs text-lira-muted mb-2">{(z.area_ha / 1000).toFixed(0)}k ha</div>
            <div className="text-xs text-lira-muted">{z.dominant_syndrome.replace(/_/g, " ")}</div>
            <div className="flex items-center gap-1 mt-2">
              {z.real_data_layers > 0
                ? <CheckCircle size={11} className="text-lira-green" />
                : <XCircle size={11} className="text-lira-muted" />}
              <span className="text-[10px] text-lira-muted">{z.real_data_layers}/5 real layers</span>
            </div>
          </button>
        ))}
      </div>

      {/* Basin comparison table */}
      {compareZones.length > 0 && (
        <Card title="Basin-Wide Indicator Comparison" className="mb-8">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-lira-border">
                  <th className="text-left py-2 px-3 text-lira-muted font-medium">Zone</th>
                  {["ndvi_mean","soil_organic_carbon_g_per_kg","soil_loss_rate_t_ha_yr",
                    "rainfall_mm_annual","overgrazing_proxy","forest_cover_pct"].map(k => (
                    <th key={k} className="text-right py-2 px-3 text-lira-muted font-medium">
                      {k.replace(/_/g," ").replace("g per kg","g/kg").slice(0,18)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {compareZones.map(([zid, zdata]) => {
                  const z = zdata as Record<string, unknown>;
                  if (!z.zone_name) return null;
                  return (
                    <tr key={zid} className={clsx("border-b border-lira-border/30",
                      selected === zid ? "bg-lira-green/5" : "")}>
                      <td className="py-2 px-3 text-slate-200 font-medium">{String(z.zone_name).split("(")[0].trim()}</td>
                      {["ndvi_mean","soil_organic_carbon_g_per_kg","soil_loss_rate_t_ha_yr",
                        "rainfall_mm_annual","overgrazing_proxy","forest_cover_pct"].map(k => (
                        <td key={k} className="py-2 px-3 text-right text-slate-300">
                          {z[k] != null ? Number(z[k]).toFixed(k.includes("annual") ? 0 : 2) : "—"}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="text-[10px] text-lira-muted mt-2">
            SOC values from real SoilGrids v2.0 · NDVI from eco-profile (PC connection pending EPSG fix)
          </p>
        </Card>
      )}

      {/* Diagnosis results */}
      {loading && (
        <div className="text-center py-12 text-lira-muted">
          <Activity size={24} className="mx-auto mb-3 animate-pulse text-lira-green" />
          Running LIRA-AI diagnosis pipeline…
        </div>
      )}

      {diagnosis && !loading && (
        <>
          <div className="text-sm font-semibold text-slate-100 mb-5">
            Diagnosis: {diagnosis.zone_name}
          </div>

          {/* Summary row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {[
              { label: "Degradation", value: <SeverityBadge level={String(diag?.degradation_severity ?? "")} /> },
              { label: "Health Score", value: `${Math.round((diag?.composite_health_score as number ?? 0)*100)}%` },
              { label: "LHII Score",   value: `${lhii?.overall_lhii ?? "—"} (${lhii?.lhii_class ?? ""})` },
              { label: "Primary Syndrome", value: <span className="text-xs text-orange-400">{String(primary?.name ?? "").split(" ").slice(0,3).join(" ")}</span> },
            ].map(({label, value}) => (
              <div key={label} className="bg-lira-surface border border-lira-border rounded-xl p-4">
                <div className="text-xs text-lira-muted mb-2">{label}</div>
                <div className="text-sm font-semibold text-slate-100">{value}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
            {/* LHII Components */}
            <Card title="Landscape Health Index (LHII)">
              {comps?.map((c) => (
                <div key={String(c.name)} className="flex justify-between items-center py-1.5 border-b border-lira-border/30 last:border-0">
                  <span className="text-xs text-lira-muted">{String(c.name).replace(/_/g," ")}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 bg-lira-border rounded-full h-1.5">
                      <div className="h-1.5 rounded-full bg-lira-green"
                        style={{width: `${Math.round((c.score as number)*100)}%`}} />
                    </div>
                    <span className="text-xs text-slate-200 w-8 text-right">{Math.round((c.score as number)*100)}%</span>
                  </div>
                </div>
              ))}
              <div className="mt-3 text-xs text-lira-muted">
                Dominant constraint: <span className="text-yellow-400">{String(lhii?.dominant_constraint ?? "")}</span>
              </div>
            </Card>

            {/* Syndrome */}
            <Card title="Syndrome Diagnosis">
              <div className="text-sm font-semibold text-slate-100 mb-2">{String(primary?.name ?? "")}</div>
              <div className="flex gap-2 mb-3">
                <SeverityBadge level={String(primary?.risk_level ?? "")} />
                <span className="text-xs text-lira-muted">
                  Confidence: {String(primary?.confidence ?? "")} · {Math.round((primary?.match_score as number ?? 0)*100)}% match
                </span>
              </div>
              <div className="text-xs font-medium text-lira-muted uppercase mb-1">Likely Drivers</div>
              {(primary?.likely_drivers as string[] ?? []).slice(0,4).map((d) => (
                <div key={d} className="text-xs text-slate-300 flex gap-2 mb-1">
                  <span className="text-yellow-400">▸</span>{d}
                </div>
              ))}
              <div className="text-xs font-medium text-lira-muted uppercase mt-3 mb-1">Main Symptoms</div>
              {(primary?.main_symptoms as string[] ?? []).slice(0,3).map((s) => (
                <div key={s} className="text-xs text-slate-300 flex gap-2 mb-1">
                  <span className="text-red-400">▸</span>{s}
                </div>
              ))}
            </Card>

            {/* Real data status */}
            <Card title="Data Source Status">
              {dq && Object.entries(dq).filter(([k]) => k.startsWith("real_")).map(([k, v]) => (
                <div key={k} className="flex justify-between items-center py-1.5 border-b border-lira-border/30 last:border-0">
                  <span className="text-xs text-lira-muted">{k.replace("real_","").replace(/_/g," ")}</span>
                  {v
                    ? <CheckCircle size={12} className="text-lira-green" />
                    : <XCircle size={12} className="text-lira-muted" />}
                </div>
              ))}
              {dq && (
                <div className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1">
                  {[
                    ["SOC g/kg", dq.soilgrids_soc_g_per_kg],
                    ["Clay %",   dq.soilgrids_clay_pct],
                    ["pH",       dq.soilgrids_ph],
                    ["S2 scenes",dq.n_sentinel2_scenes],
                  ].map(([label, val]) => val != null && (
                    <div key={String(label)} className="text-[10px] text-lira-muted">
                      {String(label)}: <span className="text-lira-green">{String(val)}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* AI Zone Narrative */}
          {diagnosis && (
            <AIInsight
              narrativeType="syndrome"
              label="Summary"
              autoLoad={true}
              context={{
                zone_name:           diagnosis.zone_name,
                syndrome_name:       primary?.name,
                degradation_severity: (diag as Record<string,unknown>)?.degradation_severity,
                lhii_score:          lhii?.overall_lhii,
                lhii_class:          lhii?.lhii_class,
                drivers:             primary?.likely_drivers ?? [],
                symptoms:            primary?.main_symptoms  ?? [],
              }}
              className="mb-6"
            />
          )}

          {/* Community intelligence */}
          {ci && (
            <Card title="Community Intelligence" badge="Field validated" badgeColor="bg-purple-900/30 text-purple-400">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div>
                  {[
                    ["Preferred future", ci.community_preferred_future],
                    ["Degradation memory", ci.local_degradation_memory],
                    ["Grazing rules", ci.grazing_rules],
                    ["Conflict risks", ci.local_conflict_risks],
                  ].map(([label, val]) => (
                    <div key={String(label)} className="mb-3">
                      <div className="text-[10px] font-medium text-lira-muted uppercase mb-1">{label}</div>
                      <div className="text-xs text-slate-300 leading-relaxed">{String(val ?? "")}</div>
                    </div>
                  ))}
                </div>
                <div>
                  <div className="text-[10px] font-medium text-lira-muted uppercase mb-2">Restoration Preferences</div>
                  {(ci.restoration_preferences as string[] ?? []).map((p) => (
                    <div key={p} className="text-xs text-lira-green flex gap-1.5 mb-1"><span>✓</span>{p}</div>
                  ))}
                  <div className="text-[10px] font-medium text-lira-muted uppercase mt-3 mb-2">Adoption Barriers</div>
                  {(ci.adoption_barriers as string[] ?? []).map((b) => (
                    <div key={b} className="text-xs text-orange-300 flex gap-1.5 mb-1"><span>!</span>{b}</div>
                  ))}
                  <div className="text-[10px] font-medium text-lira-muted uppercase mt-3 mb-2">Equity Notes</div>
                  <div className="text-xs text-slate-300">{String(ci.gendered_burdens ?? "")}</div>
                </div>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
