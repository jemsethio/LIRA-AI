"use client";
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from "recharts";
import { useTranslations } from "next-intl";

interface TradeoffsChartProps {
  data: { dimension: string; score: number }[];
}

export default function TradeoffsChart({ data }: TradeoffsChartProps) {
  const t = useTranslations();
  const maxItem = data?.length
    ? data.reduce((a, b) => (b.score > a.score ? b : a), data[0])
    : null;
  const chartSummary = data?.length
    ? `${data.length} dimensions; highest: ${maxItem?.dimension ?? ""} at ${maxItem?.score ?? ""}`
    : "No data available";
  const columns = ["Dimension", "Score"];
  const rows = (data ?? []).map((d) => [d.dimension, d.score]);

  return (
    <div
      role="img"
      aria-label={t("chart.ariaLabel", { title: "Tradeoff Dimensions Radar", summary: chartSummary })}
      aria-describedby="chart-table-tradeoffs-radar"
    >
      <ResponsiveContainer width="100%" height={300}>
        <RadarChart data={data}>
          <PolarGrid stroke="#2a3f52" />
          <PolarAngleAxis dataKey="dimension" tick={{ fill: "#7a9ab0", fontSize: 9 }} />
          <Radar
            name="Risk Score"
            dataKey="score"
            stroke="#e07a2f"
            fill="#e07a2f"
            fillOpacity={0.35}
          />
          <Tooltip contentStyle={{ background: "#1a2634", border: "1px solid #2a3f52", borderRadius: 8 }} />
        </RadarChart>
      </ResponsiveContainer>
      <table
        id="chart-table-tradeoffs-radar"
        className="sr-only"
        aria-label={t("chart.dataTable", { title: "Tradeoff Dimensions Radar" })}
      >
        <caption className="sr-only">
          Tradeoff Dimensions Radar — {t("chart.dataTableCaption")}
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
