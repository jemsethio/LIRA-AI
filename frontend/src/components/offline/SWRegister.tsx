"use client";
import { useEffect } from "react";

export default function SWRegister() {
  useEffect(() => {
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("/sw.js", { scope: "/" })
        .then((reg) => {
          // Listen for SW update and notify user (UI-SPEC: "A newer version is available. Reload")
          reg.addEventListener("updatefound", () => {
            const newSW = reg.installing;
            if (!newSW) return;
            newSW.addEventListener("statechange", () => {
              if (newSW.state === "installed" && navigator.serviceWorker.controller) {
                // Post a message or dispatch a custom event; Plan 09-03 wires the toast UI
                window.dispatchEvent(new CustomEvent("sw-update-available"));
              }
            });
          });
        })
        .catch(console.error);
    }
  }, []);
  return null;
}
