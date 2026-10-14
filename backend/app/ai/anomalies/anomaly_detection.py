from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore", category=RuntimeWarning)

ROOT = Path(__file__).resolve().parents[4]
SALES_PATH = ROOT / "data/analytical/sales_analytics.csv"
INVENTORY_PATH = ROOT / "data/analytical/inventory_analytics.csv"
OUTPUT_PATH = ROOT / "data/analytical/anomaly_alerts.csv"

CONTAMINATION = 0.01
LOW_QUANTILE = 0.005
HIGH_QUANTILE = 0.995


def statistical_flags(df, columns):
    """Flag extreme values outside the 0.5th–99.5th percentiles."""
    flags = pd.DataFrame(index=df.index)
    reasons = pd.Series("", index=df.index, dtype="object")

    for col in columns:
        if col not in df.columns:
            continue

        values = pd.to_numeric(df[col], errors="coerce")
        valid = values.replace([np.inf, -np.inf], np.nan).dropna()

        if len(valid) < 100 or valid.nunique() < 2:
            continue

        lower = valid.quantile(LOW_QUANTILE)
        upper = valid.quantile(HIGH_QUANTILE)
        flag = values.notna() & ((values < lower) | (values > upper))

        flags[col] = flag
        reasons.loc[flag] = reasons.loc[flag].apply(
            lambda old: f"{old}; statistical outlier: {col}".strip("; ")
        )

    count = flags.sum(axis=1) if not flags.empty else pd.Series(0, index=df.index)
    return count.astype(int), reasons


def detect_anomalies(df, source, features, statistical_columns, record_ids):
    """Fit Isolation Forest and combine its flags with statistical signals."""
    X = df[features].apply(pd.to_numeric, errors="coerce")
    X = X.replace([np.inf, -np.inf], np.nan)

    # Remove features that contain no usable numeric data.
    features = [
        col for col in features
        if X[col].notna().any() and X[col].nunique(dropna=True) > 1
    ]
    X = X[features]

    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("model", IsolationForest(
            n_estimators=200,
            contamination=CONTAMINATION,
            random_state=42,
            n_jobs=-1,
        )),
    ])

    pipeline.fit(X)
    model = pipeline.named_steps["model"]

    isolation_flag = model.predict(X) == -1
    anomaly_score = -model.decision_function(X)

    statistical_count, statistical_reasons = statistical_flags(
        df, statistical_columns
    )

    # Domain rules supplement the two general-purpose detectors.
    rule_reasons = pd.Series("", index=df.index, dtype="object")

    def add_rule(mask, reason):
        mask = pd.Series(mask, index=df.index).fillna(False).astype(bool)
        rule_reasons.loc[mask] = rule_reasons.loc[mask].apply(
            lambda old: f"{old}; {reason}".strip("; ")
        )

    if source == "sales":
        add_rule(
            (df["price"] <= 0) | (df["freight_value"] < 0)
            | (df["total_item_value"] <= 0),
            "non-positive sale amount or negative freight",
        )
    else:
        stock = pd.to_numeric(df["Inventory Level"], errors="coerce")
        demand = pd.to_numeric(df["Demand Forecast"], errors="coerce")
        estimated_stock = pd.to_numeric(
            df["estimated_stock_after_sales"], errors="coerce"
        )
        ratio = pd.to_numeric(
            df["inventory_to_demand_ratio"], errors="coerce"
        )

        add_rule(
            estimated_stock < 0,
            "estimated stock becomes negative after sales",
        )
        add_rule(
            (stock <= 0) & (demand > 0),
            "zero or negative inventory with positive forecast demand",
        )
        

    # Require corroborating signals to avoid overwhelming users with alerts.
    # Strong domain rules are included directly.
    alert_mask = (
        (isolation_flag & (statistical_count >= 2))
        | (statistical_count >= 3)
        | (rule_reasons != "")
    )

    reasons = []
    for i in range(len(df)):
        parts = []
        if isolation_flag[i]:
            parts.append("Isolation Forest anomaly")
        if statistical_reasons.iloc[i]:
            parts.append(statistical_reasons.iloc[i])
        if rule_reasons.iloc[i]:
            parts.append(rule_reasons.iloc[i])
        reasons.append("; ".join(parts))

    alert_rows = df.loc[alert_mask].copy()
    alert_rows.insert(0, "source_type", source)
    alert_rows.insert(1, "record_id", record_ids.loc[alert_mask].astype(str))
    alert_rows["anomaly_score"] = anomaly_score[alert_mask]
    alert_rows["isolation_forest_flag"] = isolation_flag[alert_mask]
    alert_rows["statistical_flag_count"] = statistical_count.loc[alert_mask]
    alert_rows["alert_reasons"] = np.array(reasons, dtype=object)[alert_mask]

    alert_rows["alert_severity"] = np.where(
        (rule_reasons.loc[alert_mask] != "")
        | (statistical_count.loc[alert_mask] >= 3),
        "High",
        "Medium",
    )

    print(f"\n{source.upper()} RESULTS")
    print(f"Records analyzed: {len(df):,}")
    print(f"Isolation Forest flags: {int(isolation_flag.sum()):,}")
    print(f"Records generating alerts: {len(alert_rows):,}")

    return alert_rows


