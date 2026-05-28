"use client";
import { useState, useEffect, useCallback } from "react";
import { set, del, entries, createStore } from "idb-keyval";

const queueStore = createStore("lira-queue", "mutations");

export interface QueuedMutation {
  id: string;
  endpoint: string;
  method: "POST" | "PUT" | "DELETE";
  body: unknown;
  label: string;
  timestamp: number;
  retries: number;
}

const ENDPOINT_LABELS: Record<string, string> = {
  "/diagnosis/indicators":          "Indicator run",
  "/diagnosis/syndromes/":          "Syndrome classification",
  "/pathways/":                     "Pathway generation",
  "/agents/community-intelligence": "Community note",
  "/rag/ingest":                    "Document upload",
};

function labelFor(endpoint: string): string {
  for (const [prefix, label] of Object.entries(ENDPOINT_LABELS)) {
    if (endpoint.startsWith(prefix)) return label;
  }
  return "Change";
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function useMutationQueue() {
  const [queue, setQueue] = useState<QueuedMutation[]>([]);
  const [syncing, setSyncing] = useState(false);

  // Load queue from IDB on mount
  useEffect(() => {
    entries<string, QueuedMutation>(queueStore).then((all) => {
      setQueue(all.map(([, v]) => v));
    });
  }, []);

  const enqueue = useCallback(
    async (
      endpoint: string,
      method: QueuedMutation["method"],
      body: unknown
    ) => {
      const mutation: QueuedMutation = {
        id: crypto.randomUUID(),
        endpoint,
        method,
        body,
        label: labelFor(endpoint),
        timestamp: Date.now(),
        retries: 0,
      };
      await set(mutation.id, mutation, queueStore);
      setQueue((prev) => [...prev, mutation]);
    },
    []
  );

  const discard = useCallback(async (id: string) => {
    await del(id, queueStore);
    setQueue((prev) => prev.filter((m) => m.id !== id));
  }, []);

  const drain = useCallback(async () => {
    if (syncing) return;
    const all = await entries<string, QueuedMutation>(queueStore);
    if (all.length === 0) return;

    setSyncing(true);
    for (const [key, mutation] of all) {
      try {
        const res = await fetch(`${API}${mutation.endpoint}`, {
          method: mutation.method,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(mutation.body),
        });
        if (res.ok) {
          await del(key, queueStore);
        } else {
          // Increment retries on non-ok response but keep in queue
          const updated: QueuedMutation = { ...mutation, retries: mutation.retries + 1 };
          await set(key, updated, queueStore);
        }
      } catch {
        // Network failure — increment retries and keep in queue
        const updated: QueuedMutation = { ...mutation, retries: mutation.retries + 1 };
        await set(key, updated, queueStore);
      }
    }

    // Re-read IDB as source of truth to prevent stale state divergence (Pitfall 3)
    const remaining = await entries<string, QueuedMutation>(queueStore);
    setQueue(remaining.map(([, v]) => v));
    setSyncing(false);
  }, [syncing]);

  // Auto-drain on reconnect
  useEffect(() => {
    window.addEventListener("online", drain);
    return () => {
      window.removeEventListener("online", drain);
    };
  }, [drain]);

  return {
    queue,
    syncing,
    pendingCount: queue.length,
    enqueue,
    discard,
    drain,
  };
}
