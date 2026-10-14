
import { useCallback, useEffect, useState } from "react";
import "./App.css";

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
};

const numberFormatter = new Intl.NumberFormat("en-IN");

const currencyFormatter = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

function formatNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? numberFormatter.format(number) : "—";
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

  return Number.isFinite(amount) ? currencyFormatter.format(amount) : "—";
}

// Use this for monetary values received from the API in BRL.
function formatBRLAsINR(value) {
  const convertedAmount = convertBRLToINR(value);

  return convertedAmount === null ? "—" : formatINR(convertedAmount);
}

// Convert and format monetary columns in forecast/comparison tables.
// MAPE, dates, model names, customer counts, and other non-monetary
// values are deliberately left unchanged.
function formatTableValue(key, value) {
  if (value === null || value === undefined || value === "") {
    return "—";
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
            full_name: fullName,
            email,
            password,
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
  const [segmentsData, setSegmentsData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [comparisonData, setComparisonData] = useState(null);

  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [dashboardError, setDashboardError] = useState("");
  const [analyticsError, setAnalyticsError] = useState("");

  const [activeSection, setActiveSection] = useState("overview");

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


  useEffect(() => {
    if (!token) return;

    loadDashboard();
    loadAnalytics();
  }, [token, loadDashboard, loadAnalytics]);

  if (!token) {
    return <AuthScreen onAuthenticated={handleAuthenticated} />;
  }

  const kpis = [
    {
      title: "Total Sales",
      value:
        dashboardData?.total_sales != null
          ? formatBRLAsINR(dashboardData.total_sales)
          : "—",
      description: "Delivered sales, including freight (converted to INR)",
    },
    {
      title: "Total Orders",
      value:
        dashboardData?.total_orders != null
          ? formatNumber(dashboardData.total_orders)
          : "—",
      description: "Distinct delivered orders",
    },
    {
      title: "Total Customers",
      value:
        dashboardData?.total_customers != null
          ? formatNumber(dashboardData.total_customers)
          : "—",
      description: "Unique customers",
    },
    {
      title: "Total Products",
      value:
        dashboardData?.total_products != null
          ? formatNumber(dashboardData.total_products)
          : "—",
      description: "Distinct products",
    },
  ];

  const navigation = [
    { id: "overview", label: "Overview" },
    { id: "segments", label: "Customer Segmentation" },
    { id: "forecast", label: "Revenue Forecast" },
    { id: "comparison", label: "Model Comparison" },
  ];

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
          {navigation.map((item) => (
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
            }}
            disabled={dashboardLoading || analyticsLoading}
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
              <div className="welcome-symbol">↗</div>
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
                  <p className="eyebrow">MACHINE LEARNING</p>
                  <h2>Analytics summary</h2>
                </div>
              </div>

              <div className="summary-grid">
                <button
                  className="summary-card"
                  onClick={() => setActiveSection("segments")}
                >
                  <span className="summary-icon purple">◎</span>
                  <span className="summary-title">Customer Segmentation</span>
                  <span className="summary-description">
                    Explore customer groups and cluster distributions.
                  </span>
                  <span className="summary-link">View segments →</span>
                </button>

                <button
                  className="summary-card"
                  onClick={() => setActiveSection("forecast")}
                >
                  <span className="summary-icon blue">↗</span>
                  <span className="summary-title">Revenue Forecast</span>
                  <span className="summary-description">
                    Review the forecasts produced by your models.
                  </span>
                  <span className="summary-link">View forecasts →</span>
                </button>

                <button
                  className="summary-card"
                  onClick={() => setActiveSection("comparison")}
                >
                  <span className="summary-icon orange">▥</span>
                  <span className="summary-title">Model Comparison</span>
                  <span className="summary-description">
                    Compare forecasting model error metrics.
                  </span>
                  <span className="summary-link">Compare models →</span>
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

