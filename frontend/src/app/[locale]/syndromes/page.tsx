"use client";
import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import { getSyndromes, getCausalGraph, getDiagnostic, runCausalAgent } from "@/lib/api";
import { Card, SeverityBadge, AssumptionNote } from "@/components/ui/Card";
import AIInsight from "@/components/ui/AIInsight";

// Dynamic import prevents ReactFlow SSR crash (it accesses window on load)
const ReactFlow    = dynamic(() => import("reactflow").then(m => m.default),    { ssr: false });
const Background   = dynamic(() => import("reactflow").then(m => m.Background), { ssr: false });
const Controls     = dynamic(() => import("reactflow").then(m => m.Controls),   { ssr: false });
const MiniMap      = dynamic(() => import("reactflow").then(m => m.MiniMap),    { ssr: false });

const NODE_COLOR: Record<string, string> = {
  driver:       "#1a759f",
  process:      "#52796f",
  impact:       "#c1121f",
  intervention: "#2d6a4f",
};

function SyndromesContent() {
  const params = useSearchParams();
  const projectId = params.get("project") ?? "MOCK-ETH-001";
  const [syndrome,    setSyndrome]    = useState<Record<string, unknown> | null>(null);
  const [graph,       setGraph]       = useState<Record<string, unknown> | null>(null);
  const [causalAgent, setCausalAgent] = useState<Record<string, unknown> | null>(null);
  const [error,       setError]       = useState("");

  useEffect(() => {
    getSyndromes(projectId)
      .then((d) => setSyndrome(d as Record<string, unknown>))
      .catch((e) => setError(String(e)));
    getCausalGraph(projectId)
      .then((d) => setGraph(d as Record<string, unknown>))
      .catch(() => null);
    // Run Causal Diagnosis Agent for richer analysis
    getDiagnostic(projectId).then((diag) =>
      runCausalAgent({ project_id: projectId, diagnostic: diag })
        .then((r) => setCausalAgent(r as Record<string, unknown>))
        .catch(() => null)
    ).catch(() => null);
  }, [projectId]);

  // Convert causal graph to ReactFlow format
  const rfNodes = graph
    ? (graph.nodes as Array<{ id: string; label: string; type: string }>).map((n, i) => ({
        id: n.id,
        data: { label: n.label },
        position: { x: (i % 6) * 180, y: Math.floor(i / 6) * 100 },
        style: {
          background: NODE_COLOR[n.type] ?? "#2a3f52",
          color: "#fff",
          border: "1px solid #2a3f52",
          borderRadius: 8,
          fontSize: 10,
          padding: "4px 8px",
        },
      }))
    : [];

  const rfEdges = graph
    ? (graph.edges as Array<{ source: string; target: string }>).map((e, i) => ({
        id: `e-${i}`,
        source: e.source,
        target: e.target,
        style: { stroke: "#52796f", strokeWidth: 1.5 },
        animated: false,
      }))
    : [];

  const primary = syndrome?.primary_syndrome as Record<string, unknown> | undefined;

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-100 mb-1">Degradation Syndromes</h1>
      <p className="text-lira-muted text-sm mb-8">Project: {projectId}</p>

      {error && !syndrome && (
        <div className="bg-red-900/20 border border-red-900/40 rounded-xl p-4 mb-6 text-red-400 text-sm">
          {error} — Run indicator diagnosis first from the Landscape Diagnosis page.
        </div>
      )}

      {syndrome && (
        <>
          {/* Primary syndrome */}
          <Card
            title="Primary Syndrome"
            badge={String(primary?.risk_level ?? "")}
            badgeColor="bg-red-900/30 text-red-400"
            className="mb-6"
          >
            <div className="text-lg font-semibold text-slate-100 mb-1">{String(primary?.name ?? "")}</div>
            <div className="flex items-center gap-3 mb-4">
              <SeverityBadge level={String(primary?.risk_level ?? "")} />
              <span className="text-xs text-lira-muted">
                Confidence: {String(primary?.confidence ?? "")} · Match: {Math.round((primary?.match_score as number ?? 0) * 100)}%
              </span>
            </div>
            <p className="text-sm text-lira-muted mb-3">{String(syndrome.causal_narrative ?? "")}</p>

            <AIInsight
              narrativeType="syndrome"
              label="Summary"
              autoLoad={true}
              context={{
                zone_name:           projectId,
                syndrome_name:       primary?.name,
                degradation_severity: "moderate",
                lhii_score:          0.5,
                lhii_class:          "fair",
                drivers:             primary?.likely_drivers ?? [],
                symptoms:            primary?.main_symptoms  ?? [],
              }}
              className="mb-4"
            />

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <div className="text-xs font-medium text-lira-muted uppercase mb-2">Main Symptoms</div>
                <ul className="space-y-1">
                  {(primary?.main_symptoms as string[] ?? []).map((s) => (
                    <li key={s} className="text-sm text-slate-300 flex items-start gap-2">
                      <span className="text-red-400 mt-0.5">▸</span>{s}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <div className="text-xs font-medium text-lira-muted uppercase mb-2">Likely Drivers</div>
                <ul className="space-y-1">
                  {(primary?.likely_drivers as string[] ?? []).map((d) => (
                    <li key={d} className="text-sm text-slate-300 flex items-start gap-2">
                      <span className="text-yellow-400 mt-0.5">▸</span>{d}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Card>

          {/* Causal Diagnosis Agent — driver interactions + feedback loops */}
          {causalAgent && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-6">
              <Card title="Driver Interactions">
                {(causalAgent.driver_interactions as Record<string,unknown>[] ?? []).map((di, i) => (
                  <div key={i} className="border-b border-lira-border/30 last:border-0 py-2">
                    <div className="text-xs font-medium text-slate-200">
                      {String(di.driver_a).replace(/_/g," ")}
                      <span className={`mx-1.5 text-[10px] px-1.5 py-0.5 rounded ${
                        di.interaction==="reinforcing"?"bg-red-900/30 text-red-400":
                        di.interaction==="dampening" ?"bg-lira-green/20 text-lira-green":
                        "bg-yellow-900/30 text-yellow-400"}`}>
                        {String(di.interaction)}
                      </span>
                      {String(di.driver_b).replace(/_/g," ")}
                    </div>
                    <div className="text-[10px] text-lira-muted mt-0.5">{String(di.evidence)}</div>
                  </div>
                ))}
              </Card>
              <Card title="Feedback Loops">
                {(causalAgent.feedback_loops as string[] ?? []).map((loop: string, i: number) => (
                  <div key={i} className="text-[11px] text-orange-300 border-l-2 border-orange-500/40 pl-2 py-1.5 mb-2 leading-relaxed">
                    {loop}
                  </div>
                ))}
              </Card>
            </div>
          )}

          {/* Secondary syndromes */}
          {(syndrome.secondary_syndromes as Record<string, unknown>[] ?? []).length > 0 && (
            <Card title="Secondary Syndromes" className="mb-6">
              <div className="grid gap-4">
                {(syndrome.secondary_syndromes as Record<string, unknown>[]).map((s) => (
                  <div key={String(s.syndrome_id)} className="border border-lira-border rounded-lg p-4">
                    <div className="flex items-center gap-3 mb-1">
                      <span className="text-sm font-medium text-slate-200">{String(s.name)}</span>
                      <SeverityBadge level={String(s.risk_level)} />
                    </div>
                    <div className="flex flex-wrap gap-1.5 mt-2">
                      {(s.main_symptoms as string[] ?? []).slice(0, 3).map((sym) => (
                        <span key={sym} className="text-xs bg-lira-border/40 text-slate-300 px-2 py-0.5 rounded">{sym}</span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Causal graph */}
          {rfNodes.length > 0 && (
            <Card title="Causal Futures Graph" className="mb-6">
              <div className="flex gap-4 mb-3 flex-wrap">
                {Object.entries(NODE_COLOR).map(([type, color]) => (
                  <div key={type} className="flex items-center gap-1.5 text-xs text-lira-muted">
                    <div className="w-3 h-3 rounded" style={{ background: color }} />
                    {type}
                  </div>
                ))}
              </div>
              <div className="h-96 rounded-xl overflow-hidden border border-lira-border">
                <ReactFlow nodes={rfNodes} edges={rfEdges} fitView>
                  <Background color="#2a3f52" gap={20} />
                  <Controls style={{ background: "#1a2634", border: "1px solid #2a3f52" }} />
                  <MiniMap style={{ background: "#1a2634" }} nodeColor={(n) => (n.style?.background as string) ?? "#2a3f52"} />
                </ReactFlow>
              </div>
            </Card>
          )}

          {/* Validation needs */}
          {(syndrome.needs_validation as string[] ?? []).length > 0 && (
            <Card title="Field Validation Required">
              {(syndrome.needs_validation as string[]).map((v) => (
                <AssumptionNote key={v} text={`NEEDS VALIDATION: ${v}`} />
              ))}
            </Card>
          )}
        </>
      )}
    </div>
  );
}

export default function SyndromesPage() {
  return <Suspense fallback={<div className="p-8 text-lira-muted">Loading...</div>}><SyndromesContent /></Suspense>;
}
