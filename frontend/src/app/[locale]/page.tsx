"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import {
  FlaskConical, CloudLightning, GitBranch, Sprout, Landmark,
  Database, Activity, Globe, ArrowRight, CheckCircle, Circle,
  TrendingDown, AlertTriangle, MapPin, BarChart2, Users, Zap
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const PIPELINE_STEPS = [
  { id: "evidence",   label: "Evidence Cloud",          icon: Database,       route: "/evidence",    desc: "Fetch Sentinel-2, DEM, SoilGrids, CHIRPS" },
  { id: "diagnosis",  label: "Landscape Diagnosis",     icon: FlaskConical,   route: "/diagnosis",   desc: "Classify 9 indicators → health score" },
  { id: "climate",    label: "Climate Futures",         icon: CloudLightning, route: "/climate",     desc: "CMIP6 SSP245/SSP585 risk projections" },
  { id: "syndromes",  label: "Syndromes & Causal Graph",icon: GitBranch,      route: "/syndromes",   desc: "Identify degradation syndrome + drivers" },
  { id: "pathways",   label: "Regeneration Pathways",   icon: Sprout,         route: "/pathways",    desc: "7 pathway packages matched to context" },
  { id: "investment", label: "Investment Passports",    icon: Landmark,       route: "/investment",  desc: "Finance-ready portfolios + priority index" },
  { id: "monitoring", label: "Monitoring & MELIA",      icon: Activity,       route: "/monitoring",  desc: "Before-after tracking + re-prescription" },
];

const OMO_ZONES = [
  { id: "highland",        name: "Kafa-Sheka Highland",    syndrome: "Deforestation", ndvi: "0.446", soc: "58.6", rain: "1859", color: "border-emerald-500/50 bg-emerald-900/10" },
  { id: "midland",         name: "Dawro-Wolayita Midland", syndrome: "Erosion-Productivity", ndvi: "0.283", soc: "43.1", rain: "1275", color: "border-yellow-500/50 bg-yellow-900/10" },
  { id: "lowland_pastoral",name: "South Omo Lowland",      syndrome: "Rangeland Overgrazing", ndvi: "0.111", soc: "28.2", rain: "760",  color: "border-orange-500/50 bg-orange-900/10" },
  { id: "riverine",        name: "Omo River Corridor",     syndrome: "Reservoir Sedimentation", ndvi: "0.101", soc: "67.9", rain: "686",  color: "border-blue-500/50 bg-blue-900/10"  },
];

