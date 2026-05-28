"use client";
/**
 * LeafletMap — Leaflet loaded imperatively via useEffect.
 * No react-leaflet. Pure Leaflet JS API — avoids ALL react-leaflet SSR issues.
 * Works reliably with Next.js 15 / React 18 StrictMode.
 */
import { useEffect, useRef } from "react";

const LHII_COLORS: Record<string, string> = {
  severely_degraded: "#c1121f",
  degraded:          "#e07a2f",
  fair:              "#e9c46a",
  good:              "#52796f",
  excellent:         "#2d6a4f",
};

const SYNDROME_COLORS: Record<string, string> = {
  deforestation_vegetation_loss: "#264653",
  erosion_productivity_decline:  "#e07a2f",
  rangeland_overgrazing:         "#c1121f",
  reservoir_sedimentation:       "#1a759f",
  moisture_stress:               "#e9c46a",
  mixed_high_risk:               "#9b2226",
};

function valueColor(v: number, lo: number, hi: number, reverse = false): string {
  const t = Math.max(0, Math.min(1, (v - lo) / (hi - lo)));
  const p = reverse ? 1 - t : t;
  if (p < 0.25) return "#2d6a4f";
  if (p < 0.50) return "#52796f";
  if (p < 0.75) return "#e9c46a";
  if (p < 0.90) return "#e07a2f";
  return "#c1121f";
}

function getColor(props: Record<string, unknown>, layer: string): string {
  switch (layer) {
    case "lhii":      return LHII_COLORS[String(props.lhii_class ?? "fair")] ?? "#e9c46a";
    case "syndrome":  return SYNDROME_COLORS[String(props.syndrome_id ?? "")] ?? "#7a9ab0";
    case "ndvi":      return valueColor(Number(props.ndvi ?? 0.3), 0.05, 0.65);
    case "soil_loss": return valueColor(Number(props.soil_loss_t_ha_yr ?? 20), 2, 100, true);
    case "rainfall":  return valueColor(Number(props.rainfall_mm ?? 800), 300, 2000);
    default:          return "#52796f";
  }
}

interface Props {
  geojson:          object;
  activeLayer:      string;
  onZoneClick:      (props: Record<string, unknown>) => void;
  selectedZones:    string[];
  onZoneShiftClick: (zoneId: string) => void;
}

