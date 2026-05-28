"use client";

import React from "react";
import { PDFGenerationSpinner } from "./PDFGenerationSpinner";

interface DownloadButtonProps {
  label: string;
  onClick: () => Promise<void>;
  isLoading: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
}

export function DownloadButton({
  label,
  onClick,
  isLoading,
  disabled,
  icon,
}: DownloadButtonProps) {
  if (isLoading) {
    return <PDFGenerationSpinner label={label} />;
  }

  return (
    <button
      onClick={onClick}
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      aria-label={label}
      className="flex items-center gap-2 px-4 py-2 bg-lira-green text-white rounded-lg text-sm font-medium min-h-[44px] hover:bg-lira-green/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#9db8cc] focus-visible:ring-offset-2 focus-visible:ring-offset-lira-bg"
    >
      {icon && (
        <span aria-hidden="true" className="flex-shrink-0">
          {icon}
        </span>
      )}
      {label}
    </button>
  );
}