def main():
    print("=" * 60)
    print("MARKETMIND AI - ANOMALY DETECTION")
    print("=" * 60)

    if not SALES_PATH.exists():
        raise FileNotFoundError(f"Sales dataset not found: {SALES_PATH}")
    if not INVENTORY_PATH.exists():
        raise FileNotFoundError(
            f"Inventory dataset not found: {INVENTORY_PATH}"
        )

    sales = pd.read_csv(SALES_PATH)
    inventory = pd.read_csv(INVENTORY_PATH)

    sales_features = [
        "price", "freight_value", "total_item_value",
        "product_weight_g", "delivery_days",
        "estimated_delivery_days", "delivery_delay_days",
        "is_late_delivery", "purchase_hour",
    ]
    sales_stats = [
        "price", "freight_value", "total_item_value",
        "product_weight_g", "delivery_days", "delivery_delay_days",
    ]

    inventory_features = [
        "Inventory Level", "Units Sold", "Units Ordered",
        "Demand Forecast", "Price", "Discount",
        "estimated_stock_after_sales", "inventory_to_demand_ratio",
        "forecast_error", "absolute_forecast_error",
        "stockout_risk", "high_demand",
        "price_difference_competitor",
    ]
    inventory_stats = [
        "Inventory Level", "Units Sold", "Units Ordered",
        "Demand Forecast", "inventory_to_demand_ratio",
        "forecast_error", "absolute_forecast_error",
        "price_difference_competitor",
    ]

    sales_ids = (
        sales["order_id"].astype(str) + "-" +
        sales["order_item_id"].astype(str)
    )
    inventory_ids = (
        inventory["Date"].astype(str) + "-" +
        inventory["Store ID"].astype(str) + "-" +
        inventory["Product ID"].astype(str)
    )

    sales_alerts = detect_anomalies(
        sales, "sales", sales_features, sales_stats, sales_ids
    )
    inventory_alerts = detect_anomalies(
        inventory, "inventory", inventory_features,
        inventory_stats, inventory_ids
    )

    alerts = pd.concat(
        [sales_alerts, inventory_alerts],
        ignore_index=True,
        sort=False,
    )

    if not alerts.empty:
        alerts["_severity_order"] = alerts["alert_severity"].map(
            {"High": 0, "Medium": 1}
        )
        alerts = alerts.sort_values(
            ["_severity_order", "statistical_flag_count", "anomaly_score"],
            ascending=[True, False, False],
        ).drop(columns="_severity_order")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    alerts.to_csv(OUTPUT_PATH, index=False)

    print("\n" + "=" * 60)
    print("ANOMALY DETECTION SUMMARY")
    print("=" * 60)
    print(f"Total alerts: {len(alerts):,}")
    if not alerts.empty:
        print("\nAlerts by source:")
        print(alerts["source_type"].value_counts().to_string())
        print("\nAlerts by severity:")
        print(alerts["alert_severity"].value_counts().to_string())
        print("\nSample alerts:")
        preview = [
            c for c in [
                "source_type", "record_id", "alert_severity",
                "anomaly_score", "statistical_flag_count", "alert_reasons",
            ] if c in alerts.columns
        ]
        print(alerts[preview].head(10).to_string(index=False))

    print(f"\nSaved alerts: {OUTPUT_PATH}")
    print("\nAlerts indicate unusual activity for review, not confirmed fraud.")


if __name__ == "__main__":
    main()
