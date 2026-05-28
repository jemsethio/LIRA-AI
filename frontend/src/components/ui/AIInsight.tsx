"use client";
/**
 * AIInsight — reusable AI summary component.
 * Generates concise, data-grounded, academic-practical summaries.
 * Provider: Ollama → Groq → HuggingFace → template fallback.
 * No Regenerate button — one authoritative summary per context.
 */
import { useState, useEffect, useCallback } from "react";
import { clsx } from "clsx";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface AIInsightProps {
  narrativeType: string;
  context:       Record<string, unknown>;
  autoLoad?:     boolean;   // auto-generate on mount
  label?:        string;    // defaults to "Summary"
  className?:    string;
  compact?:      boolean;
}

interface NarrateResult {
  text:      string | null;
  provider:  string;
  model:     string | null;
  is_llm:    boolean;
  latency_s: number;
}

export default function AIInsight({
  narrativeType,
  context,
  autoLoad = false,
  label = "Summary",
  className,
  compact = false,
}: AIInsightProps) {
  const [result,  setResult]  = useState<NarrateResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState("");

  const generate = useCallback(async () => {
    if (loading) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API}/ai/narrate`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          narrative_type: narrativeType,
          context,
          max_wait: 60,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setResult(await res.json() as NarrateResult);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [narrativeType, JSON.stringify(context)]);

  useEffect(() => {
    if (autoLoad && Object.keys(context).length > 0) {
      generate();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoLoad, narrativeType]);

  return (
    <div className={clsx(
      "rounded-lg border border-lira-border/40 bg-lira-bg/60",
      compact ? "p-3" : "p-4",
      className,
    )}>
      {/* Header row */}
      <div className="flex items-center gap-2 mb-2">
        {/* Spark icon */}
        <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"
          className="text-lira-sky shrink-0 opacity-80">
          <path d="M12 2l2.4 6.6L21 11l-6.6 2.4L12 20l-2.4-6.6L3 11l6.6-2.4z"/>
        </svg>
        <span className={clsx(
          "font-semibold text-slate-300 tracking-wide uppercase",
          compact ? "text-[9px]" : "text-[10px]",
        )}>
          {label}
        </span>

        {/* Provider chip — only shown when a result exists */}
        {result?.is_llm && (
          <span className="ml-1 text-[9px] text-lira-muted opacity-60">
            {result.provider}{result.model ? ` · ${result.model}` : ""}
          </span>
        )}

        {/* Generate button — only when no result yet and not loading */}
        {!result && !loading && (
          <button
            onClick={generate}
            className={clsx(
              "ml-auto flex items-center gap-1 text-lira-sky hover:text-slate-200 transition-colors",
              compact ? "text-[10px]" : "text-xs",
            )}
          >
            <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Generate
          </button>
        )}
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-1.5 animate-pulse">
          {[100, 92, 96, 80, 88].map(w => (
            <div key={w} className="h-1.5 bg-lira-border/30 rounded"
              style={{ width: `${w}%` }} />
          ))}
          <p className="text-[10px] text-lira-muted mt-1 opacity-60">
            Generating summary…
          </p>
        </div>
      ) : error ? (
        <p className="text-red-400 text-[11px]">{error}</p>
      ) : result?.text ? (
        <p className={clsx(
          "text-slate-300 leading-relaxed",
          compact ? "text-[11px]" : "text-xs",
        )}>
          {result.text}
        </p>
      ) : (
        <p className={clsx(
          "text-lira-muted italic",
          compact ? "text-[10px]" : "text-[11px]",
        )}>
          Click <span className="text-lira-sky not-italic">Generate</span> for an
          evidence-grounded summary.
        </p>
      )}
    </div>
  );
}
