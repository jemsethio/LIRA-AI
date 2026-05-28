"use client";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Cell } from "recharts";
import { useTranslations } from "next-intl";

const RISK_COLOR = (score: number) =>
  score > 0.7 ? "#c1121f" : score > 0.5 ? "#e07a2f" : score > 0.3 ? "#e9c46a" : "#2d6a4f";

interface ClimateChartProps {
  data: { name: string; score: number }[];
}

export default function ClimateChart({ data }: ClimateChartProps) {
  const t = useTranslations();
  const vals = (data ?? []).map((d) => d.score);
  const min = vals.length ? Math.min(...vals) : 0;
  const max = vals.length ? Math.max(...vals) : 0;
  const chartSummary = data?.length
    ? `${data.length} data points; range ${min}–${max}`
    : "No data available";
  const columns = ["Name", "Score"];
  const rows = (data ?? []).map((d) => [d.name, d.score]);

  return (
    <div
      role="img"
      aria-label={t("chart.ariaLabel", { title: "Climate Risk Profile", summary: chartSummary })}
      aria-describedby="chart-table-climate-bar"
    >
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} layout="vertical">
          <XAxis type="number" domain={[0, 100]} tick={{ fill: "#7a9ab0", fontSize: 10 }} />
          <YAxis type="category" dataKey="name" width={220} tick={{ fill: "#7a9ab0", fontSize: 10 }} />
          <Tooltip
            contentStyle={{ background: "#1a2634", border: "1px solid #2a3f52", borderRadius: 8 }}
          />
          <Bar dataKey="score" radius={[0, 4, 4, 0]}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={RISK_COLOR(entry.score / 100)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
      <table
        id="chart-table-climate-bar"
        className="sr-only"
        aria-label={t("chart.dataTable", { title: "Climate Risk Profile" })}
      >
        <caption className="sr-only">
          Climate Risk Profile — {t("chart.dataTableCaption")}
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
