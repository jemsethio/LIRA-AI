"use client";

interface PDFGenerationSpinnerProps {
  label: string;
}

export function PDFGenerationSpinner({ label }: PDFGenerationSpinnerProps) {
  return (
    <div
      className="flex items-center gap-2 px-4 py-2 bg-lira-surface border border-lira-border text-lira-muted-aa rounded-lg text-sm min-h-[44px]"
      aria-live="polite"
      aria-label={label}
      role="status"
    >
      <div
        className="border-t-2 border-lira-green-aa rounded-full w-4 h-4 animate-spin flex-shrink-0"
        aria-hidden="true"
      />
      <span>{label}</span>
    </div>
  );
}
