"use client";
import { useState, useEffect } from "react";
import { getMcpTools, callMcpTool } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { clsx } from "clsx";
import { Cpu, Play, ChevronDown, ChevronRight } from "lucide-react";

interface MCPTool {
  name:        string;
  description: string;
  inputs:      string[];
}

const EXAMPLE_INPUTS: Record<string, Record<string, unknown>> = {
  diagnose_landscape:   { project_id: "demo", ndvi_mean: 0.28, soil_loss_rate_t_ha_yr: 32.5, rainfall_mm_annual: 1275, overgrazing_proxy: 0.55 },
  compute_rusle:        { rainfall_mm: 1859, slope_deg: 9.8, ndvi: 0.446, forest_cover_pct: 61.7, soil_texture: "clay" },
  fetch_soilgrids:      { lon: 36.35, lat: 7.90 },
  fetch_sentinel2_ndvi: { west: 36.1, south: 7.6, east: 36.4, north: 7.9, date_range: "2022-06-01/2023-10-31" },
  get_climate_risk:     { scenario: "ssp245", horizon: 2050, model: "MIROC6" },
  search_cgspace:       { query: "Omo-Ghibe Ethiopia landscape restoration", n_results: 5 },
  retrieve_rag:         { project_id: "demo", query: "soil bunds Ethiopia", n_results: 3 },
  generate_pathways:    { project_id: "demo", primary_syndrome: "Erosion-Productivity Decline", degradation_severity: "severe" },
  get_zone_data:        { zone_id: "highland" },
  narrate_summary:      { narrative_type: "lhii", context: '{"zone_name":"Kafa-Sheka Highland","lhii_score":0.743,"lhii_class":"good","dominant_constraint":"climate risk","recovery_potential":"high","hotspots":[],"green_spots":[]}' },
};

export default function McpToolsPage() {
  const [tools,    setTools]    = useState<MCPTool[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [inputs,   setInputs]   = useState<string>("");
  const [result,   setResult]   = useState<unknown>(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    getMcpTools().then(d => setTools((d as Record<string,unknown>).tools as MCPTool[])).catch(() => null);
  }, []);

  const selectTool = (name: string) => {
    setSelected(name);
    setResult(null); setError("");
    const ex = EXAMPLE_INPUTS[name] ?? {};
    setInputs(JSON.stringify(ex, null, 2));
  };

  const run = async () => {
    if (!selected) return;
    setLoading(true); setResult(null); setError("");
    try {
      const parsedInputs = JSON.parse(inputs);
      const r = await callMcpTool(selected, parsedInputs) as Record<string,unknown>;
      setResult(r.result);
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Cpu size={20} className="text-lira-sky" />
          <h1 className="text-2xl font-bold text-slate-100">MCP Tool Explorer</h1>
        </div>
        <p className="text-lira-muted text-sm">
          10 scientific tools exposed via Model Context Protocol — call any tool directly or via an AI agent
        </p>
        <div className="mt-2 text-xs text-lira-muted">
          Standalone server: <code className="bg-lira-surface px-2 py-0.5 rounded text-lira-sky">python -m app.mcp.server</code>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Tool list */}
        <div className="space-y-1.5">
          <div className="text-[10px] font-semibold text-lira-muted uppercase tracking-wide mb-3">
            Available Tools ({tools.length})
          </div>
          {tools.map((t) => (
            <button key={t.name} onClick={() => { selectTool(t.name); setExpanded(t.name); }}
              className={clsx("w-full text-left px-3 py-2.5 rounded-lg text-xs transition-all border",
                selected === t.name
                  ? "bg-lira-sky/10 border-lira-sky/40 text-slate-200"
                  : "border-lira-border/40 text-lira-muted hover:border-lira-sky/30 hover:text-slate-200")}>
              <div className="font-medium">{t.name}</div>
              <div className="text-[10px] opacity-60 mt-0.5 line-clamp-1">{t.description}</div>
            </button>
          ))}
        </div>

        {/* Tool runner */}
        <div className="col-span-2 space-y-4">
          {selected ? (
            <>
              <Card title={selected} badge="MCP Tool" badgeColor="bg-lira-sky/20 text-lira-sky">
                <p className="text-xs text-lira-muted mb-3">
                  {tools.find(t => t.name === selected)?.description}
                </p>
                <div className="text-[10px] text-lira-muted mb-2 uppercase">Inputs (JSON)</div>
                <textarea
                  value={inputs}
                  onChange={e => setInputs(e.target.value)}
                  rows={8}
                  className="w-full bg-lira-bg border border-lira-border rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-lira-sky/60 resize-none"
                />
                <button onClick={run} disabled={loading}
                  className="flex items-center gap-2 mt-3 px-4 py-2 bg-lira-sky text-white rounded-lg text-xs font-medium hover:bg-lira-sky/80 disabled:opacity-50">
                  <Play size={12} />
                  {loading ? "Running…" : "Run Tool"}
                </button>
              </Card>

              {/* Result */}
              {error && (
                <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-4 text-red-400 text-xs">{error}</div>
              )}
              {result && (
                <Card title="Result">
                  <pre className="text-[11px] text-slate-300 font-mono overflow-auto max-h-80 whitespace-pre-wrap leading-relaxed">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </Card>
              )}
            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-64 text-center text-lira-muted">
              <Cpu size={32} className="mb-3 text-lira-border" />
              <p className="text-sm font-medium text-slate-300 mb-1">Select a tool</p>
              <p className="text-xs">Click any tool on the left to run it with example inputs</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