export default function LeafletMap({ geojson, activeLayer, onZoneClick, selectedZones, onZoneShiftClick }: Props) {
  const containerRef     = useRef<HTMLDivElement>(null);
  const mapRef           = useRef<unknown>(null);
  const layerRef         = useRef<unknown>(null);
  const selectedZonesRef = useRef<string[]>([]);

  // Sync selectedZonesRef whenever selectedZones changes — no map/layer redraw
  useEffect(() => {
    selectedZonesRef.current = selectedZones;
  }, [selectedZones]);

  // Initialize map once on mount
  useEffect(() => {
    if (!containerRef.current) return;

    // Dynamically import Leaflet (browser-only)
    import("leaflet").then((L) => {
      // Inject Leaflet CSS if not already present
      if (!document.querySelector('link[href*="leaflet"]')) {
        const link = document.createElement("link");
        link.rel  = "stylesheet";
        link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
        document.head.appendChild(link);
      }

      // Fix default marker icons
      const iconProto = L.Icon.Default.prototype as unknown as Record<string, unknown>;
      delete iconProto._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
        iconUrl:       "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
        shadowUrl:     "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
      });

      // If container already has a map, remove it first
      const el = containerRef.current!;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      if ((el as any)._leaflet_id) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (mapRef.current as any)?.remove?.();
      }

      // Create map
      const map = L.map(el, {
        center: [6.5, 37.0],
        zoom:   7,
        zoomControl: false,
      });
      mapRef.current = map;

      // Controls
      L.control.zoom({ position: "bottomright" }).addTo(map);
      L.control.scale({ position: "bottomleft", imperial: false }).addTo(map);

      // Dark basemap
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        attribution: "&copy; CARTO",
        maxZoom: 19,
      }).addTo(map);

      // Add GeoJSON
      addGeoJSON(L, map, geojson, activeLayer, onZoneClick, onZoneShiftClick);
    });

    // Cleanup on unmount
    return () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (mapRef.current as any)?.remove?.();
      mapRef.current  = null;
      layerRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run once — map stays alive

  // Update layer colours when activeLayer changes (no map recreate)
  useEffect(() => {
    if (!mapRef.current) return;
    import("leaflet").then((L) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const map = mapRef.current as any;
      // Remove old GeoJSON layer
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      if (layerRef.current) map.removeLayer(layerRef.current as any);
      addGeoJSON(L, map, geojson, activeLayer, onZoneClick, onZoneShiftClick);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeLayer, geojson]);

  return (
    <div
      ref={containerRef}
      style={{ height: "100%", width: "100%", background: "#0f1923" }}
    />
  );

  // ── helpers ──────────────────────────────────────────────────────────────
  function addGeoJSON(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    L: any, map: any, data: object, layer: string,
    onClick: (p: Record<string, unknown>) => void,
    onShiftClick: (zoneId: string) => void
  ) {
    const geoLayer = L.geoJSON(data, {
      style: (feature: { properties: Record<string, unknown> }) => ({
        fillColor:   getColor(feature.properties ?? {}, layer),
        fillOpacity: 0.65,
        color:       "#0f1923",
        weight:      2,
        opacity:     0.9,
      }),
      onEachFeature: (
        feature: { properties: Record<string, unknown> },
        fl:      unknown
      ) => {
        const p = feature.properties ?? {};
        // Only bind clicks to enriched zone features (have lhii_score)
        if (!p.lhii_score) return;

        const featureLayer = fl as any; // eslint-disable-line @typescript-eslint/no-explicit-any
        const zoneId = String(p.zone_id ?? "");

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        featureLayer.on({
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          click: (e: any) => {
            if (e.originalEvent && e.originalEvent.shiftKey) {
              // Shift-click: toggle zone in multi-selection
              onShiftClick(zoneId);
              // After state → ref cycle completes, update visual style
              setTimeout(() => {
                if (selectedZonesRef.current.includes(zoneId)) {
                  featureLayer.setStyle({ color: "#ffffff", weight: 3, dashArray: "6 4", fillOpacity: 0.75 });
                } else {
                  featureLayer.setStyle({ color: "#0f1923", weight: 2, dashArray: "", fillOpacity: 0.65 });
                }
              }, 50);
            } else {
              // Plain click: single-zone selection
              onClick(p);
              // After state → ref cycle completes, update visual style
              setTimeout(() => {
                if (selectedZonesRef.current.includes(zoneId)) {
                  featureLayer.setStyle({ color: "#ffffff", weight: 3, dashArray: "6 4", fillOpacity: 0.75 });
                } else {
                  featureLayer.setStyle({ color: "#0f1923", weight: 2, dashArray: "", fillOpacity: 0.65 });
                }
              }, 50);
            }
          },
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          mouseover: (e: any) => e.target.setStyle({ weight: 3, fillOpacity: 0.85 }),
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          mouseout:  (e: any) => {
            // Preserve selected style on mouseout
            if (selectedZonesRef.current.includes(zoneId)) {
              e.target.setStyle({ color: "#ffffff", weight: 3, dashArray: "6 4", fillOpacity: 0.75 });
            } else {
              e.target.setStyle({ color: "#0f1923", weight: 2, dashArray: "", fillOpacity: 0.65 });
            }
          },
        });

        // Tooltip
        const displayName = p.zone_name || p.name || p.zone || "Zone";
        featureLayer.bindTooltip(
          `<b>${displayName}</b><br>LHII: ${Number(p.lhii_score ?? 0).toFixed(3)}<br>${p.syndrome_name ?? ""}`,
          { sticky: true, className: "lira-tooltip" }
        );
      },
    }).addTo(map);

    layerRef.current = geoLayer;
  }
}
