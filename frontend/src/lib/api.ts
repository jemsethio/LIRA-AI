const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${res.status}: ${err}`);
  }
  return res.json() as Promise<T>;
}

// Projects
export const createProject = (data: unknown) =>
  request("/projects/", { method: "POST", body: JSON.stringify(data) });

export const listProjects = () => request("/projects/");

export const getProject = (id: string) => request(`/projects/${id}`);

// Diagnosis
export const runDiagnosis = (indicators: unknown) =>
  request("/diagnosis/indicators", { method: "POST", body: JSON.stringify(indicators) });

export const classifySyndromes = (projectId: string) =>
  request(`/diagnosis/syndromes/${projectId}`, { method: "POST", body: "{}" });

export const getCausalGraph = (projectId: string) =>
  request(`/diagnosis/causal-graph/${projectId}`);

export const getDiagnostic = (projectId: string) =>
  request(`/diagnosis/indicators/${projectId}`);

export const getSyndromes = (projectId: string) =>
  request(`/diagnosis/syndromes/${projectId}`);

export const bootstrapSyndrome = (zoneId: "highland" | "midland" | "lowland_pastoral" | "riverine" = "highland") =>
  request(`/diagnosis/bootstrap/${zoneId}`, { method: "POST" });

// Climate  — scenario must match ClimateScenario enum: "RCP4.5"|"RCP8.5"|"SSP2-4.5"|"SSP5-8.5"|"mock_placeholder"
export const runClimateFutures = (projectId: string, indicators: unknown, scenario = "mock_placeholder", horizon = "2050") =>
  request(`/climate/${projectId}?scenario=${encodeURIComponent(scenario)}&horizon=${horizon}`, {
    method: "POST",
    body: JSON.stringify(indicators),
  });

export const getClimateReport = (projectId: string) =>
  request(`/climate/${projectId}`);

// Pathways — backend expects {"syndrome": {...}, "climate": null} (two body params → wrapper required)
export const generatePathways = (projectId: string, syndrome: unknown, climate?: unknown) =>
  request(`/pathways/${projectId}/generate`, {
    method: "POST",
    body: JSON.stringify({ syndrome, climate: climate ?? null }),
  });

export const getPathways = (projectId: string) =>
  request(`/pathways/${projectId}`);

export const runTradeoffs = (projectId: string, community?: unknown) =>
  request(`/pathways/${projectId}/tradeoffs`, {
    method: "POST",
    body: JSON.stringify(community ?? null),
  });

export const getTradeoffs = (projectId: string) =>
  request(`/pathways/${projectId}/tradeoffs`);

// Investment
export const createPassport = (projectId: string, data: unknown) =>
  request(`/investment/${projectId}/passport`, { method: "POST", body: JSON.stringify(data) });

export const listPassports = (projectId: string) =>
  request(`/investment/${projectId}/passports`);

// Community & Policy
export const saveCommunityIntelligence = (projectId: string, data: unknown) =>
  request(`/community/${projectId}/intelligence`, { method: "POST", body: JSON.stringify(data) });

export const getCommunityIntelligence = (projectId: string) =>
  request(`/community/${projectId}/intelligence`);

// Export
export const exportMarkdown = (bundle: unknown) =>
  fetch(`${BASE}/export/markdown`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bundle),
  }).then((r) => r.text());

export const exportJson = (bundle: unknown) =>
  request("/export/json", { method: "POST", body: JSON.stringify(bundle) });

// ── Agents (new) ──────────────────────────────────────────────────────────────
export const runCommunityAgent = (data: unknown) =>
  request("/agents/community-intelligence", { method: "POST", body: JSON.stringify(data) });

export const runPolicyAgent = (data: unknown) =>
  request("/agents/policy-alignment", { method: "POST", body: JSON.stringify(data) });

export const runInvestmentAgent = (data: unknown) =>
  request("/agents/investment-planning", { method: "POST", body: JSON.stringify(data) });

export const runCausalAgent = (data: unknown) =>
  request("/agents/causal-diagnosis", { method: "POST", body: JSON.stringify(data) });

export const runFullDiagnosis = (data: unknown) =>
  request("/agents/full-diagnosis", { method: "POST", body: JSON.stringify(data) });

export const getAgentRegistry = () => request("/agents/registry");

// ── RAG Knowledge Base (new) ──────────────────────────────────────────────────
export const getRagStatus = () => request("/rag/status");

export const ingestCGSpace = (data: { project_id: string; query: string; n_results: number; multi_query?: boolean }) =>
  request("/rag/ingest-cgspace", { method: "POST", body: JSON.stringify(data) });

export const ragRetrieve = (data: { project_id: string; query: string; n_results: number }) =>
  request("/rag/retrieve", { method: "POST", body: JSON.stringify(data) });

export const getRagCards = (projectId: string, query = "restoration intervention") =>
  request(`/rag/cards/${projectId}?query=${encodeURIComponent(query)}`);

// ── MCP Tools (new) ───────────────────────────────────────────────────────────
export const getMcpTools = () => request("/mcp/tools");

export const callMcpTool = (tool: string, inputs: Record<string, unknown>) =>
  request("/mcp/call", { method: "POST", body: JSON.stringify({ tool, inputs }) });

// ── Spatial helpers (plan 13-02) ──────────────────────────────────────────────
export async function fetchAggregateStats(zoneIds: string[]): Promise<Record<string, unknown>> {
  const r = await fetch(
    `${BASE}/spatial/zones/aggregate?zone_ids=${zoneIds.join(",")}`
  );
  if (!r.ok) throw new Error(`aggregate fetch failed: ${r.status}`);
  return r.json();
}

export async function fetchNdviHistory(
  zoneId: string,
  startYear: number,
  endYear: number
): Promise<{ year: number; ndvi: number }[]> {
  const r = await fetch(
    `${BASE}/spatial/zone/${zoneId}/ndvi-history?start_year=${startYear}&end_year=${endYear}`
  );
  if (!r.ok) throw new Error(`ndvi-history fetch failed: ${r.status}`);
  const d = await r.json() as { series?: { year: number; ndvi: number }[]; data?: { year: number; ndvi: number }[] };
  return d.series ?? d.data ?? [];
}

export async function fetchGeotiff(layer: string, zoneIds: string[]): Promise<Blob> {
  const zoneParam = zoneIds.join(",");
  const r = await fetch(
    `${BASE}/spatial/export/geotiff?layer=${layer}&zone_ids=${zoneParam}`
  );
  if (!r.ok) throw new Error(`GeoTIFF export failed: ${r.status}`);
  return r.blob();
}
