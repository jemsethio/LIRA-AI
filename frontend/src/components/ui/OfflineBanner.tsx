"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { WifiOff, RefreshCw, AlertTriangle, Clock } from "lucide-react";
import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { useMutationQueue } from "@/hooks/useMutationQueue";

type BannerState = "offline-idle" | "offline-queued" | "reconnecting" | "sync-failed";

const BANNER_STYLES: Record<BannerState, { bg: string; border: string; text: string }> = {
  "offline-idle":   { bg: "rgba(224,122,47,0.12)", border: "rgba(224,122,47,0.4)",  text: "#e07a2f" },
  "offline-queued": { bg: "rgba(224,122,47,0.16)", border: "rgba(224,122,47,0.5)",  text: "#e07a2f" },
  "reconnecting":   { bg: "rgba(26,117,159,0.14)", border: "rgba(26,117,159,0.45)", text: "#1a759f" },
  "sync-failed":    { bg: "rgba(193,18,31,0.14)",  border: "rgba(193,18,31,0.45)",  text: "#c1121f" },
};

export default function OfflineBanner() {
  const { isOnline } = useOnlineStatus();
  const { queue, syncing, pendingCount, drain } = useMutationQueue();

  // SSR-safe: initialize to true to match server render, update on mount
  const [mounted, setMounted] = useState(false);
  const [syncFailed, setSyncFailed] = useState(false);
  const prevOnlineRef = useRef(true);

  useEffect(() => {
    setMounted(true);
  }, []);

  // Stable drain-and-check callback
  const drainAndCheck = useCallback(() => {
    drain().then(() => {
      // queue state updated by useMutationQueue after drain
      // syncFailed will be set in the pendingCount+isOnline watcher below
    }).catch(() => {
      setSyncFailed(true);
    });
  }, [drain]);

  // When going from offline -> online, call drain()
  useEffect(() => {
    if (!mounted) return;
    const wasOffline = !prevOnlineRef.current;
    prevOnlineRef.current = isOnline;

    if (isOnline && wasOffline && pendingCount > 0) {
      drainAndCheck();
    }
  }, [isOnline, mounted, drainAndCheck, pendingCount]);

  // Watch for sync completion to detect failures
  useEffect(() => {
    if (!mounted) return;
    // If we're online, not syncing, and queue still has items with retries > 0 → sync failed
    if (isOnline && !syncing && queue.some((m) => m.retries > 0)) {
      setSyncFailed(true);
    }
    // Reset when everything is clear
    if (isOnline && pendingCount === 0) {
      setSyncFailed(false);
    }
  }, [isOnline, syncing, queue, pendingCount, mounted]);

  // Determine banner state
  if (!mounted || (isOnline && pendingCount === 0 && !syncFailed)) return null;

  let state: BannerState;
  if (syncing) {
    state = "reconnecting";
  } else if (!isOnline && pendingCount > 0) {
    state = "offline-queued";
  } else if (!isOnline) {
    state = "offline-idle";
  } else if (syncFailed) {
    state = "sync-failed";
  } else {
    state = "offline-idle";
  }

  const styles = BANNER_STYLES[state];
  const failedItems = queue.filter((m) => m.retries > 0);

  return (
    <div
      role="status"
      aria-live="polite"
      className="sticky top-0 z-50 min-h-[44px] px-4 py-2 flex items-center gap-3 border-b text-sm"
      style={{
        background: styles.bg,
        borderColor: styles.border,
        color: styles.text,
      }}
    >
      {state === "offline-idle" && (
        <>
          <WifiOff size={16} className="shrink-0" aria-hidden="true" />
          <span className="flex-1">Offline — showing cached data</span>
          <button
            onClick={drain}
            disabled={syncing}
            className="ml-auto text-sm font-medium min-h-[44px] min-w-[44px] flex items-center justify-center px-3 disabled:opacity-50"
            style={{ color: styles.text }}
            aria-label="Retry connection"
          >
            Retry now
          </button>
        </>
      )}

      {state === "offline-queued" && (
        <>
          <WifiOff size={16} className="shrink-0" aria-hidden="true" />
          <Clock size={14} className="shrink-0" aria-hidden="true" />
          <span className="flex-1">
            Offline — {pendingCount} {pendingCount === 1 ? "change" : "changes"} queued
          </span>
        </>
      )}

      {state === "reconnecting" && (
        <>
          <RefreshCw size={16} className="shrink-0 animate-spin" aria-hidden="true" />
          <span className="flex-1">
            {pendingCount > 0
              ? `Syncing ${pendingCount} ${pendingCount === 1 ? "change" : "changes"}…`
              : "Reconnecting…"}
          </span>
        </>
      )}

      {state === "sync-failed" && (
        <>
          <AlertTriangle size={16} className="shrink-0" aria-hidden="true" />
          <span className="flex-1">
            Sync failed — {failedItems.length} of {queue.length}{" "}
            {queue.length === 1 ? "change" : "changes"} could not be saved.
          </span>
          <button
            onClick={drain}
            disabled={syncing}
            className="ml-auto text-sm font-medium min-h-[44px] min-w-[44px] flex items-center justify-center px-3 disabled:opacity-50"
            style={{ color: styles.text }}
            aria-label="Review queue and retry"
          >
            Retry now
          </button>
        </>
      )}
    </div>
  );
}
