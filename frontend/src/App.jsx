
import { useCallback, useEffect, useState } from "react";
import "./App.css";
import AnalyticsReports from "./AnalyticsReports";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

// Estimated exchange rate: 1 Brazilian real = 19.3908 Indian rupees.
// Update this rate when you want to use a newer exchange rate.
const BRL_TO_INR_RATE = 19.3908;

const API = {
  login: "/api/auth/login",
  register: "/api/auth/register",
  logout: "/api/auth/logout",
  dashboard: "/api/dashboard",
  segments: "/api/analytics/segments",
  forecast: "/api/analytics/forecast",
  comparison: "/api/analytics/model-comparison",
  salesSummary: "/api/sales/summary",
  salesRecords: "/api/sales/records",
  insights: "/api/analytics/dashboard-insights",
};

function DonutChart({ items, total }) {
  const colors = ["#dc5b62", "#e6a23c", "#3a9d78", "#6688d9", "#9470c8"];
  const circumference = 2 * Math.PI * 42;
  let currentOffset = 0;

  const segments = items.map(([label, count], index) => {
    const numericCount = Number(count) || 0;
    const length = total > 0 ? (numericCount / total) * circumference : 0;
    const segment = {
      label,
      count: numericCount,
      color: colors[index % colors.length],
      length,
      offset: currentOffset,
    };
    currentOffset += length;
    return segment;
  });

  return (
    <div className="ai-donut-layout">
      <div className="ai-donut-visual">
        <svg viewBox="0 0 120 120" role="img" aria-label="Customer churn risk distribution">
          <circle cx="60" cy="60" r="42" fill="none"
            stroke="var(--border-color, #e2e8f0)" strokeWidth="16" />
          {segments.map((segment) => (
            <circle key={segment.label} cx="60" cy="60" r="42" fill="none"
              stroke={segment.color} strokeWidth="16"
              strokeDasharray={`${segment.length} ${circumference - segment.length}`}
              strokeDashoffset={-segment.offset}
              transform="rotate(-90 60 60)">
              <title>{segment.label}: {formatNumber(segment.count)}</title>
            </circle>
          ))}
          <text x="60" y="57" textAnchor="middle" className="ai-donut-total">
            {formatNumber(total)}
          </text>
          <text x="60" y="72" textAnchor="middle" className="ai-donut-caption">
            Customers
          </text>
        </svg>
      </div>
      <ul className="ai-chart-legend">
        {segments.map((segment) => (
          <li key={segment.label}>
            <span className="ai-legend-label">
              <span className="ai-legend-dot" style={{ backgroundColor: segment.color }} />
              {formatLabel(segment.label)}
            </span>
            <strong>{formatNumber(segment.count)}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}

function HorizontalBarChart({ items, formatValue }) {
  const maxValue = Math.max(
    1,
    ...items.map((item) => Math.max(0, Number(item.value) || 0))
  );

  return (
    <div className="ai-horizontal-bars">
      {items.map((item, index) => {
        const value = Math.max(0, Number(item.value) || 0);
        const width = (value / maxValue) * 100;

        return (
          <div className="ai-bar-row" key={`${item.label}-${index}`}>
            <div className="ai-bar-heading">
              <span>{item.label}</span>
              <strong>{formatValue(value)}</strong>
            </div>
            {item.detail && <p className="ai-bar-detail">{item.detail}</p>}
            <div className="ai-bar-track">
              <div className="ai-bar-fill" style={{ width: `${width}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
const numberFormatter = new Intl.NumberFormat("en-IN");

const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? numberFormatter.format(number) : "â€”";
}

// Convert a Brazilian-real amount to Indian rupees.
function convertBRLToINR(value) {
  const amount = Number(value);

  if (!Number.isFinite(amount)) {
    return null;
  }

  return amount * BRL_TO_INR_RATE;
}

// Format an amount that is already in INR.
function formatINR(value) {
  const amount = Number(value);

  return Number.isFinite(amount) ? currencyFormatter.format(amount) : "â€”";
}

// Use this for monetary values received from the API in BRL.
function formatBRLAsINR(value) {
  const convertedAmount = convertBRLToINR(value);

  return convertedAmount === null ? "â€”" : formatINR(convertedAmount);
}

// Convert and format monetary columns in forecast/comparison tables.
// MAPE, dates, model names, customer counts, and other non-monetary
// values are deliberately left unchanged.
function formatTableValue(key, value) {
  if (value === null || value === undefined || value === "") {
    return "â€”";
  }

  const field = String(key).toLowerCase();

  const isMonetaryField =
    /sales|forecast|revenue|mae|rmse|price|purchase_value|amount|cost|profit|freight|item_value/.test(
      field
    );

  if (isMonetaryField && typeof value !== "boolean") {
    const amount = Number(value);

    if (Number.isFinite(amount)) {
      return formatBRLAsINR(amount);
    }
  }

  if (typeof value === "number") {
    return formatNumber(value);
  }

  return typeof value === "object" ? JSON.stringify(value) : String(value);
}

function formatLabel(value) {
  return String(value ?? "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

async function requestJson(path, options = {}, token = "") {
  const headers = {
    ...(options.body instanceof URLSearchParams
      ? {}
      : { "Content-Type": "application/json" }),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  let response;

  try {
  response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });
} catch (error) {
  if (error.name === "AbortError") {
    throw error;
  }

  throw new Error(
    "Cannot connect to the MarketMind AI backend. Please check that the backend server is running."
  );
}

  const text = await response.text();
  let data = {};

  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    const detail =
      data.detail ||
      data.message ||
      `Request failed with status ${response.status}`;

    throw new Error(
      typeof detail === "string" ? detail : JSON.stringify(detail)
    );
  }

  return data;
}

function getTokenFromResponse(data) {
  return (
    data?.access_token ||
    data?.token ||
    data?.data?.access_token ||
    ""
  );
}

function getRows(data, type) {
  if (Array.isArray(data)) {
    return data;
  }

  if (!data || typeof data !== "object") {
    return [];
  }

  const candidates =
    type === "segments"
      ? [
          "segments",
          "clusters",
          "distribution",
          "cluster_distribution",
          "data",
          "results",
        ]
      : type === "forecast"
        ? ["forecasts", "forecast", "data", "results", "predictions"]
        : [
            "metrics",
            "models",
            "comparison",
            "model_comparison",
            "data",
            "results",
          ];

  for (const key of candidates) {
    if (Array.isArray(data[key])) {
      return data[key];
    }

    if (
      type === "segments" &&
      key.includes("distribution") &&
      data[key] &&
      typeof data[key] === "object"
    ) {
      return Object.entries(data[key]).map(([cluster, count]) => ({
        cluster,
        customer_count: count,
      }));
    }
  }

  if (type === "segments" && data.cluster_distribution) {
    return Object.entries(data.cluster_distribution).map(
      ([cluster, count]) => ({
        cluster,
        customer_count: count,
      })
    );
  }

  return [];
}

function DataTable({ data, type, emptyMessage }) {
  const rows = getRows(data, type);

  if (!rows.length) {
    return <p className="empty-message">{emptyMessage}</p>;
  }

  const columns = [
    ...new Set(
      rows
        .slice(0, 20)
        .flatMap((row) =>
          row && typeof row === "object" && !Array.isArray(row)
            ? Object.keys(row)
            : []
        )
    ),
  ].slice(0, 8);

  if (!columns.length) {
    return <pre className="json-output">{JSON.stringify(data, null, 2)}</pre>;
  }

  return (
    <div className="table-wrapper">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{formatLabel(column)}</th>
            ))}
          </tr>
        </thead>

        <tbody>
          {rows.slice(0, 100).map((row, index) => (
            <tr key={row.id ?? row.date ?? row.cluster ?? index}>
              {columns.map((column) => (
                <td key={column}>
                  {formatTableValue(column, row?.[column])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>

      {rows.length > 100 && (
        <p className="table-note">
          Showing the first 100 of {formatNumber(rows.length)} records.
        </p>
      )}
    </div>
  );
}

function MetricCard({ title, value, description }) {
  return (
    <article className="kpi-card">
      <p className="kpi-title">{title}</p>
      <h2 className="kpi-value">{value}</h2>
      {description && <p className="kpi-description">{description}</p>}
    </article>
  );
}


function AuthScreen({ onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [fullName, setFullName] = useState("");
  const [username, setUsername] = useState("");
  const [role, setRole] = useState("Store Manager");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      if (mode === "login") {
        // FastAPI OAuth2PasswordRequestForm expects form-encoded data.
        const body = new URLSearchParams();
        body.set("username", email);
        body.set("password", password);

        const data = await requestJson(API.login, {
          method: "POST",
          body,
        });

        const token = getTokenFromResponse(data);

        if (!token) {
          throw new Error(
            "Login succeeded but no access token was returned. Check the login API response."
          );
        }

        onAuthenticated(token);
      } else {
        await requestJson(API.register, {
          method: "POST",
          body: JSON.stringify({
            username,
            full_name: fullName,
            email,
            password,
            role,
          }),

        });

        setMessage("Registration successful. Please sign in.");
        setMode("login");
        setPassword("");
      }
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="brand-mark">M</div>
        <p className="eyebrow">SALES INTELLIGENCE PLATFORM</p>
        <h1>MarketMind AI</h1>
        <p className="auth-subtitle">
          Understand your sales, customers, and business performance.
        </p>

        <div className="auth-tabs">
          <button
            type="button"
            className={mode === "login" ? "auth-tab active" : "auth-tab"}
            onClick={() => {
              setMode("login");
              setError("");
              setMessage("");
            }}
          >
            Sign in
          </button>

          <button
            type="button"
            className={mode === "register" ? "auth-tab active" : "auth-tab"}
            onClick={() => {
              setMode("register");
              setError("");
              setMessage("");
            }}
          >
            Create account
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
        
          {mode === "register" && (
            <>
              <label>
                Username
                <input
                  type="text"
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="Choose a username (at least 3 characters)"
                  autoComplete="username"
                  minLength={3}
                  required
                />
              </label>

              <label>
                Role
                <select
                  value={role}
                  onChange={(event) => setRole(event.target.value)}
                  required
                >
                  <option value="Business Owner">Business Owner</option>
                  <option value="Store Manager">Store Manager</option>
                  <option value="Sales Executive">Sales Executive</option>
                  <option value="Administrator">Administrator</option>
                </select>
              </label>
            </>
          )}

          {mode === "register" && (
            <label>
              Full name
              <input
                type="text"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Enter your full name"
                autoComplete="name"
                required
              />
            </label>
          )}

          <label>
            Email address
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
              required
            />
          </label>

          {error && <p className="alert alert-error">{error}</p>}
          {message && <p className="alert alert-success">{message}</p>}

          <button className="primary-button full-button" disabled={loading}>
            {loading
              ? "Please wait..."
              : mode === "login"
                ? "Sign in"
                : "Create account"}
          </button>
        </form>

        <p className="auth-footer">
          Secure access powered by role-based permissions.
        </p>
      </section>
    </main>
  );
}

function App() {
  const [token, setToken] = useState(
    () => localStorage.getItem("access_token") || ""
  );

  const [dashboardData, setDashboardData] = useState(null);
  const [insightsData, setInsightsData] = useState(null);
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [insightsError, setInsightsError] = useState("");
  const [trendPeriod, setTrendPeriod] = useState("daily");
  const [segmentsData, setSegmentsData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);
  const [salesSummary, setSalesSummary] = useState(null);
  const [salesRecords, setSalesRecords] = useState([]);
  const [salesTotal, setSalesTotal] = useState(0);
  const [salesSearch, setSalesSearch] = useState("");
  const [salesStatus, setSalesStatus] = useState("");
  const [salesOffset, setSalesOffset] = useState(0);

  const [salesLoading, setSalesLoading] = useState(false);
  const [salesError, setSalesError] = useState("");
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState("");
  const [analyticsError, setAnalyticsError] = useState("");

  const [activeSection, setActiveSection] = useState("overview");
  const [forecastHorizon, setForecastHorizon] = useState("30");
  const [forecastModel, setForecastModel] = useState("random_forest_forecast");

  const handleAuthenticated = useCallback((newToken) => {
    localStorage.setItem("access_token", newToken);
    setToken(newToken);
  }, []);

  const handleLogout = useCallback(async () => {
    const currentToken = token;

    try {
      if (currentToken) {
        await requestJson(API.logout, { method: "POST" }, currentToken);
      }
    } catch {
      // Clear the local session even if the server logout route is unavailable.
    } finally {
      localStorage.removeItem("access_token");
      setToken("");
      setDashboardData(null);
      setInsightsData(null);
      setSegmentsData(null);
      setForecastData(null);
      setComparisonData(null);
    }
  }, [token]);

  const loadDashboard = useCallback(async () => {
    setDashboardLoading(true);
    setDashboardError("");

    try {
      const data = await requestJson(API.dashboard, {}, token);
      setDashboardData(data);
    } catch (err) {
      setDashboardError(err.message || "Could not load the dashboard.");
    } finally {
      setDashboardLoading(false);
    }
  }, [token]);

 
  const loadDashboardInsights = useCallback(async () => {
    setInsightsLoading(true);
    setInsightsError("");
    try {
      const data = await requestJson(API.insights, {}, token);
      setInsightsData(data);
    } catch (err) {
      setInsightsError(err.message || "Could not load dashboard insights.");
    } finally {
      setInsightsLoading(false);
    }
  }, [token]);

  const loadAnalytics = useCallback(async () => {
  setAnalyticsLoading(true);
  setAnalyticsError("");

  try {
    const requests = [
      ["segments", API.segments],
      ["forecast", API.forecast],
      ["comparison", API.comparison],
    ];

    const results = await Promise.allSettled(
      requests.map(([, path]) => requestJson(path, {}, token))
    );

    const failures = [];

    results.forEach((result, index) => {
      const key = requests[index][0];

      if (result.status === "fulfilled") {
        if (key === "segments") setSegmentsData(result.value);
        if (key === "forecast") setForecastData(result.value);
        if (key === "comparison") setComparisonData(result.value);
      } else {
        failures.push(
          `${key}: ${result.reason?.message || "Request failed"}`
        );
      }
    });

    if (failures.length) {
      setAnalyticsError(failures.join(" | "));
    }
  } catch (err) {
    setAnalyticsError(
      err.message || "Could not load analytics data."
    );
  } finally {
    setAnalyticsLoading(false);
  }
}, [token]);


  const loadSalesSummary = useCallback(async () => {
    try {
      const data = await requestJson(API.salesSummary, {}, token);
      setSalesSummary(data);
    } catch (err) {
      setSalesError(err.message || "Could not load the sales summary.");
    }
  }, [token]);

  const loadSalesRecords = useCallback(async (
    offset = 0,
    search = "",
    status = ""
  ) => {
    setSalesLoading(true);
    setSalesError("");

    try {
      const params = new URLSearchParams({
        limit: "25",
        offset: String(offset),
      });

      if (search.trim()) params.set("search", search.trim());
      if (status) params.set("status", status);

      const data = await requestJson(
        `${API.salesRecords}?${params.toString()}`,
        {},
        token
      );

      setSalesRecords(data.records || []);
      setSalesTotal(data.total || 0);
    } catch (err) {
      setSalesError(err.message || "Could not load sales records.");
    } finally {
      setSalesLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!token) return;

    loadDashboard();
    loadAnalytics();
    loadDashboardInsights();
  }, [token, loadDashboard, loadAnalytics, loadDashboardInsights]);

  useEffect(() => {
    if (!token || activeSection !== "sales") return;

    loadSalesSummary();
    loadSalesRecords(0, salesSearch, salesStatus);
    setSalesOffset(0);
  }, [
    token,
    activeSection,
    loadSalesSummary,
    loadSalesRecords,
  ]);

  if (!token) {
    return <AuthScreen onAuthenticated={handleAuthenticated} />;
  }

  const kpis = [
    {
      title: "Total Sales",
      value:
        dashboardData?.total_sales != null
          ? formatBRLAsINR(dashboardData.total_sales)
          : "â€”",
      description: "Delivered sales, including freight (converted to INR)",
    },
    {
      title: "Total Orders",
      value:
        dashboardData?.total_orders != null
          ? formatNumber(dashboardData.total_orders)
          : "â€”",
      description: "Distinct delivered orders",
    },
    {
      title: "Total Customers",
      value:
        dashboardData?.total_customers != null
          ? formatNumber(dashboardData.total_customers)
          : "â€”",
      description: "Unique customers",
    },
    {
      title: "Total Products",
      value:
        dashboardData?.total_products != null
          ? formatNumber(dashboardData.total_products)
          : "â€”",
      description: "Distinct products",
    },
  ];

  
  const forecastRows = Array.isArray(forecastData?.forecasts)
    ? forecastData.forecasts
    : [];

  const visibleForecastRows = forecastRows.slice(0, Number(forecastHorizon));
  const forecastValues = visibleForecastRows
    .map((row) => Number(row[forecastModel]))
    .filter((value) => Number.isFinite(value));

  const chartMin = forecastValues.length ? Math.min(...forecastValues) : 0;
  const chartMax = forecastValues.length ? Math.max(...forecastValues) : 1;
  const chartRange = chartMax - chartMin || 1;
  const chartWidth = 900;
  const chartHeight = 280;
  const chartPadding = 42;

  const forecastChartPoints = visibleForecastRows
    .map((row, index) => {
      const value = Number(row[forecastModel]);
      if (!Number.isFinite(value)) return null;

      const x = visibleForecastRows.length <= 1
        ? chartWidth / 2
        : chartPadding + index * (chartWidth - chartPadding * 2) /
          (visibleForecastRows.length - 1);
      const y = chartHeight - chartPadding -
        ((value - chartMin) / chartRange) *
          (chartHeight - chartPadding * 2);

      return { x, y, value, date: row.ds };
    })
    .filter(Boolean);
  const navigation = [
    { id: "overview", label: "Overview" },
    { id: "sales", label: "Sales" },
    { id: "segments", label: "Customer Segmentation" },
    { id: "forecast", label: "Revenue Forecast" },
    { id: "comparison", label: "Model Comparison" },
    { id: "churn", label: "Churn Prediction" },
    { id: "recommendations", label: "Product Recommendations" },
    { id: "anomalies", label: "Anomaly Detection" },
    { id: "reports", label: "Analytics & Reports" },
  ];

  const roleAccess = {
    "Business Owner": [
      "overview", "sales", "segments", "forecast", "comparison",
      "churn", "recommendations", "anomalies", "reports"
    ],
    "Store Manager": [
      "overview", "sales", "segments", "forecast",
      "churn", "recommendations", "anomalies", "reports"
    ],
    "Sales Executive": [
      "overview", "sales"
    ],
    "Administrator": [
      "overview", "sales", "segments", "forecast", "comparison",
      "churn", "recommendations", "anomalies", "reports"
    ]
  };

  const allowedSections = roleAccess[dashboardData?.role] || ["overview"];

  const visibleNavigation = navigation.filter(
    (item) => allowedSections.includes(item.id)
  );

useEffect(() => {
  if (!allowedSections.includes(activeSection)) {
    setActiveSection("overview");
  }
}, [activeSection, dashboardData?.role]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark small-mark">M</div>
          <div>
            <strong>MarketMind</strong>
            <span>AI Intelligence</span>
          </div>
        </div>

        <p className="nav-heading">WORKSPACE</p>

        <nav className="sidebar-nav">
          {visibleNavigation.map((item) => (
            <button
              type="button"
              key={item.id}
              className={
                activeSection === item.id ? "nav-item active" : "nav-item"
              }
              onClick={() => setActiveSection(item.id)}
            >
              <span className="nav-dot" />
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="user-chip">
            <div className="user-avatar">
              {(dashboardData?.role || "U").charAt(0).toUpperCase()}
            </div>
            <div className="user-info">
              <strong>{dashboardData?.role || "Authenticated user"}</strong>
              <span>Signed in</span>
            </div>
          </div>

          <button
            type="button"
            className="logout-button"
            onClick={handleLogout}
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">BUSINESS INTELLIGENCE</p>
            <h1>
              {activeSection === "overview"
                ? "Dashboard Overview"
                : navigation.find((item) => item.id === activeSection)?.label}
            </h1>
          </div>

          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              loadDashboard();
              loadAnalytics();
              loadDashboardInsights();
              if (activeSection === "sales") {
                loadSalesSummary();
                loadSalesRecords(salesOffset, salesSearch, salesStatus);
              }
            }}
            disabled={dashboardLoading || analyticsLoading || salesLoading}
          >
            {dashboardLoading || analyticsLoading
              ? "Refreshing..."
              : "Refresh data"}
          </button>
        </header>

        {dashboardError && (
          <div className="alert alert-error page-alert">
            <strong>Dashboard error:</strong> {dashboardError}
            <p>
              Check that the backend is running and that your account has
              dashboard:view permission.
            </p>
          </div>
        )}

        {activeSection === "overview" && (
          <>
            <section className="welcome-panel">
              <div>
                <p className="welcome-label">YOUR BUSINESS AT A GLANCE</p>
                <h2>{dashboardData?.message || "Welcome to MarketMind AI"}</h2>
                <p>
                  Explore your sales performance, customer segments, and
                  revenue forecasting results.
                </p>
              </div>
              <div className="welcome-symbol">â†—</div>
            </section>

            <section className="section-block">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">PERFORMANCE SNAPSHOT</p>
                  <h2>Business metrics</h2>
                </div>
                <span className="data-label">Live API data</span>
              </div>

              {dashboardLoading && !dashboardData ? (
                <div className="loading-panel">Loading dashboard metrics...</div>
              ) : (
                <div className="kpi-grid">
                  {kpis.map((kpi) => (
                    <MetricCard
                      key={kpi.title}
                      title={kpi.title}
                      value={kpi.value}
                      description={kpi.description}
                    />
                  ))}
                </div>
              )}

              {dashboardData && (
                <p className="data-footnote">
                  Monetary values are displayed in INR, converted from BRL
                  using an estimated rate of 1 BRL = {BRL_TO_INR_RATE} INR.
                  Original API data remains in BRL.
                </p>
              )}
            </section>

            <section className="section-block">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">SALES PERFORMANCE</p>
                  <h2>Revenue trends</h2>
                  <p className="section-description">Historical delivered order items, including freight. Values shown in INR.</p>
                </div>
                <div className="trend-tabs">
                  {["daily", "weekly", "monthly"].map((period) => (
                    <button key={period} type="button" className={trendPeriod === period ? "trend-tab active" : "trend-tab"} onClick={() => setTrendPeriod(period)}>
                      {formatLabel(period)}
                    </button>
                  ))}
                </div>
              </div>

              {insightsLoading && !insightsData ? (
                <div className="loading-panel">Loading sales and AI insights...</div>
              ) : insightsError ? (
                <div className="alert alert-warning">{insightsError}</div>
              ) : insightsData ? (
                <>
                  <div className="data-panel">
                    <p className="data-footnote">Historical data: 2016â€“2018. Hover over a bar to see its date and revenue.</p>
                    {(() => {
                      const rows = insightsData.sales_trends?.[trendPeriod] || [];
                      const maxRevenue = Math.max(1, ...rows.map((item) => Number(item.revenue) || 0));
                      return rows.length ? (
                        <div className="trend-chart">
                          {rows.map((item) => (
                            <div className="trend-column" key={item.period} title={`${item.period}: ${formatBRLAsINR(item.revenue)}`}>
                              <div className="trend-bar" style={{ height: `${Math.max(3, (Number(item.revenue) / maxRevenue) * 150)}px` }} />
                              <span>{trendPeriod === "daily" ? item.period.slice(8) : trendPeriod === "monthly" ? item.period.slice(2) : item.period.slice(5, 10)}</span>
                            </div>
                          ))}
                        </div>
                      ) : <p>No trend data available for this period.</p>;
                    })()}
                  </div>

                  <div className="insight-grid">
                    <div className="data-panel">
                      <h3>Top-selling products</h3>
                      {(insightsData.top_products || []).map((product) => (
                        <div className="insight-row" key={product.product_id}>
                          <div><strong>{formatLabel(product.product_category_name_english || "Product")}</strong><p>{product.product_id}</p><span>{formatNumber(product.total_items_sold)} items sold</span></div>
                          <strong>{formatBRLAsINR(product.total_sales)}</strong>
                        </div>
                      ))}
                      {!insightsData.top_products?.length && <p>No product analytics available.</p>}
                    </div>

                    <div className="data-panel">
                      <h3>Inventory alerts</h3>
                      <div className="insight-stat"><span>Low-stock items</span><strong>{formatNumber(insightsData.inventory?.low_stock_items)}</strong></div>
                      <div className="insight-stat"><span>Stockout-risk items</span><strong>{formatNumber(insightsData.inventory?.stockout_risk_items)}</strong></div>
                      <p className="data-footnote">Latest inventory snapshot: {insightsData.inventory?.latest_snapshot_date || "Unavailable"}. These are historical figures, not live stock.</p>
                    </div>

                    <div className="data-panel">
                      <h3>AI business summary</h3>
                      <div className="insight-stat"><span>Forecast model</span><strong>{insightsData.forecast?.model || "Unavailable"}</strong></div>
                      <div className="insight-stat"><span>Average daily forecast</span><strong>{formatBRLAsINR(insightsData.forecast?.average_daily_forecast_brl)}</strong></div>
                      <p className="data-footnote">{formatNumber(insightsData.forecast?.forecast_days)} forecast days: {insightsData.forecast?.forecast_start || "â€”"} to {insightsData.forecast?.forecast_end || "â€”"}. Forecast is based on historical data.</p>
                      <hr />
                      <h3>Customer segments</h3>
                      {Object.entries(insightsData.segments?.segment_counts || {}).map(([name, count]) => (
                        <div className="insight-stat" key={name}><span>{name}</span><strong>{formatNumber(count)}</strong></div>
                      ))}
                    </div>

                    <div className="data-panel">
                      <h3>Churn risk</h3>
                      {Object.entries(insightsData.churn?.risk_counts || {}).map(([risk, count]) => (
                        <div className="insight-stat" key={risk}><span>{risk} risk</span><strong>{formatNumber(count)}</strong></div>
                      ))}
                      <p className="data-footnote">Existing model predictions; counts are not live customer activity.</p>
                      <hr />
                      <h3>Anomaly alerts</h3>
                      <div className="insight-stat"><span>Total alerts</span><strong>{formatNumber(insightsData.anomalies?.total_alerts)}</strong></div>
                      {Object.entries(insightsData.anomalies?.severity_counts || {}).map(([severity, count]) => (
                        <div className="insight-stat" key={severity}><span>{severity}</span><strong>{formatNumber(count)}</strong></div>
                      ))}
                    </div>

                    <div className="data-panel">
                      <h3>Product suggestions</h3>
                      {(insightsData.product_suggestions || []).map((suggestion) => (
                        <div className="insight-row" key={suggestion.product_id}>
                          <div><strong>{formatLabel(suggestion.category || "Product")}</strong><p>{suggestion.product_id}</p><span>{suggestion.reason || "Suggested by existing recommendation output"}</span></div>
                          <strong>{formatNumber(suggestion.score)}</strong>
                        </div>
                      ))}
                      {!insightsData.product_suggestions?.length && <p>No product suggestions available.</p>}
                    </div>
                  </div>
                </>
              ) : (
                <div className="loading-panel">Insights are not available yet.</div>
              )}
            </section>
            <section className="section-block">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">MACHINE LEARNING</p>
                  <h2>Analytics summary</h2>
                </div>
              </div>

              <div className="summary-grid">
                <button
                  className="summary-card"
                  onClick={() => setActiveSection("segments")}
                >
                  <span className="summary-icon purple">â—Ž</span>
                  <span className="summary-title">Customer Segmentation</span>
                  <span className="summary-description">
                    Explore customer groups and cluster distributions.
                  </span>
                  <span className="summary-link">View segments â†’</span>
                </button>

                <button
                  className="summary-card"
                  onClick={() => setActiveSection("forecast")}
                >
                  <span className="summary-icon blue">â†—</span>
                  <span className="summary-title">Revenue Forecast</span>
                  <span className="summary-description">
                    Review the forecasts produced by your models.
                  </span>
                  <span className="summary-link">View forecasts â†’</span>
                </button>

                <button
                  className="summary-card"
                  onClick={() => setActiveSection("comparison")}
                >
                  <span className="summary-icon orange">â–¥</span>
                  <span className="summary-title">Model Comparison</span>
                  <span className="summary-description">
                    Compare forecasting model error metrics.
                  </span>
                  <span className="summary-link">Compare models â†’</span>
                </button>
              </div>
            </section>
          </>
        )}

        {activeSection === "segments" && (
          <section className="section-block">
            <div className="section-heading">
              <div>
                <p className="eyebrow">CUSTOMER ANALYTICS</p>
                <h2>Customer segmentation</h2>
                <p className="section-description">
                  Customer groups generated by your segmentation pipeline.
                </p>
              </div>
            </div>

            {analyticsLoading && !segmentsData && (
              <div className="loading-panel">Loading customer segments...</div>
            )}

            {segmentsData && (
              <>
                <div className="mini-stats">
                  <MetricCard
                    title="Customers Segmented"
                    value={formatNumber(
                      segmentsData.total_customers ??
                        segmentsData.customers_segmented ??
                        segmentsData.total ??
                        0
                    )}
                  />
                  <MetricCard
                    title="Number of Clusters"
                    value={formatNumber(
                      segmentsData.number_of_clusters ??
                        segmentsData.number_of_segments ??
                        segmentsData.n_clusters ??
                        getRows(segmentsData, "segments").length
                    )}
                  />
                </div>

                <div className="segment-analysis-grid">
                  {segmentsData.segments?.map((segment) => {
                    const total = Number(segmentsData.total_customers || 0);
                    const count = Number(segment.customer_count || 0);
                    const percentage = total > 0 ? (count / total) * 100 : 0;

                    return (
                      <article className="segment-analysis-card" key={segment.hierarchical_cluster}>
                        <div className="segment-card-heading">
                          <span>{segment.segment_name || `Cluster ${segment.hierarchical_cluster}`}</span>
                          <strong>{formatNumber(count)}</strong>
                        </div>
                        <div className="segment-bar-track">
                          <div className="segment-bar-fill" style={{ width: `${percentage}%` }} />
                        </div>
                        <p>{percentage.toFixed(1)}% of all customers</p>
                      </article>
                    );
                  })}
                </div>

                <div className="data-panel segment-marketing-panel">
                  <h3>Marketing insights</h3>
                  <div className="segment-insight-item">
                    <strong>Re-engage one-time customers</strong>
                    <p>Recent One-Time Customers are the largest group. Test follow-up campaigns and relevant product offers to encourage a second purchase.</p>
                  </div>
                  <div className="segment-insight-item">
                    <strong>Win back inactive customers</strong>
                    <p>Consider targeted reactivation campaigns for Inactive / Low-Value Customers, then measure whether they return.</p>
                  </div>
                  <div className="segment-insight-item">
                    <strong>Retain high-value repeat customers</strong>
                    <p>Consider loyalty rewards and personalized recommendations for Repeat High-Value Customers.</p>
                  </div>
                  <p className="data-footnote">These are suggested actions based on segment labels and sizes, not measured campaign results.</p>
                </div>
                <div className="data-panel">
                  <DataTable
                    data={segmentsData}
                    type="segments"
                    emptyMessage="The endpoint returned data, but no segment rows were found."
                  />
                </div>

                <details className="raw-details">
                  <summary>View original API response</summary>
                  <p className="data-footnote">
                    Raw values are shown as returned by the backend.
                  </p>
                  <pre className="json-output">
                    {JSON.stringify(segmentsData, null, 2)}
                  </pre>
                </details>
              </>
            )}
          </section>
        )}

        {activeSection === "forecast" && (
          <section className="section-block">
            <div className="section-heading">
              <div>
                <p className="eyebrow">REVENUE PREDICTION</p>
                <h2>Revenue forecasts</h2>
                <p className="section-description">
                  Monetary forecast values are converted to INR using the
                  configured BRL exchange rate.
                </p>
              </div>
            </div>

            {analyticsLoading && !forecastData && (
              <div className="loading-panel">Loading forecasts...</div>
            )}

            <div className="forecast-chart-controls" data-feature="forecast-chart-controls">
  <div className="forecast-control">
    <label htmlFor="forecast-model">Forecast model</label>
    <select
      id="forecast-model"
      value={forecastModel}
      onChange={(event) => setForecastModel(event.target.value)}
    >
      <option value="random_forest_forecast">Random Forest</option>
      <option value="xgboost_forecast">XGBoost</option>
      <option value="prophet_forecast">Prophet</option>
    </select>
  </div>

  <div className="forecast-control">
    <label htmlFor="forecast-horizon">Forecast horizon</label>
    <select
      id="forecast-horizon"
      value={forecastHorizon}
      onChange={(event) => setForecastHorizon(event.target.value)}
    >
      <option value="30">Next 30 days</option>
      <option value="60">Next 60 days</option>
      <option value="90">Next 90 days</option>
    </select>
  </div>
</div>

<div className="data-panel forecast-chart-panel">
  <div className="forecast-chart-heading">
    <div>
      <h3>
        {forecastModel === "random_forest_forecast"
          ? "Random Forest"
          : forecastModel === "xgboost_forecast"
            ? "XGBoost"
            : "Prophet"} revenue forecast
      </h3>
      <p className="data-footnote">
        Forecast values are converted from BRL to INR for display.
      </p>
    </div>
    {forecastValues.length > 0 && (
      <div className="forecast-chart-summary">
        <span>Average daily forecast</span>
        <strong>
          {formatBRLAsINR(
            forecastValues.reduce((sum, value) => sum + value, 0) /
              forecastValues.length
          )}
        </strong>
      </div>
    )}
  </div>

  {forecastChartPoints.length > 0 ? (
    <div className="forecast-chart-scroll">
      <svg
        className="forecast-line-chart"
        viewBox={`0 0 ${chartWidth} ${chartHeight}`}
        role="img"
        aria-label="Revenue forecast line chart"
      >
        {[0, 1, 2, 3, 4].map((tick) => {
          const y = chartPadding +
            tick * (chartHeight - chartPadding * 2) / 4;
          return (
            <line
              key={tick}
              x1={chartPadding}
              y1={y}
              x2={chartWidth - chartPadding}
              y2={y}
              className="forecast-grid-line"
            />
          );
        })}
        <polyline
          points={forecastChartPoints
            .map((point) => `${point.x},${point.y}`)
            .join(" ")}
          className="forecast-line"
        />
        {forecastChartPoints.map((point, index) => (
          <circle
            key={`${point.date}-${index}`}
            cx={point.x}
            cy={point.y}
            r="3"
            className="forecast-chart-point"
          >
            <title>
              {point.date}: {formatBRLAsINR(point.value)}
            </title>
          </circle>
        ))}
      </svg>
      <div className="forecast-chart-labels">
        <span>{visibleForecastRows[0]?.ds}</span>
        <span>{visibleForecastRows[visibleForecastRows.length - 1]?.ds}</span>
      </div>
    </div>
  ) : (
    <p className="empty-message">No forecast values are available for this model.</p>
  )}

  <p className="data-footnote">
    Hover over a chart point to view its date and predicted value.
    Historical actuals are not included in this forecast API response.
  </p>
</div>
{forecastData && (
              <div className="data-panel">
                <DataTable
                  data={forecastData}
                  type="forecast"
                  emptyMessage="No forecast rows were returned."
                />
                <details className="raw-details">
                  <summary>View original API response (BRL values)</summary>
                  <pre className="json-output">
                    {JSON.stringify(forecastData, null, 2)}
                  </pre>
                </details>
              </div>
            )}
          </section>
        )}

                {activeSection === "churn" && (
          <section className="section-block">
            <div className="section-heading">
              <div>
                <p className="eyebrow">CUSTOMER RETENTION</p>
                <h2>Churn Prediction</h2>
                <p className="section-description">
                  Review the risk categories produced by the existing churn prediction output.
                </p>
              </div>
            </div>

            {insightsData?.churn ? (
              <>
                <div className="ai-summary-grid">
                  <div className="data-panel ai-summary-card">
                    <span>Total predictions</span>
                    <strong>{formatNumber(insightsData.churn.total_predictions)}</strong>
                  </div>
                  {Object.entries(insightsData.churn.risk_counts || {}).map(([risk, count]) => (
                    <div className="data-panel ai-summary-card" key={risk}>
                      <span>{formatLabel(risk)} risk</span>
                      <strong>{formatNumber(count)}</strong>
                      <span>
                        {insightsData.churn.total_predictions
                          ? `${((Number(count) / insightsData.churn.total_predictions) * 100).toFixed(1)}% of predictions`
                          : "No predictions"}
                      </span>
                    </div>
                  ))}
                </div>
                              <div className="data-panel ai-chart-panel">
                <h3>Churn risk distribution</h3>
                <p className="data-footnote">
                  Share of customers in each risk category.
                </p>
                <DonutChart
                  items={Object.entries(insightsData.churn.risk_counts || {})}
                  total={Number(insightsData.churn.total_predictions) || 0}
                />
              </div>
<div className="data-panel ai-explanation">
                  <h3>Recommended actions</h3>
                  <ul>
                    <li><strong>High risk:</strong> Prioritize personal outreach and investigate reasons for reduced engagement.</li>
                    <li><strong>Medium risk:</strong> Try relevant offers and timely follow-ups.</li>
                    <li><strong>Low risk:</strong> Maintain service quality and encourage repeat purchases.</li>
                  </ul>
                  <p className="data-footnote">
                    This page displays risk-category totals only. Individual customer records and churn probabilities are not returned by the current dashboard insights endpoint.
                  </p>
                </div>
              </>
            ) : (
              <div className="empty-message">
                {insightsLoading ? "Loading churn insights..." : "Churn summary data is unavailable."}
              </div>
            )}
          </section>
        )}

        {activeSection === "recommendations" && (
          <section className="section-block">
            <div className="section-heading">
              <div>
                <p className="eyebrow">PRODUCT DISCOVERY</p>
                <h2>Product Recommendations</h2>
                <p className="section-description">
                  Review the product suggestions generated by the existing recommendation output.
                </p>
              </div>
            </div>

            {insightsData?.product_suggestions?.length > 0 ? (
              <>
                <div className="ai-summary-grid">
                  <div className="data-panel ai-summary-card">
                    <span>Available suggestions</span>
                    <strong>{formatNumber(insightsData.product_suggestions.length)}</strong>
                  </div>
                </div>
                                <div className="data-panel ai-chart-panel">
                  <h3>Recommendation score comparison</h3>
                  <p className="data-footnote">
                    Scores are shown as returned by the model and are not percentages.
                  </p>
                  <HorizontalBarChart
                    items={insightsData.product_suggestions.map((suggestion, index) => ({
                      label: String(suggestion.product_id ?? `Product ${index + 1}`),
                      detail: formatLabel(suggestion.category || "Product"),
                      value: Number(suggestion.score) || 0,
                    }))}
                    formatValue={(value) => value.toFixed(3)}
                  />
                </div>
<div className="ai-recommendation-grid">
                  {insightsData.product_suggestions.map((suggestion, index) => (
                    <article className="data-panel ai-recommendation-card"
                      key={suggestion.product_id ?? `suggestion-${index}`}>
                      <span className="eyebrow">SUGGESTION {index + 1}</span>
                      <h3>{formatLabel(suggestion.category || "Product")}</h3>
                      <p className="ai-product-id">
                        Product ID: {suggestion.product_id ?? "Not provided"}
                      </p>
                      <p>{suggestion.reason || "Suggested by the existing recommendation output."}</p>
                      {suggestion.score != null && (
                        <div className="ai-score">
                          <span>Recommendation score</span>
                          <strong>{formatNumber(suggestion.score)}</strong>
                        </div>
                      )}
                    </article>
                  ))}
                </div>
                <p className="data-footnote">
                  Suggestions and scores are displayed as returned by the backend; the score is not assumed to be a percentage.
                </p>
              </>
            ) : (
              <div className="empty-message">
                {insightsLoading ? "Loading product suggestions..." : "No product suggestions are currently available."}
              </div>
            )}
          </section>
        )}

        {activeSection === "anomalies" && (
          <section className="section-block">
            <div className="section-heading">
              <div>
                <p className="eyebrow">SALES MONITORING</p>
                <h2>Anomaly Detection</h2>
                <p className="section-description">
                  Review the severity distribution from the existing anomaly detection results.
                </p>
              </div>
            </div>

            {insightsData?.anomalies ? (
              <>
                <div className="ai-summary-grid">
                  <div className="data-panel ai-summary-card">
                    <span>Total alerts</span>
                    <strong>{formatNumber(insightsData.anomalies.total_alerts)}</strong>
                  </div>
                  {Object.entries(insightsData.anomalies.severity_counts || {}).map(([severity, count]) => (
                    <div className="data-panel ai-summary-card" key={severity}>
                      <span>{formatLabel(severity)} severity</span>
                      <strong>{formatNumber(count)}</strong>
                      <span>
                        {insightsData.anomalies.total_alerts
                          ? `${((Number(count) / insightsData.anomalies.total_alerts) * 100).toFixed(1)}% of alerts`
                          : "No alerts"}
                      </span>
                    </div>
                  ))}
                </div>
                              <div className="data-panel ai-chart-panel">
                <h3>Alerts by severity</h3>
                <p className="data-footnote">
                  Compare the number of alerts in each severity category.
                </p>
                <HorizontalBarChart
                  items={Object.entries(insightsData.anomalies.severity_counts || {}).map(
                    ([severity, count]) => ({
                      label: `${formatLabel(severity)} severity`,
                      value: Number(count) || 0,
                    })
                  )}
                  formatValue={(value) => formatNumber(value)}
                />
              </div>
<div className="data-panel ai-explanation">
                  <h3>Suggested review workflow</h3>
                  <ul>
                    <li>Review high-severity alerts first.</li>
                    <li>Compare flagged activity with the original transaction and sales records before taking action.</li>
                    <li>Document investigated alerts and confirmed causes for follow-up.</li>
                  </ul>
                  <p className="data-footnote">
                    The current endpoint returns alert totals by severity, not individual alert records or timestamps. These counts should not be interpreted as confirmed fraud.
                  </p>
                </div>
              </>
            ) : (
              <div className="empty-message">
                {insightsLoading ? "Loading anomaly insights..." : "Anomaly summary data is unavailable."}
              </div>
            )}
          </section>
        )}
{activeSection === "reports" && (
          <AnalyticsReports
            insightsData={insightsData}
            forecastData={forecastData}
            comparisonData={comparisonData}
            segmentsData={segmentsData}
          />
        )}

        {activeSection === "comparison" && (
          <section className="section-block">
            <div className="section-heading">
              <div>
                <p className="eyebrow">MODEL EVALUATION</p>
                <h2>Forecast model comparison</h2>
                <p className="section-description">
                  MAE and RMSE are converted to INR. MAPE remains a percentage.
                </p>
              </div>
            </div>

            {analyticsLoading && !comparisonData && (
              <div className="loading-panel">Loading model comparison...</div>
            )}

            {comparisonData && (
              <div className="data-panel">
                <DataTable
                  data={comparisonData}
                  type="comparison"
                  emptyMessage="No model comparison rows were returned."
                />
                <details className="raw-details">
                  <summary>View original API response (BRL metrics)</summary>
                  <pre className="json-output">
                    {JSON.stringify(comparisonData, null, 2)}
                  </pre>
                </details>
              </div>
            )}
          </section>
        )}

        {activeSection === "sales" && (
          <section className="section-block">
            <div className="section-heading">
              <div>
                <p className="eyebrow">HISTORICAL SALES DATA</p>
                <h2>Sales records</h2>
                <p className="section-description">
                  Sales figures are from sales_analytics.csv. Amounts are
                  displayed in Brazilian reais (BRL).
                </p>
              </div>
            </div>

            {salesError && (
              <div className="alert alert-error page-alert">
                <strong>Sales error:</strong> {salesError}
              </div>
            )}

            {salesSummary && (
              <div className="kpi-grid">
                <MetricCard
                  title="Delivered Sales"
                  value={new Intl.NumberFormat("pt-BR", {
                    style: "currency",
                    currency: "BRL",
                  }).format(salesSummary.total_sales || 0)}
                  description="Delivered line-item value"
                />
                <MetricCard
                  title="Delivered Orders"
                  value={formatNumber(salesSummary.delivered_orders)}
                  description="Distinct delivered orders"
                />
                <MetricCard
                  title="Average Item Value"
                  value={new Intl.NumberFormat("pt-BR", {
                    style: "currency",
                    currency: "BRL",
                  }).format(salesSummary.average_item_value || 0)}
                  description="Average delivered line-item value"
                />
                <MetricCard
                  title="All Sales Records"
                  value={formatNumber(salesSummary.total_records)}
                  description="All order statuses"
                />
              </div>
            )}

            <form
              className="sales-filters"
              onSubmit={(event) => {
                event.preventDefault();
                setSalesOffset(0);
                loadSalesRecords(0, salesSearch, salesStatus);
              }}
            >
              <input
                type="search"
                aria-label="Search sales records"
                placeholder="Search order, customer, or product ID"
                value={salesSearch}
                onChange={(event) => setSalesSearch(event.target.value)}
              />

              <select
                aria-label="Filter by order status"
                value={salesStatus}
                onChange={(event) => setSalesStatus(event.target.value)}
              >
                <option value="">All statuses</option>
                <option value="delivered">Delivered</option>
                <option value="shipped">Shipped</option>
                <option value="canceled">Canceled</option>
                <option value="invoiced">Invoiced</option>
                <option value="processing">Processing</option>
                <option value="unavailable">Unavailable</option>
                <option value="approved">Approved</option>
              </select>

              <button
                type="submit"
                className="secondary-button"
                disabled={salesLoading}
              >
                Search / Filter
              </button>
            </form>

            <div className="data-panel">
              {salesLoading ? (
                <div className="loading-panel">Loading sales records...</div>
              ) : salesRecords.length === 0 ? (
                <div className="loading-panel">
                  No sales records match these filters.
                </div>
              ) : (
                <div className="sales-table-wrap">
                  <table className="sales-table">
                    <thead>
                      <tr>
                        <th>Order ID</th>
                        <th>Customer ID</th>
                        <th>Product ID</th>
                        <th>Category</th>
                        <th>Status</th>
                        <th>Purchase date</th>
                        <th>Item value (BRL)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {salesRecords.map((record, index) => (
                        <tr
                          key={`${record.order_id}-${record.product_id}-${index}`}
                        >
                          <td>{record.order_id}</td>
                          <td>{record.customer_id}</td>
                          <td>{record.product_id}</td>
                          <td>
                            {record.product_category_name_english || "Unknown"}
                          </td>
                          <td>
                            <span className="sales-status">
                              {record.order_status}
                            </span>
                          </td>
                          <td>{record.order_purchase_timestamp}</td>
                          <td>
                            {new Intl.NumberFormat("pt-BR", {
                              style: "currency",
                              currency: "BRL",
                            }).format(Number(record.total_item_value || 0))}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="sales-pagination">
              <span>
                {salesTotal === 0
                  ? "0 records"
                  : `Showing ${salesOffset + 1}?${Math.min(
                      salesOffset + salesRecords.length,
                      salesTotal
                    )} of ${formatNumber(salesTotal)} records`}
              </span>
              <div>
                <button
                  type="button"
                  className="secondary-button"
                  disabled={salesLoading || salesOffset === 0}
                  onClick={() => {
                    const nextOffset = Math.max(0, salesOffset - 25);
                    setSalesOffset(nextOffset);
                    loadSalesRecords(nextOffset, salesSearch, salesStatus);
                  }}
                >
                  Previous
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  disabled={
                    salesLoading || salesOffset + 25 >= salesTotal
                  }
                  onClick={() => {
                    const nextOffset = salesOffset + 25;
                    setSalesOffset(nextOffset);
                    loadSalesRecords(nextOffset, salesSearch, salesStatus);
                  }}
                >
                  Next
                </button>
              </div>
            </div>
          </section>
        )}

        {analyticsError && (
          <div className="alert alert-warning page-alert">
            <strong>Some analytics could not be loaded.</strong>
            <p>{analyticsError}</p>
            <p>
              Your dashboard KPIs can still work even if an analytics endpoint
              has a separate issue.
            </p>
          </div>
        )}

        <footer className="app-footer">
          <span>MarketMind AI</span>
          <span>Sales intelligence and analytics</span>
        </footer>
      </main>
    </div>
  );
}

export default App;


