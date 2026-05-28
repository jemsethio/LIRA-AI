"use client";
import { useState, useEffect, useRef } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const HEARTBEAT_INTERVAL = 30_000; // 30 s — acceptable battery trade-off for field use

export function useOnlineStatus() {
  // Initialize to true — matches server-side default, avoids hydration mismatch
  const [isOnline, setIsOnline] = useState(true);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  const checkConnectivity = async () => {
    try {
      const res = await fetch(`${API}/health/ready`, {
        method: "GET",
        cache: "no-store",
        signal: AbortSignal.timeout(4000),
      });
      setIsOnline(res.ok);
    } catch {
      setIsOnline(false);
    }
  };

  useEffect(() => {
    // Layer 1 + 2: DOM events for immediate state changes
    const goOnline = () => {
      setIsOnline(true);
      // Also trigger a heartbeat on reconnect to confirm backend reachability
      checkConnectivity();
    };
    const goOffline = () => setIsOnline(false);

    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);

    // Layer 3: 30 s heartbeat (catches captive portals and backend-down scenarios)
    heartbeatRef.current = setInterval(checkConnectivity, HEARTBEAT_INTERVAL);

    // Initial check on mount (runs after hydration)
    checkConnectivity();

    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
      clearInterval(heartbeatRef.current);
    };
  }, []); // checkConnectivity is defined in this scope and doesn't need to be a dep

  return { isOnline };
}
