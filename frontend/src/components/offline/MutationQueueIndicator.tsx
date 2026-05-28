"use client";
import { useState } from "react";
import { Clock, RefreshCw, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";
import { TouchableRow } from "@/components/ui/TouchableRow";
import type { QueuedMutation } from "@/hooks/useMutationQueue";

interface MutationQueueIndicatorProps {
  queue: QueuedMutation[];
  syncing: boolean;
  onDiscard: (id: string) => void;
  onRetry: () => void;
}

function formatRelativeTime(ms: number): string {
  const secs = Math.floor(ms / 1000);
  if (secs < 60) return "just now";
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  return `${Math.floor(hrs / 24)} days ago`;
}

export function MutationQueueIndicator({
  queue,
  syncing,
  onDiscard,
  onRetry,
}: MutationQueueIndicatorProps) {
  const [expanded, setExpanded] = useState(false);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  if (queue.length === 0) return null;

  const pendingCount = queue.length;
  const failedCount = queue.filter((m) => m.retries > 0).length;

  return (
    <div className="border border-lira-border rounded-xl overflow-hidden text-sm">
      {/* Summary row */}
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full min-h-[44px] flex items-center gap-2 px-4 py-2.5 hover:bg-white/5 transition-colors"
      >
        {syncing ? (
          <RefreshCw size={14} className="shrink-0 animate-spin text-lira-sky" />
        ) : failedCount > 0 ? (
          <AlertTriangle size={14} className="shrink-0 text-red-400" />
        ) : (
          <Clock size={14} className="shrink-0 text-amber-400" />
        )}

        <span className="flex-1 text-left text-slate-200">
          {syncing
            ? `Syncing ${pendingCount} ${pendingCount === 1 ? "change" : "changes"}…`
            : `${pendingCount} ${pendingCount === 1 ? "change" : "changes"} queued`}
          {failedCount > 0 && !syncing && (
            <span className="ml-2 text-xs text-red-400">· {failedCount} failed</span>
          )}
        </span>

        {!syncing && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onRetry();
            }}
            className="text-xs text-lira-sky hover:underline min-h-[44px] px-2 flex items-center"
            aria-label="Retry syncing queued changes"
          >
            Retry now
          </button>
        )}

        {expanded ? (
          <ChevronUp size={14} className="text-lira-muted shrink-0" />
        ) : (
          <ChevronDown size={14} className="text-lira-muted shrink-0" />
        )}
      </button>

      {/* Expanded list */}
      {expanded && (
        <div className="border-t border-lira-border divide-y divide-lira-border/40">
          {queue.map((item) => {
            const isFailed = item.retries > 0;
            const isConfirming = confirmId === item.id;

            return (
              <div key={item.id} className="px-2 py-1">
                {isConfirming ? (
                  /* Confirm discard */
                  <div className="min-h-[44px] flex items-center gap-2 px-2 py-2">
                    <span className="flex-1 text-xs text-slate-300">
                      Discard this change?
                    </span>
                    <button
                      type="button"
                      onClick={() => setConfirmId(null)}
                      className="min-h-[44px] px-3 text-xs text-lira-muted hover:text-slate-200"
                    >
                      Keep
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        onDiscard(item.id);
                        setConfirmId(null);
                      }}
                      className="min-h-[44px] px-3 text-xs text-red-400 hover:text-red-300"
                    >
                      Discard
                    </button>
                  </div>
                ) : (
                  <TouchableRow
                    label={item.label}
                    subLabel={formatRelativeTime(Date.now() - item.timestamp)}
                    icon={
                      syncing ? (
                        <RefreshCw size={14} className="animate-spin text-lira-sky" />
                      ) : isFailed ? (
                        <AlertTriangle size={14} className="text-red-400" />
                      ) : (
                        <Clock size={14} className="text-amber-400" />
                      )
                    }
                    trailing={
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={onRetry}
                          className="min-h-[44px] min-w-[44px] text-xs text-lira-sky hover:underline px-2 flex items-center justify-center"
                          aria-label={`Retry ${item.label}`}
                        >
                          Retry
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmId(item.id)}
                          className="min-h-[44px] min-w-[44px] text-xs text-red-400 hover:text-red-300 px-2 flex items-center justify-center"
                          aria-label={`Discard ${item.label}`}
                        >
                          Discard
                        </button>
                      </div>
                    }
                  />
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default MutationQueueIndicator;
