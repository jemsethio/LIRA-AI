import { clsx } from "clsx";

interface CardProps {
  title?: string;
  badge?: string;
  badgeColor?: string;
  children: React.ReactNode;
  className?: string;
}

export function Card({ title, badge, badgeColor = "bg-lira-green/20 text-lira-green", children, className }: CardProps) {
  return (
    <div className={clsx("bg-lira-surface border border-lira-border rounded-xl p-5", className)}>
      {title && (
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
          {badge && (
            <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium", badgeColor)}>
              {badge}
            </span>
          )}
        </div>
      )}
      {children}
    </div>
  );
}

export function MetricRow({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <dl className="flex justify-between items-center py-1.5 border-b border-lira-border/50 last:border-0">
      <dt className="text-xs text-lira-muted-aa">{label}</dt>
      <dd className={clsx("text-sm font-medium", color ?? "text-slate-200")}>{value}</dd>
    </dl>
  );
}

export function SeverityBadge({ level }: { level: string }) {
  const color = {
    very_severe: "bg-red-900/40 text-red-400",
    severe:      "bg-orange-900/40 text-orange-400",
    moderate:    "bg-yellow-900/40 text-yellow-400",
    low:         "bg-lira-green/20 text-lira-green",
    very_low:    "bg-lira-sky/20 text-lira-sky",
    high:        "bg-orange-900/40 text-orange-400",
    very_high:   "bg-red-900/40 text-red-400",
    medium:      "bg-yellow-900/40 text-yellow-400",
  }[level] ?? "bg-lira-border text-lira-muted";

  return (
    <span className={clsx("px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wide", color)}>
      {level.replace(/_/g, " ")}
    </span>
  );
}

export function AssumptionNote({ text }: { text: string }) {
  const isAssumption = text.startsWith("ASSUMPTION");
  const isValidation = text.startsWith("NEEDS VALIDATION");
  return (
    <div role="note" className={clsx(
      "text-xs px-3 py-2 rounded border-l-2 mb-1",
      isAssumption  ? "border-yellow-500 bg-yellow-900/10 text-yellow-300" :
      isValidation  ? "border-lira-warning bg-lira-warning/10 text-orange-300" :
                      "border-lira-border text-lira-muted"
    )}>
      {text}
    </div>
  );
}
