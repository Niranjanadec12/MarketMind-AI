import { useMemo, useState } from "react";
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { Bar, Doughnut, Line } from "react-chartjs-2";
import "./AnalyticsReports.css";

ChartJS.register(
  ArcElement,
  BarElement,
  CategoryScale,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip
);

const palette = {
  violet: "#a78bfa",
  indigo: "#818cf8",
  cyan: "#67e8f9",
  pink: "#f0abfc",
  green: "#6ee7b7",
  orange: "#fdba74",
};

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      labels: { color: "#e5e7eb", usePointStyle: true, padding: 18 },
    },
    tooltip: {
      backgroundColor: "#111127",
      titleColor: "#ffffff",
      bodyColor: "#e5e7eb",
      borderColor: "#433879",
      borderWidth: 1,
    },
  },
  scales: {
    x: {
      ticks: { color: "#a5b4fc", maxRotation: 45, minRotation: 0 },
      grid: { color: "rgba(148,163,184,0.10)" },
    },
    y: {
      ticks: { color: "#cbd5e1" },
      grid: { color: "rgba(148,163,184,0.12)" },
    },
  },
};

const number = (value) =>
  new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(
    Number(value) || 0
  );

const money = (value) =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 2,
  }).format(Number(value) || 0);

const percent = (part, total) =>
  Number(total) > 0 ? `${((Number(part) / Number(total)) * 100).toFixed(1)}%` : "0%";

