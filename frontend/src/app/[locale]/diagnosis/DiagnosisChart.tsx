"use client";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from "recharts";
import { useTranslations } from "next-intl";

interface DiagnosisChartProps {
  data: { subject: string; severity: number }[];
}

export default function DiagnosisChart({ data }: DiagnosisChartProps) {
  const t = useTranslations();
  const maxItem = data?.length
    ? data.reduce((a, b) => (b.severity > a.severity ? b : a), data[0])
    : null;
  const chartSummary = data?.length
    ? `${data.length} indicators; highest: ${maxItem?.subject ?? ""} at ${maxItem?.severity ?? ""}`
    : "No data available";
  const columns = ["Indicator", "Severity"];
  const rows = (data ?? []).map((d) => [d.subject, d.severity]);

  return (
    <div
      role="img"
      aria-label={t("chart.ariaLabel", { title: "Indicator Severity Radar", summary: chartSummary })}
      aria-describedby="chart-table-diagnosis-radar"
    >
      <ResponsiveContainer width="100%" height={280}>
        <RadarChart data={data}>
          <PolarGrid stroke="#2a3f52" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: "#7a9ab0", fontSize: 10 }} />
          <Radar
            name="Severity"
            dataKey="severity"
            stroke="#e07a2f"
            fill="#e07a2f"
            fillOpacity={0.3}
          />
          <Tooltip
            contentStyle={{ background: "#1a2634", border: "1px solid #2a3f52", borderRadius: 8 }}
            labelStyle={{ color: "#e2e8f0" }}
          />
        </RadarChart>
      </ResponsiveContainer>
      <table
        id="chart-table-diagnosis-radar"
        className="sr-only"
        aria-label={t("chart.dataTable", { title: "Indicator Severity Radar" })}
      >
        <caption className="sr-only">
          Indicator Severity Radar — {t("chart.dataTableCaption")}
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
