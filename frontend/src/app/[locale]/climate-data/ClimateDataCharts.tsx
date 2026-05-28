"use client";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer,
  Tooltip, Legend, Cell,
} from "recharts";
import { useTranslations } from "next-intl";

interface ChartDataItem {
  year: string;
  precip_mm: number;
  delta_temp: number;
  is_real?: boolean;
}

interface RiskDataItem {
  year: string;
  drought: number;
  heat: number;
  rainfall: number;
  erosion: number;
  is_real?: boolean;
}

interface ClimateDataChartsProps {
  chartData: ChartDataItem[];
  riskData: RiskDataItem[];
  activeScenario: string;
}

export default function ClimateDataCharts({ chartData, riskData, activeScenario }: ClimateDataChartsProps) {
  const t = useTranslations();
  // Chart 1: Precipitation & Temperature
  const precipVals = (chartData ?? []).map((d) => d.precip_mm);
  const precipMin = precipVals.length ? Math.min(...precipVals) : 0;
  const precipMax = precipVals.length ? Math.max(...precipVals) : 0;
  const chart1Summary = chartData?.length
    ? `${chartData.length} data points; precip range ${precipMin}–${precipMax} mm`
    : "No data available";
  const chart1Columns = ["Year", "Precipitation (mm)", "ΔTemp (°C)"];
  const chart1Rows = (chartData ?? []).map((d) => [d.year, d.precip_mm, d.delta_temp]);

  // Chart 2: Risk Scores
  const riskSummary = riskData?.length
    ? `${riskData.length} data points across drought, heat, rainfall, erosion risk`
    : "No data available";
  const chart2Columns = ["Year", "Drought", "Heat", "Rainfall", "Erosion"];
  const chart2Rows = (riskData ?? []).map((d) => [d.year, d.drought, d.heat, d.rainfall, d.erosion]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
      <div className="bg-lira-surface border border-lira-border rounded-xl p-4">
        <div className="text-sm font-semibold text-slate-200 mb-3">
          Precipitation & Temperature — {activeScenario.toUpperCase()}
        </div>
        <div
          role="img"
          aria-label={t("chart.ariaLabel", { title: "Precipitation and Temperature", summary: chart1Summary })}
          aria-describedby="chart-table-climate-data-bar-1"
        >
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={chartData}>
              <XAxis dataKey="year" tick={{fill:"#7a9ab0",fontSize:11}} />
              <YAxis yAxisId="l" tick={{fill:"#7a9ab0",fontSize:10}} label={{value:"mm/yr",angle:-90,position:"insideLeft",fill:"#7a9ab0",fontSize:9}} />
              <YAxis yAxisId="r" orientation="right" tick={{fill:"#7a9ab0",fontSize:10}} label={{value:"ΔT °C",angle:90,position:"insideRight",fill:"#7a9ab0",fontSize:9}} />
              <Tooltip contentStyle={{background:"#1a2634",border:"1px solid #2a3f52",borderRadius:8}} />
              <Legend wrapperStyle={{fontSize:10,color:"#7a9ab0"}} />
              <Bar yAxisId="l" dataKey="precip_mm" name="Annual precip (mm)" fill="#1a759f" radius={[4,4,0,0]} />
              <Bar yAxisId="r" dataKey="delta_temp" name="ΔTemp vs 1990 (°C)" fill="#c1121f" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
          <table
            id="chart-table-climate-data-bar-1"
            className="sr-only"
            aria-label={t("chart.dataTable", { title: "Precipitation and Temperature" })}
          >
            <caption className="sr-only">
              Precipitation and Temperature — {t("chart.dataTableCaption")}
            </caption>
            <thead>
              <tr>
                {chart1Columns.map((col) => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {chart1Rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[10px] text-lira-muted mt-1 text-center">
          {chartData[0]?.is_real ? "✓ Real NASA NEX GDDP CMIP6 data" : "⚠ Fallback values (run prep script)"}
        </p>
      </div>

      <div className="bg-lira-surface border border-lira-border rounded-xl p-4">
        <div className="text-sm font-semibold text-slate-200 mb-3">
          Risk Scores — {activeScenario.toUpperCase()}
        </div>
        <div
          role="img"
          aria-label={t("chart.ariaLabel", { title: "Risk Scores", summary: riskSummary })}
          aria-describedby="chart-table-climate-data-bar-2"
        >
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={riskData}>
              <XAxis dataKey="year" tick={{fill:"#7a9ab0",fontSize:11}} />
              <YAxis tick={{fill:"#7a9ab0",fontSize:10}} domain={[0,100]} label={{value:"Risk %",angle:-90,position:"insideLeft",fill:"#7a9ab0",fontSize:9}} />
              <Tooltip contentStyle={{background:"#1a2634",border:"1px solid #2a3f52",borderRadius:8}} />
              <Legend wrapperStyle={{fontSize:10,color:"#7a9ab0"}} />
              <Bar dataKey="drought"  name="Drought" fill="#e07a2f" stackId="a" />
              <Bar dataKey="heat"     name="Heat stress" fill="#c1121f" stackId="a" />
              <Bar dataKey="rainfall" name="Rainfall intensity" fill="#1a759f" stackId="a" />
              <Bar dataKey="erosion"  name="Erosion/runoff" fill="#52796f" stackId="a" />
            </BarChart>
          </ResponsiveContainer>
          <table
            id="chart-table-climate-data-bar-2"
            className="sr-only"
            aria-label={t("chart.dataTable", { title: "Risk Scores" })}
          >
            <caption className="sr-only">
              Risk Scores — {t("chart.dataTableCaption")}
            </caption>
            <thead>
              <tr>
                {chart2Columns.map((col) => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {chart2Rows.map((row, i) => (
                <tr key={i}>
                  {row.map((cell, j) => (
                    <td key={j}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