function downloadCsv(filename, rows) {
  if (!rows?.length) {
    window.alert("There is no data available to export yet.");
    return;
  }

  const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  const escapeCell = (value) => {
    const text = value == null ? "" : String(value);
    return `"${text.replace(/"/g, '""')}"`;
  };
  const csv = [
    columns.map(escapeCell).join(","),
    ...rows.map((row) => columns.map((key) => escapeCell(row[key])).join(",")),
  ].join("\r\n");

  const blob = new Blob(["\uFEFF", csv], {
    type: "text/csv;charset=utf-8;",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function ReportCard({ title, value, detail }) {
  return (
    <article className="reports-metric">
      <span>{title}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}

function ChartPanel({ title, description, children, className = "" }) {
  return (
    <section className={`reports-panel ${className}`}>
      <div className="reports-panel-heading">
        <h3>{title}</h3>
        {description && <p>{description}</p>}
      </div>
      {children}
    </section>
  );
}

export default function AnalyticsReports({
  insightsData,
  forecastData,
  comparisonData,
  segmentsData,
}) {
  const [period, setPeriod] = useState("daily");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  const trendRows = useMemo(() => {
    const rows = insightsData?.sales_trends?.[period] || [];
    return rows.filter((row) => {
      const date = String(row.period || "");
      return (!fromDate || date >= fromDate) && (!toDate || date <= toDate);
    });
  }, [insightsData, period, fromDate, toDate]);

  const products = insightsData?.top_products || [];
  const segmentCounts =
    insightsData?.segments?.segment_counts ||
    Object.fromEntries(
      (segmentsData?.segments || []).map((item) => [
        item.segment_name || `Segment ${item.hierarchical_cluster}`,
        item.customer_count || 0,
      ])
    );
  const churnCounts = insightsData?.churn?.risk_counts || {};
  const anomalyCounts = insightsData?.anomalies?.severity_counts || {};
  const forecasts = forecastData?.forecasts || [];
  const metrics = comparisonData?.metrics || [];

  const segmentEntries = Object.entries(segmentCounts);
  const churnEntries = Object.entries(churnCounts);
  const anomalyEntries = Object.entries(anomalyCounts);

  const trendChart = {
    labels: trendRows.map((row) => row.period),
    datasets: [
      {
        label: "Historical revenue (BRL)",
        data: trendRows.map((row) => Number(row.revenue) || 0),
        borderColor: palette.violet,
        backgroundColor: "rgba(167,139,250,0.16)",
        fill: true,
        tension: 0.3,
        pointRadius: 3,
      },
    ],
  };

  const productChart = {
    labels: products.map(
      (item) => item.product_category_name_english || item.product_id || "Product"
    ),
    datasets: [
      {
        label: "Sales value (BRL)",
        data: products.map((item) => Number(item.total_sales) || 0),
        backgroundColor: [
          palette.violet,
          palette.indigo,
          palette.cyan,
          palette.pink,
          palette.green,
        ],
        borderRadius: 6,
      },
    ],
  };

  const segmentChart = {
    labels: segmentEntries.map(([label]) => label),
    datasets: [
      {
        data: segmentEntries.map(([, count]) => Number(count) || 0),
        backgroundColor: [
          palette.violet,
          palette.indigo,
          palette.cyan,
          palette.pink,
          palette.green,
        ],
        borderColor: "#17172b",
        borderWidth: 3,
      },
    ],
  };

  const forecastChart = {
    labels: forecasts.map((row) => row.ds),
    datasets: [
      {
        label: "Random Forest",
        data: forecasts.map((row) => row.random_forest_forecast ?? null),
        borderColor: palette.violet,
        backgroundColor: palette.violet,
        pointRadius: 0,
        tension: 0.2,
      },
      {
        label: "XGBoost",
        data: forecasts.map((row) => row.xgboost_forecast ?? null),
        borderColor: palette.cyan,
        backgroundColor: palette.cyan,
        pointRadius: 0,
        tension: 0.2,
      },
      {
        label: "Prophet",
        data: forecasts.map((row) => row.prophet_forecast ?? null),
        borderColor: palette.orange,
        backgroundColor: palette.orange,
        pointRadius: 0,
        tension: 0.2,
      },
    ],
  };

  const riskChart = {
    labels: churnEntries.map(([label]) => label),
    datasets: [
      {
        label: "Customers",
        data: churnEntries.map(([, count]) => Number(count) || 0),
        backgroundColor: [palette.green, palette.orange, "#fb7185", palette.indigo],
        borderRadius: 6,
      },
    ],
  };

  const anomalyChart = {
    labels: anomalyEntries.map(([label]) => label),
    datasets: [
      {
        label: "Alerts",
        data: anomalyEntries.map(([, count]) => Number(count) || 0),
        backgroundColor: [palette.cyan, palette.orange, "#fb7185", palette.indigo],
        borderRadius: 6,
      },
    ],
  };

  const totalSegments = segmentEntries.reduce(
    (sum, [, count]) => sum + (Number(count) || 0),
    0
  );
  const totalChurn = Number(insightsData?.churn?.total_predictions) || 0;
  const totalAnomalies = Number(insightsData?.anomalies?.total_alerts) || 0;
  const inventory = insightsData?.inventory || {};
  const forecastSummary = insightsData?.forecast || {};

  const exportSummary = () => {
    const rows = [
      { section: "Report information", metric: "Generated at", value: new Date().toISOString(), unit: "" },
      { section: "Sales trend", metric: "Period granularity", value: period, unit: "" },
      { section: "Sales trend", metric: "Start date filter", value: fromDate || "Not set", unit: "" },
      { section: "Sales trend", metric: "End date filter", value: toDate || "Not set", unit: "" },
      { section: "Sales trend", metric: "Currency", value: "BRL", unit: "" },
      { section: "Sales trend", metric: "Trend rows included", value: trendRows.length, unit: "rows" },
      { section: "Inventory", metric: "Latest snapshot date", value: inventory.latest_snapshot_date || "Unknown", unit: "" },
      { section: "Inventory", metric: "Low-stock items", value: inventory.low_stock_items ?? "", unit: "items" },
      { section: "Inventory", metric: "Stockout-risk items", value: inventory.stockout_risk_items ?? "", unit: "items" },
      { section: "Segments", metric: "Total customers segmented", value: insightsData?.segments?.total_customers ?? totalSegments, unit: "customers" },
      { section: "Churn", metric: "Total predictions", value: totalChurn, unit: "predictions" },
      { section: "Anomalies", metric: "Total alerts", value: totalAnomalies, unit: "alerts" },
      { section: "Forecast", metric: "Selected summary model", value: forecastSummary.model || "Random Forest", unit: "" },
      { section: "Forecast", metric: "Forecast days", value: forecastSummary.forecast_days ?? forecasts.length, unit: "days" },
      { section: "Forecast", metric: "Average daily forecast", value: forecastSummary.average_daily_forecast_brl ?? "", unit: "BRL" },
      ...trendRows.map((row) => ({ section: "Historical sales trend", metric: row.period, value: row.revenue, unit: "BRL" })),
      ...products.map((row) => ({ section: "Top products", metric: row.product_category_name_english || row.product_id, value: row.total_sales, unit: "BRL sales" })),
      ...segmentEntries.map(([label, count]) => ({ section: "Customer segments", metric: label, value: count, unit: "customers" })),
      ...churnEntries.map(([label, count]) => ({ section: "Churn risk", metric: label, value: count, unit: "predictions" })),
      ...anomalyEntries.map(([label, count]) => ({ section: "Anomaly severity", metric: label, value: count, unit: "alerts" })),
      ...metrics.map((row) => ({ section: "Forecast model comparison", metric: row.model, value: JSON.stringify(row), unit: "evaluation metrics" })),
    ];

    downloadCsv("marketmind_analytics_report.csv", rows);
  };

  return (
    <div className="reports-page">
      <header className="reports-header">
        <div>
          <p className="reports-eyebrow">BUSINESS INTELLIGENCE</p>
          <h2>Analytics &amp; Reports</h2>
          <p>
            Explore historical sales, product performance, customers, forecasts,
            and model evaluation results.
          </p>
        </div>
        <button className="reports-export-button" onClick={exportSummary} type="button">
          Export full report CSV
        </button>
      </header>

      <div className="reports-filter-panel">
        <label>
          Trend granularity
          <select value={period} onChange={(event) => setPeriod(event.target.value)}>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
          </select>
        </label>
        <label>
          From
          <input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} />
        </label>
        <label>
          To
          <input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} />
        </label>
        <button
          type="button"
          className="reports-secondary-button"
          onClick={() => {
            setFromDate("");
            setToDate("");
          }}
        >
          Clear filters
        </button>
        <button
          type="button"
          className="reports-secondary-button"
          onClick={() =>
            downloadCsv(
              `marketmind_${period}_sales_trend.csv`,
              trendRows.map((row) => ({ period: row.period, revenue_brl: row.revenue }))
            )
          }
        >
          Export filtered trend
        </button>
      </div>

      <p className="reports-note">
        Trend filters apply to the currently loaded series only: up to 30 daily,
        12 weekly, or 12 monthly points. These are historical analytics, not live
        transactions. Sales amounts and forecast values are in BRL.
      </p>

      <div className="reports-metrics-grid">
        <ReportCard
          title="Trend points"
          value={number(trendRows.length)}
          detail={`${period} records after filtering`}
        />
        <ReportCard
          title="Customer segments"
          value={number(insightsData?.segments?.total_customers ?? totalSegments)}
          detail="Customers in historical segmentation output"
        />
        <ReportCard
          title="Churn predictions"
          value={number(totalChurn)}
          detail="Historical model output"
        />
        <ReportCard
          title="Anomaly alerts"
          value={number(totalAnomalies)}
          detail="Alerts require investigation"
        />
      </div>

      <div className="reports-chart-grid">
        <ChartPanel
          title="Sales & revenue trend"
          description="Delivered order items, including freight. Historical values in BRL."
          className="reports-panel-wide"
        >
          {trendRows.length ? (
            <div className="reports-chart reports-chart-tall">
              <Line data={trendChart} options={chartOptions} />
            </div>
          ) : (
            <p className="reports-empty">No trend points match the selected dates.</p>
          )}
        </ChartPanel>

        <ChartPanel title="Top product performance" description="Top five products by historical sales value.">
          {products.length ? (
            <>
              <div className="reports-chart">
                <Bar data={productChart} options={{ ...chartOptions, indexAxis: "y" }} />
              </div>
              <div className="reports-table-wrap">
                <table className="reports-table">
                  <thead><tr><th>Product / category</th><th>Items sold</th><th>Sales (BRL)</th></tr></thead>
                  <tbody>
                    {products.map((product, index) => (
                      <tr key={product.product_id || index}>
                        <td>{product.product_category_name_english || product.product_id || "Unknown"}</td>
                        <td>{number(product.total_items_sold)}</td>
                        <td>{money(product.total_sales)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : <p className="reports-empty">Product analytics are unavailable.</p>}
        </ChartPanel>

        <ChartPanel title="Customer segment distribution" description="Existing hierarchical clustering output.">
          {segmentEntries.length ? (
            <>
              <div className="reports-chart reports-chart-doughnut">
                <Doughnut data={segmentChart} options={{ ...chartOptions, scales: undefined, cutout: "64%" }} />
              </div>
              <ul className="reports-legend-list">
                {segmentEntries.map(([label, count]) => (
                  <li key={label}><span>{label}</span><strong>{number(count)} · {percent(count, totalSegments)}</strong></li>
                ))}
              </ul>
            </>
          ) : <p className="reports-empty">Segment data is unavailable.</p>}
        </ChartPanel>

        <ChartPanel title="Inventory summary" description="Latest recorded inventory snapshot, not live stock.">
          <div className="reports-inventory-grid">
            <div><span>Snapshot date</span><strong>{inventory.latest_snapshot_date || "Unavailable"}</strong></div>
            <div><span>Low-stock items</span><strong>{number(inventory.low_stock_items)}</strong></div>
            <div><span>Stockout-risk items</span><strong>{number(inventory.stockout_risk_items)}</strong></div>
          </div>
          <p className="reports-note">{inventory.note || "Inventory figures reflect a historical snapshot."}</p>
        </ChartPanel>

        <ChartPanel title="Revenue forecasts" description="Existing model outputs; forecast values are estimates, not actual sales.">
          {forecasts.length ? (
            <div className="reports-chart reports-chart-tall">
              <Line data={forecastChart} options={chartOptions} />
            </div>
          ) : <p className="reports-empty">Forecast data is unavailable.</p>}
          <p className="reports-note">
            {number(forecastSummary.forecast_days ?? forecasts.length)} forecast days.
            {forecastSummary.forecast_start ? ` From ${forecastSummary.forecast_start}` : ""}
            {forecastSummary.forecast_end ? ` to ${forecastSummary.forecast_end}.` : ""}
          </p>
          <button
            type="button"
            className="reports-secondary-button"
            onClick={() => downloadCsv("marketmind_revenue_forecasts.csv", forecasts)}
          >
            Export forecast rows
          </button>
        </ChartPanel>

        <ChartPanel title="Churn-risk summary" description="Counts from saved churn predictions; reliability is affected by class imbalance.">
          {churnEntries.length ? (
            <div className="reports-chart">
              <Bar data={riskChart} options={chartOptions} />
            </div>
          ) : <p className="reports-empty">Churn data is unavailable.</p>}
          <ul className="reports-legend-list">
            {churnEntries.map(([label, count]) => (
              <li key={label}><span>{label}</span><strong>{number(count)} · {percent(count, totalChurn)}</strong></li>
            ))}
          </ul>
          <p className="reports-note">Treat these as historical risk estimates, not confirmed customer decisions.</p>
        </ChartPanel>

        <ChartPanel title="Anomaly alert summary" description="Alert counts grouped by severity.">
          {anomalyEntries.length ? (
            <div className="reports-chart">
              <Bar data={anomalyChart} options={chartOptions} />
            </div>
          ) : <p className="reports-empty">Anomaly data is unavailable.</p>}
          <ul className="reports-legend-list">
            {anomalyEntries.map(([label, count]) => (
              <li key={label}><span>{label}</span><strong>{number(count)} · {percent(count, totalAnomalies)}</strong></li>
            ))}
          </ul>
          <p className="reports-note">
            Alerts are not proof of fraud. The recorded benchmark metrics used synthetic labels.
          </p>
        </ChartPanel>

        <ChartPanel title="Forecast model evaluation" description="Saved evaluation results; no model is retrained by this page.">
          {metrics.length ? (
            <div className="reports-table-wrap">
              <table className="reports-table">
                <thead><tr><th>Model</th><th>MAE</th><th>RMSE</th><th>MAPE</th></tr></thead>
                <tbody>
                  {metrics.map((model, index) => (
                    <tr key={model.model || index}>
                      <td>{model.model || "Unknown"}</td>
                      <td>{number(model.MAE)}</td>
                      <td>{number(model.RMSE)}</td>
                      <td>{model.MAPE == null ? "—" : `${number(model.MAPE)}%`}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p className="reports-empty">Model comparison data is unavailable.</p>}
          <p className="reports-note">
            MAE and RMSE are error metrics: lower values are generally better when compared on the same test set.
          </p>
          <button
            type="button"
            className="reports-secondary-button"
            onClick={() => downloadCsv("marketmind_model_evaluation.csv", metrics)}
          >
            Export evaluation metrics
          </button>
        </ChartPanel>

        <ChartPanel title="Product recommendations" description="Highest-scoring saved product suggestions.">
          {(insightsData?.product_suggestions || []).length ? (
            <div className="reports-table-wrap">
              <table className="reports-table">
                <thead><tr><th>Product</th><th>Category</th><th>Score</th><th>Reason</th></tr></thead>
                <tbody>
                  {insightsData.product_suggestions.map((item, index) => (
                    <tr key={item.product_id || index}>
                      <td>{item.product_id || "—"}</td>
                      <td>{item.category || "—"}</td>
                      <td>{number(item.score)}</td>
                      <td>{item.reason || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <p className="reports-empty">Recommendation data is unavailable.</p>}
          <p className="reports-note">
            Recommendations are candidate suggestions based on historical interactions, not guaranteed future purchases.
          </p>
        </ChartPanel>
      </div>
    </div>
  );
}
