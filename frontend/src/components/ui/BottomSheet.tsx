"use client";
import { useState, useRef } from "react";
import { useTranslations } from "next-intl";

type SnapPoint = "peek" | "half" | "full";

const SNAP_Y: Record<SnapPoint, string> = {
  peek: "calc(100% - 88px)",
  half: "50vh",
  full: "8vh",
};

const SNAP_ORDER: SnapPoint[] = ["peek", "half", "full"];

interface BottomSheetProps {
  children: React.ReactNode;
  open: boolean;
}

export function BottomSheet({ children, open }: BottomSheetProps) {
  const t = useTranslations();
  const [snap, setSnap] = useState<SnapPoint>("peek");
  const dragStartY = useRef<number | null>(null);

  if (!open) return null;

  const cycleSnap = () => {
    const idx = SNAP_ORDER.indexOf(snap);
    setSnap(SNAP_ORDER[(idx + 1) % SNAP_ORDER.length]);
  };

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    dragStartY.current = e.clientY;
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (dragStartY.current === null) return;
    const delta = e.clientY - dragStartY.current;
    dragStartY.current = null;
    const idx = SNAP_ORDER.indexOf(snap);
    if (delta > 60 && idx > 0) {
      // dragged down — go down one level (less expanded)
      setSnap(SNAP_ORDER[idx - 1]);
    } else if (delta < -60 && idx < SNAP_ORDER.length - 1) {
      // dragged up — go up one level (more expanded)
      setSnap(SNAP_ORDER[idx + 1]);
    }
  };

  return (
    <>
      {/* Backdrop scrim at full state only */}
      {snap === "full" && (
        <div
          className="fixed inset-0 z-20 bg-black/40 md:hidden"
          onClick={() => setSnap("half")}
          aria-hidden="true"
        />
      )}

      {/* Sheet — pointer-events-none on container so Leaflet map receives touch events in peek state */}
      <div
        role="region"
        aria-label={t('map.zoneDetail')}
        className="fixed inset-x-0 bottom-0 z-30 bg-lira-surface border-t border-lira-border rounded-t-2xl shadow-2xl transition-transform duration-300 ease-out md:hidden pointer-events-none"
        style={{ height: "92vh", transform: `translateY(${SNAP_Y[snap]})` }}
      >
        {/* Drag handle — re-enables pointer events */}
        <div
          role="button"
          aria-label={t('map.bottomSheet.handle')}
          className="h-[44px] flex items-center justify-center cursor-grab active:cursor-grabbing pointer-events-auto"
          onClick={cycleSnap}
          onPointerDown={handlePointerDown}
          onPointerUp={handlePointerUp}
        >
          <div className="w-8 h-1 rounded-full bg-lira-border/70" />
        </div>

        {/* Scrollable body — re-enables pointer events */}
        <div
          className="overflow-y-auto pb-[env(safe-area-inset-bottom)] pointer-events-auto"
          style={{ height: "calc(100% - 44px)" }}
        >
          {children}
        </div>
      </div>
    </>
  );
}
