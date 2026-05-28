"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { getRagStatus, ingestCGSpace, ragRetrieve, getRagCards } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { clsx } from "clsx";
import { BookOpen, Search, Database, Upload, FileText, CheckCircle } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function KnowledgeContent() {
  const params    = useSearchParams();
  const projectId = params.get("project") ?? "MOCK-ETH-001";

  const [status,       setStatus]       = useState<Record<string,unknown> | null>(null);
  const [searchQuery,  setSearchQuery]  = useState("Ethiopia landscape restoration soil erosion");
  const [searchResult, setSearchResult] = useState<Record<string,unknown>[] | null>(null);
  const [cards,        setCards]        = useState<Record<string,unknown>[] | null>(null);
  const [ingestQuery,  setIngestQuery]  = useState("Ethiopia Omo-Ghibe landscape restoration degradation");
  const [ingestN,      setIngestN]      = useState(20);
  const [loading,      setLoading]      = useState<string | null>(null);
  const [message,      setMessage]      = useState("");
  const [uploadFile,   setUploadFile]   = useState<File | null>(null);

  useEffect(() => {
    getRagStatus().then(d => setStatus(d as Record<string,unknown>)).catch(() => null);
  }, []);

  const handleIngest = async () => {
    setLoading("ingest"); setMessage("");
    try {
      const r = await ingestCGSpace({ project_id: projectId, query: ingestQuery, n_results: ingestN, multi_query: true } as Parameters<typeof ingestCGSpace>[0]) as Record<string,unknown>;
      setMessage(`✓ ${r.message}`);
      getRagStatus().then(d => setStatus(d as Record<string,unknown>)).catch(() => null);
    } catch (e) { setMessage(`Error: ${e}`); }
    finally { setLoading(null); }
  };

  const handleSearch = async () => {
    setLoading("search"); setSearchResult(null);
    try {
      const r = await ragRetrieve({ project_id: projectId, query: searchQuery, n_results: 8 }) as Record<string,unknown>;
      setSearchResult(r.results as Record<string,unknown>[]);
    } catch (e) { setMessage(`Error: ${e}`); }
    finally { setLoading(null); }
  };

  const handleCards = async () => {
    setLoading("cards"); setCards(null);
    try {
      const r = await getRagCards(projectId, searchQuery) as Record<string,unknown>;
      setCards(r.cards as Record<string,unknown>[]);
    } catch (e) { setMessage(`Error: ${e}`); }
    finally { setLoading(null); }
  };

  const handleUpload = async () => {
    if (!uploadFile) return;
    setLoading("upload"); setMessage("");
    const form = new FormData();
    form.append("project_id", projectId);
    form.append("source_label", uploadFile.name.replace(/\.[^.]+$/, ""));
    form.append("file", uploadFile);
    try {
      const res = await fetch(`${API}/rag/ingest`, { method: "POST", body: form });
      const d   = await res.json() as Record<string,unknown>;
      setMessage(`✓ Indexed ${d.n_chunks} chunks from '${d.filename}'`);
      getRagStatus().then(d2 => setStatus(d2 as Record<string,unknown>)).catch(() => null);
    } catch (e) { setMessage(`Upload error: ${e}`); }
    finally { setLoading(null); }
  };

  return (
    <div className="p-4 md:p-6 lg:p-8 max-w-6xl mx-auto">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <BookOpen size={20} className="text-lira-green" />
          <h1 className="text-2xl font-bold text-slate-100">RAG Knowledge Base</h1>
        </div>
        <p className="text-lira-muted text-sm">
          Index restoration manuals, policy documents, and CGIAR evidence for AI-grounded recommendations
        </p>
      </div>

      {message && (
        <div className="bg-lira-green/10 border border-lira-green/30 rounded-xl p-3 mb-6 text-lira-green text-sm flex items-center gap-2">
          <CheckCircle size={14} />{message}
        </div>
      )}

      {/* Status */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        <div className="bg-lira-surface border border-lira-border rounded-xl p-4">
          <div className="text-xs text-lira-muted mb-1">Knowledge Base Status</div>
          <div className={`text-sm font-semibold ${status?.status==="ready"?"text-lira-green":"text-yellow-400"}`}>
            {String(status?.status ?? "loading")}
          </div>
        </div>
        <div className="bg-lira-surface border border-lira-border rounded-xl p-4">
          <div className="text-xs text-lira-muted mb-1">Total Indexed Chunks</div>
          <div className="text-lg font-bold text-slate-100">{String(status?.total_chunks ?? "—")}</div>
        </div>
        <div className="bg-lira-surface border border-lira-border rounded-xl p-4">
          <div className="text-xs text-lira-muted mb-1">Vector Store</div>
          <div className="text-sm text-lira-muted">ChromaDB + sentence-transformers</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Auto-ingest CGSpace */}
        <Card title="Auto-Ingest CGIAR CGSpace">
          <p className="text-xs text-lira-muted mb-4 leading-relaxed">
            Search CGIAR's institutional repository and automatically index relevant abstracts
            into the project knowledge base.
          </p>
          <div className="space-y-3">
            <div>
              <label className="text-[10px] text-lira-muted uppercase mb-1 block">Search query</label>
              <input value={ingestQuery} onChange={e => setIngestQuery(e.target.value)}
                className="w-full bg-lira-bg border border-lira-border rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-lira-green/60" />
            </div>
            <div>
              <label className="text-[10px] text-lira-muted uppercase mb-1 block">Max documents</label>
              <input type="number" value={ingestN} min={1} max={50}
                onChange={e => setIngestN(Number(e.target.value))}
                className="w-24 bg-lira-bg border border-lira-border rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none" />
            </div>
            <button onClick={handleIngest} disabled={loading==="ingest"}
              className="w-full bg-lira-green text-white py-2 rounded-lg text-xs font-medium hover:bg-lira-green/80 disabled:opacity-50">
              {loading==="ingest" ? "Ingesting…" : "Ingest from CGSpace"}
            </button>
          </div>
        </Card>

        {/* Upload document */}
        <Card title="Upload Document">
          <p className="text-xs text-lira-muted mb-4 leading-relaxed">
            Upload a PDF, DOCX, TXT, or Markdown file (restoration manuals, policy docs, field reports).
          </p>
          <div className="space-y-3">
            <div className={clsx("border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition",
              uploadFile ? "border-lira-green/40 bg-lira-green/5" : "border-lira-border hover:border-lira-green/30")}>
              <input type="file" accept=".pdf,.docx,.txt,.md"
                onChange={e => setUploadFile(e.target.files?.[0] || null)}
                className="hidden" id="file-upload" />
              <label htmlFor="file-upload" className="cursor-pointer">
                <Upload size={20} className="mx-auto mb-2 text-lira-muted" />
                <p className="text-xs text-lira-muted">
                  {uploadFile ? uploadFile.name : "Click to select PDF, DOCX, TXT, MD"}
                </p>
              </label>
            </div>
            <button onClick={handleUpload} disabled={!uploadFile || loading==="upload"}
              className="w-full bg-lira-sky/20 border border-lira-sky/40 text-lira-sky py-2 rounded-lg text-xs font-medium hover:bg-lira-sky/30 disabled:opacity-50">
              {loading==="upload" ? "Indexing…" : "Upload & Index"}
            </button>
          </div>
        </Card>
      </div>

      {/* Semantic search */}
      <Card title="Semantic Search" className="mb-6">
        <div className="flex gap-3 mb-4">
          <input value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            placeholder="e.g. soil bund construction Ethiopia slopes"
            className="flex-1 bg-lira-bg border border-lira-border rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-lira-green/60" />
          <button onClick={handleSearch} disabled={loading==="search"}
            className="flex items-center gap-1.5 px-4 py-2 bg-lira-surface border border-lira-border text-slate-200 rounded-lg text-xs hover:border-lira-green/40 disabled:opacity-50">
            <Search size={12} />
            {loading==="search" ? "Searching…" : "Search"}
          </button>
          <button onClick={handleCards} disabled={loading==="cards"}
            className="flex items-center gap-1.5 px-4 py-2 bg-lira-surface border border-lira-border text-lira-sky rounded-lg text-xs hover:border-lira-sky/40 disabled:opacity-50">
            <FileText size={12} />
            {loading==="cards" ? "Extracting…" : "Extract Cards"}
          </button>
        </div>

        {/* Search results */}
        {searchResult && (
          <div className="space-y-2">
            {searchResult.length === 0 ? (
              <p className="text-xs text-lira-muted italic">No results — ingest documents first</p>
            ) : searchResult.map((r, i) => (
              <div key={i} className="bg-lira-bg border border-lira-border/40 rounded-lg p-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[10px] text-lira-muted">{String(r.source ?? "")}</span>
                  <span className="text-[10px] bg-lira-green/20 text-lira-green px-2 py-0.5 rounded-full">
                    {Math.round((r.score as number ?? 0)*100)}% match
                  </span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed line-clamp-3">{String(r.text ?? "")}</p>
              </div>
            ))}
          </div>
        )}

        {/* Restoration option cards */}
        {cards && (
          <div className="mt-4">
            <div className="text-xs font-medium text-lira-muted uppercase mb-3">
              Extracted Restoration Option Cards ({cards.length})
            </div>
            {cards.length === 0 ? (
              <p className="text-xs text-lira-muted italic">No restoration options detected — try different query or ingest more documents</p>
            ) : (
              <div className="grid gap-3">
                {cards.map((c, i) => (
                  <div key={i} className="bg-lira-bg border border-lira-border/40 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-slate-100">{String(c.option_name ?? "")}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded font-medium ${
                        c.confidence_level==="high"?"bg-lira-green/20 text-lira-green":
                        c.confidence_level==="medium"?"bg-yellow-900/30 text-yellow-400":
                        "bg-lira-border/30 text-lira-muted"}`}>
                        {String(c.confidence_level)}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-[10px] text-lira-muted">
                      <div>Slope: {String(c.slope_range ?? "N/A")}</div>
                      <div>Rainfall: {String(c.rainfall_range ?? "N/A")}</div>
                    </div>
                    {(c.benefits as string[] ?? []).length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {(c.benefits as string[]).slice(0,2).map((b: string) => (
                          <span key={b} className="text-[10px] bg-lira-green/10 text-lira-green border border-lira-green/20 px-2 py-0.5 rounded">{b}</span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}

export default function KnowledgePage() {
  return <Suspense fallback={<div className="p-8 text-lira-muted">Loading…</div>}><KnowledgeContent /></Suspense>;
}
