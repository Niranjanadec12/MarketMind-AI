from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from app.auth.database_models import User
from app.auth.dependencies import require_permission


router = APIRouter(
    prefix="/api/analytics",
    tags=["Dashboard Insights"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "analytical"


def read_csv(filename, required_columns=None):
    path = DATA_DIR / filename

    if not path.is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Analytics file not found: {filename}",
        )

    try:
        df = pd.read_csv(path)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not read analytics file: {filename}",
        ) from exc

    if required_columns:
        missing = set(required_columns) - set(df.columns)
        if missing:
            raise HTTPException(
                status_code=503,
                detail=f"{filename} is missing required columns: {sorted(missing)}",
            )

    return df


def clean_records(df):
    return (
        df.astype(object)
        .where(pd.notna(df), None)
        .to_dict(orient="records")
    )


@router.get("/dashboard-insights")
def get_dashboard_insights(
    current_user: User = Depends(
        require_permission("dashboard:view")
    ),
):
    # Historical sales trends: only delivered sales are included.
    sales = read_csv(
        "sales_analytics.csv",
        ["order_id", "order_status", "purchase_date", "total_item_value"],
    )

    sales = sales.loc[
        sales["order_status"].astype(str).str.lower().eq("delivered")
    ].copy()

    sales["purchase_date"] = pd.to_datetime(
        sales["purchase_date"], errors="coerce"
    )
    sales["total_item_value"] = pd.to_numeric(
        sales["total_item_value"], errors="coerce"
    ).fillna(0)

    sales = sales.dropna(subset=["purchase_date"])
    sales["date"] = sales["purchase_date"].dt.strftime("%Y-%m-%d")
    sales["week"] = sales["purchase_date"].dt.to_period("W").astype(str)
    sales["month"] = sales["purchase_date"].dt.to_period("M").astype(str)

    daily = (
        sales.groupby("date", as_index=False)["total_item_value"]
        .sum()
        .rename(columns={"date": "period", "total_item_value": "revenue"})
        .sort_values("period")
        .tail(30)
    )

    weekly = (
        sales.groupby("week", as_index=False)["total_item_value"]
        .sum()
        .rename(columns={"week": "period", "total_item_value": "revenue"})
        .sort_values("period")
        .tail(12)
    )

    monthly = (
        sales.groupby("month", as_index=False)["total_item_value"]
        .sum()
        .rename(columns={"month": "period", "total_item_value": "revenue"})
        .sort_values("period")
        .tail(12)
    )

    # Best-selling products from the existing product analytics output.
    products = read_csv(
        "product_analytics.csv",
        [
            "product_id",
            "product_category_name_english",
            "total_items_sold",
            "total_sales",
        ],
    )

    products["total_sales"] = pd.to_numeric(
        products["total_sales"], errors="coerce"
    ).fillna(0)
    products["total_items_sold"] = pd.to_numeric(
        products["total_items_sold"], errors="coerce"
    ).fillna(0)

    top_products = products.nlargest(5, "total_sales")[
        [
            "product_id",
            "product_category_name_english",
            "total_items_sold",
            "total_sales",
        ]
    ]

    # Inventory is a separate dataset. Report the latest recorded snapshot.
    inventory = read_csv(
        "inventory_analytics.csv",
        [
            "Date",
            "Product ID",
            "Inventory Level",
            "estimated_stock_after_sales",
            "stockout_risk",
        ],
    )

    inventory["Date"] = pd.to_datetime(inventory["Date"], errors="coerce")
    inventory = inventory.dropna(subset=["Date"])
    latest_inventory_date = None
    low_stock_items = 0
    stockout_risk_items = 0

    if not inventory.empty:
        latest_date = inventory["Date"].max()
        latest_inventory_date = latest_date.strftime("%Y-%m-%d")
        latest_inventory = inventory.loc[inventory["Date"] == latest_date].copy()

        latest_inventory["estimated_stock_after_sales"] = pd.to_numeric(
            latest_inventory["estimated_stock_after_sales"],
            errors="coerce",
        )
        latest_inventory["stockout_risk"] = pd.to_numeric(
            latest_inventory["stockout_risk"],
            errors="coerce",
        ).fillna(0)

        low_stock_items = int(
            latest_inventory.loc[
                latest_inventory["estimated_stock_after_sales"] <= 0,
                "Product ID",
            ].nunique()
        )
        stockout_risk_items = int(
            latest_inventory.loc[
                latest_inventory["stockout_risk"] == 1,
                "Product ID",
            ].nunique()
        )

    # Churn prediction summary from the existing model output.
    churn = read_csv(
        "customer_churn_predictions.csv",
        ["customer_unique_id", "risk_category"],
    )
    churn_counts = (
        churn["risk_category"]
        .fillna("Unknown")
        .astype(str)
        .value_counts()
        .to_dict()
    )

    # Existing anomaly detection results.
    anomalies = read_csv(
        "anomaly_alerts.csv",
        ["alert_severity"],
    )
    anomaly_counts = (
        anomalies["alert_severity"]
        .fillna("Unknown")
        .astype(str)
        .value_counts()
        .to_dict()
    )

    # Existing customer segmentation output.
    segments = read_csv(
        "customer_segments_hierarchical.csv",
        ["customer_unique_id", "segment_name"],
    )
    segment_counts = (
        segments.groupby("segment_name")["customer_unique_id"]
        .nunique()
        .sort_values(ascending=False)
        .to_dict()
    )

    # Forecast summary uses the existing forecast file, without retraining.
    forecasts = read_csv(
        "future_revenue_forecasts.csv",
        ["ds", "random_forest_forecast"],
    )
    forecasts["random_forest_forecast"] = pd.to_numeric(
        forecasts["random_forest_forecast"], errors="coerce"
    )
    valid_forecasts = forecasts.dropna(
        subset=["random_forest_forecast"]
    )
    forecast_summary = {
        "forecast_days": int(len(valid_forecasts)),
        "average_daily_forecast_brl": (
            round(float(valid_forecasts["random_forest_forecast"].mean()), 2)
            if not valid_forecasts.empty
            else None
        ),
        "forecast_start": (
            str(valid_forecasts["ds"].min())
            if not valid_forecasts.empty
            else None
        ),
        "forecast_end": (
            str(valid_forecasts["ds"].max())
            if not valid_forecasts.empty
            else None
        ),
        "model": "Random Forest",
    }

    # Optional product suggestions; an empty result is valid.
    suggestions = []
    suggestions_path = DATA_DIR / "customer_sales_suggestions.csv"

    if suggestions_path.is_file():
        try:
            suggestion_df = pd.read_csv(suggestions_path)
            if {"product_id", "score"}.issubset(suggestion_df.columns):
                suggestion_df["score"] = pd.to_numeric(
                    suggestion_df["score"], errors="coerce"
                )
                if "category" not in suggestion_df.columns:
                    suggestion_df["category"] = None
                if "reason" not in suggestion_df.columns:
                    suggestion_df["reason"] = None

                suggestions = clean_records(
                    suggestion_df.dropna(subset=["score"])
                    .nlargest(5, "score")[
                        ["product_id", "category", "score", "reason"]
                    ]
                )
        except Exception:
            suggestions = []

    return {
        "sales_trends": {
            "daily": clean_records(daily),
            "weekly": clean_records(weekly),
            "monthly": clean_records(monthly),
            "currency": "BRL",
            "basis": "Delivered order items, including freight",
        },
        "top_products": clean_records(top_products),
        "inventory": {
            "latest_snapshot_date": latest_inventory_date,
            "low_stock_items": low_stock_items,
            "stockout_risk_items": stockout_risk_items,
            "note": "Counts refer to the latest recorded inventory snapshot, not live stock.",
        },
        "churn": {
            "total_predictions": int(len(churn)),
            "risk_counts": churn_counts,
        },
        "anomalies": {
            "total_alerts": int(len(anomalies)),
            "severity_counts": anomaly_counts,
        },
        "segments": {
            "total_customers": int(segments["customer_unique_id"].nunique()),
            "segment_counts": segment_counts,
        },
        "forecast": forecast_summary,
        "product_suggestions": suggestions,
    }
