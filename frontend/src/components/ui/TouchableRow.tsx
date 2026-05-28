"use client";
import React from "react";
import Link from "next/link";
import { clsx } from "clsx";

interface TouchableRowProps {
  as?: "button" | "link";
  href?: string;
  onClick?: () => void;
  icon?: React.ReactNode;
  label: string;
  subLabel?: string;
  trailing?: React.ReactNode;
  className?: string;
  disabled?: boolean;
}

const BASE_CLASSES =
  "min-h-[44px] flex items-center gap-3 px-4 py-3 rounded-lg transition-colors w-full text-left " +
  "hover:bg-white/5 active:bg-white/10 " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lira-green focus-visible:ring-offset-2 focus-visible:ring-offset-lira-bg";

const DISABLED_CLASSES = "opacity-50 pointer-events-none";

function RowContent({
  icon,
  label,
  subLabel,
  trailing,
}: {
  icon?: React.ReactNode;
  label: string;
  subLabel?: string;
  trailing?: React.ReactNode;
}) {
  return (
    <>
      {icon && (
        <span className="shrink-0 text-lira-muted" style={{ width: 20, height: 20, display: "flex", alignItems: "center" }}>
          {icon}
        </span>
      )}
      <span className="flex-1 flex flex-col min-w-0">
        <span className="text-sm text-slate-200 truncate">{label}</span>
        {subLabel && (
          <span className="text-xs text-lira-muted-aa truncate mt-0.5">{subLabel}</span>
        )}
      </span>
      {trailing && <span className="shrink-0">{trailing}</span>}
    </>
  );
}

export function TouchableRow({
  as = "button",
  href,
  onClick,
  icon,
  label,
  subLabel,
  trailing,
  className,
  disabled = false,
}: TouchableRowProps) {
  const combinedClass = clsx(BASE_CLASSES, disabled && DISABLED_CLASSES, className);

  if (as === "link" && href) {
    return (
      <Link href={href} className={combinedClass} aria-disabled={disabled}>
        <RowContent icon={icon} label={label} subLabel={subLabel} trailing={trailing} />
      </Link>
    );
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className={combinedClass}
    >
      <RowContent icon={icon} label={label} subLabel={subLabel} trailing={trailing} />
    </button>
  );
}

export default TouchableRow;