const DATA_SOURCES = [
  { name: "SoilGrids v2.0",      status: "real",      value: "SOC 28–68 g/kg confirmed" },
  { name: "Sentinel-2 L2A",      status: "real",      value: "NDVI 0.10–0.45 confirmed" },
  { name: "Copernicus DEM",       status: "real",      value: "Elev 977–2194m confirmed" },
  { name: "ESA WorldCover 2021",  status: "real",      value: "Forest 2–62% confirmed" },
  { name: "MODIS MOD13Q1",        status: "real",      value: "LPI 0.49–0.87 confirmed" },
  { name: "CHIRPS v2.0",          status: "real",      value: "Rain 686–1859 mm/yr confirmed" },
  { name: "ERA5 / Open-Meteo",    status: "real",      value: "T 15–29°C confirmed" },
  { name: "NASA NEX GDDP CMIP6",  status: "real",      value: "SSP245/585 2030–2070" },
  { name: "CGIAR CGSpace",        status: "real",      value: "1,659+ Ethiopia results" },
];

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tc = useTranslations("common");
  const [sysStatus, setSysStatus] = useState<"loading"|"ok"|"error">("loading");
  const [routes, setRoutes]       = useState(0);
  const [agents, setAgents]       = useState<string[]>([]);

  useEffect(() => {
    fetch(`${API}/`)
      .then(r => r.json())
      .then(d => {
        setSysStatus("ok");
        setAgents(d.agents ?? []);
      })
      .catch(() => setSysStatus("error"));
    fetch(`${API}/openapi.json`)
      .then(r => r.json())
      .then(d => setRoutes(Object.keys(d.paths ?? {}).length))
      .catch(() => {});
  }, []);

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:justify-between items-start gap-4">
        <div>
          <div>
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
              <span className="text-lira-green">{t("title")}</span>
            </h1>
            <div className="text-sm font-medium text-slate-300 mt-0.5">
              {t("subtitle")}
            </div>
            <p className="text-lira-muted mt-0.5 text-xs">
              {t("tagline")}
            </p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${
            sysStatus === "ok" ? "border-lira-green/40 bg-lira-green/10 text-lira-green" :
            sysStatus === "error" ? "border-red-500/40 bg-red-900/20 text-red-400" :
            "border-lira-border text-lira-muted"
          }`}>
            <span className={`w-2 h-2 rounded-full ${sysStatus === "ok" ? "bg-lira-green animate-pulse" : "bg-lira-muted"}`} />
            {sysStatus === "ok" ? tc("apiOnline", { routes }) : sysStatus === "error" ? tc("apiOffline") : tc("apiConnecting")}
          </div>
          <Link href="/omo-ghibe"
            className="flex items-center gap-2 bg-lira-green text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-lira-green/80 transition">
            <Globe size={14} /> {tc("openOmoGhibe")}
          </Link>
        </div>
      </div>

      {/* Central shift banner */}
      <div className="bg-lira-surface border border-lira-green/20 rounded-xl p-5">
        <div className="flex items-start gap-4">
          <Zap size={20} className="text-lira-green mt-0.5 shrink-0" />
          <div>
            <div className="text-sm font-semibold text-slate-100 mb-1">{t("centralShift.heading")}</div>
            <div className="text-sm text-lira-muted leading-relaxed">
              From <span className="text-slate-300 italic">{t("centralShift.from")}</span> {t("centralShift.arrow")}{" "}
              <span className="text-lira-green font-medium">{t("centralShift.to")}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Three-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Pipeline steps */}
        <div className="col-span-2 bg-lira-surface border border-lira-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <BarChart2 size={16} className="text-lira-green" />
            <h2 className="text-sm font-semibold text-slate-200">{t("pipeline.heading")}</h2>
            <span className="ml-auto text-xs text-lira-muted">{t("pipeline.hint")}</span>
          </div>
          <div className="space-y-2">
            {PIPELINE_STEPS.map((step, i) => (
              <Link key={step.id} href={step.route}
                className="flex items-center gap-4 px-4 py-3 rounded-lg border border-lira-border/50 hover:border-lira-green/40 hover:bg-lira-green/5 transition group">
                <div className="flex items-center gap-3 flex-1">
                  <div className="w-6 h-6 rounded-full bg-lira-border/40 flex items-center justify-center text-[10px] text-lira-muted font-bold shrink-0">
                    {i + 1}
                  </div>
                  <step.icon size={15} className="text-lira-muted group-hover:text-lira-green shrink-0" />
                  <div>
                    <div className="text-sm font-medium text-slate-200">{step.label}</div>
                    <div className="text-xs text-lira-muted">{step.desc}</div>
                  </div>
                </div>
                <ArrowRight size={13} className="text-lira-border group-hover:text-lira-green" />
              </Link>
            ))}
          </div>
        </div>

        {/* Agents + data sources */}
        <div className="space-y-4">
          {/* Agent roster */}
          <div className="bg-lira-surface border border-lira-border rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <Users size={14} className="text-lira-sky" />
              <h3 className="text-xs font-semibold text-slate-200 uppercase tracking-wide">{t("agentRoster.heading")}</h3>
              <span className="ml-auto text-[10px] text-lira-muted">{agents.length} agents</span>
            </div>
            <div className="space-y-1 max-h-52 overflow-y-auto">
              {agents.length > 0 ? agents.map(a => (
                <div key={a} className="flex items-center gap-1.5 py-0.5">
                  <CheckCircle size={10} className="text-lira-green shrink-0" />
                  <span className="text-[11px] text-lira-muted">{a.replace("Agent","").replace(/([A-Z])/g," $1").trim()}</span>
                </div>
              )) : (
                <div className="text-xs text-lira-muted">{t("agentRoster.empty")}</div>
              )}
            </div>
          </div>

          {/* System stats */}
          <div className="bg-lira-surface border border-lira-border rounded-xl p-4">
            <h3 className="text-xs font-semibold text-slate-200 uppercase tracking-wide mb-3">{t("system.heading")}</h3>
            {[
              { label: t("system.apiRoutes"),   value: routes || "—" },
              { label: t("system.pythonFiles"), value: "51" },
              { label: t("system.tests"),       value: "16+ passing" },
              { label: t("system.epsg"),        value: "32637 (UTM 37N)" },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between py-1 border-b border-lira-border/30 last:border-0">
                <span className="text-[11px] text-lira-muted">{label}</span>
                <span className="text-[11px] text-lira-green font-medium">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Omo-Ghibe Basin */}
      <div className="bg-lira-surface border border-lira-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <MapPin size={16} className="text-lira-green" />
          <h2 className="text-sm font-semibold text-slate-200">{t("basin.heading")}</h2>
          <Link href="/omo-ghibe" className="ml-auto text-xs text-lira-sky hover:underline flex items-center gap-1">
            {t("basin.openLab")} <ArrowRight size={11} />
          </Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {OMO_ZONES.map(z => (
            <Link key={z.id} href={`/omo-ghibe`}
              className={`border rounded-xl p-4 hover:scale-[1.02] transition-transform ${z.color}`}>
              <div className="text-xs font-semibold text-slate-200 mb-2 leading-tight">{z.name}</div>
              <div className="text-[10px] text-lira-muted mb-3 italic">{z.syndrome}</div>
              <div className="space-y-1">
                {[
                  ["NDVI", z.ndvi],
                  ["SOC", `${z.soc} g/kg`],
                  ["Rain", `${z.rain} mm`],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-[10px] text-lira-muted">{k}</span>
                    <span className="text-[10px] text-slate-300 font-medium">{v}</span>
                  </div>
                ))}
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Data sources status */}
      <div className="bg-lira-surface border border-lira-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Database size={16} className="text-lira-sky" />
          <h2 className="text-sm font-semibold text-slate-200">{t("dataSources.heading")}</h2>
          <Link href="/climate-data" className="ml-auto text-xs text-lira-sky hover:underline">{t("dataSources.cmip6Link")}</Link>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {DATA_SOURCES.map(s => (
            <div key={s.name} className="flex items-start gap-2 bg-lira-bg border border-lira-border/40 rounded-lg px-3 py-2">
              <CheckCircle size={12} className="text-lira-green mt-0.5 shrink-0" />
              <div>
                <div className="text-[11px] font-medium text-slate-200">{s.name}</div>
                <div className="text-[10px] text-lira-muted">{s.value}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Action buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { href: "/setup",       label: tc("newProject"),    icon: FlaskConical,   color: "bg-lira-green hover:bg-lira-green/80 text-white" },
          { href: "/omo-ghibe",   label: tc("openOmoGhibe"),  icon: Globe,          color: "bg-lira-sky/20 border border-lira-sky/40 hover:bg-lira-sky/30 text-lira-sky" },
          { href: "/climate-data",label: t("dataSources.cmip6Link"), icon: CloudLightning, color: "bg-lira-surface border border-lira-border hover:border-lira-sky/40 text-slate-200" },
          { href: "/export",      label: tc("exportReport"),  icon: Activity,       color: "bg-lira-surface border border-lira-border hover:border-lira-green/40 text-slate-200" },
        ].map(({ href, label, icon: Icon, color }) => (
          <Link key={href} href={href}
            className={`flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-medium transition ${color}`}>
            <Icon size={15} /> {label}
          </Link>
        ))}
      </div>
    </div>
  );
}
