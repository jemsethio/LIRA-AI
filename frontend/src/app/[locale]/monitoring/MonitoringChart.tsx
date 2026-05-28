"use client";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from "recharts";
import { useTranslations } from "next-intl";

interface MonitoringChartProps {
  data: { subject: string; score: number }[];
}

export default function MonitoringChart({ data }: MonitoringChartProps) {
  const t = useTranslations();
  const maxItem = data?.length
    ? data.reduce((a, b) => (b.score > a.score ? b : a), data[0])
    : null;
  const chartSummary = data?.length
    ? `${data.length} indicators; highest: ${maxItem?.subject ?? ""} at ${maxItem?.score ?? ""}`
    : "No data available";
  const columns = ["Indicator", "Score"];
  const rows = (data ?? []).map((d) => [d.subject, d.score]);

  return (
    <div
      role="img"
      aria-label={t("chart.ariaLabel", { title: "Monitoring Indicators", summary: chartSummary })}
      aria-describedby="chart-table-monitoring-chart"
    >
      <ResponsiveContainer width="100%" height={240}>
        <RadarChart data={data}>
          <PolarGrid stroke="#2a3f52" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: "#7a9ab0", fontSize: 10 }} />
          <Radar
            name="Score"
            dataKey="score"
            stroke="#2d6a4f"
            fill="#2d6a4f"
            fillOpacity={0.3}
          />
          <Tooltip contentStyle={{ background: "#1a2634", border: "1px solid #2a3f52", borderRadius: 8 }} />
        </RadarChart>
      </ResponsiveContainer>
      <table
        id="chart-table-monitoring-chart"
        className="sr-only"
        aria-label={t("chart.dataTable", { title: "Monitoring Indicators" })}
      >
        <caption className="sr-only">
          Monitoring Indicators — {t("chart.dataTableCaption")}
        </caption>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
