
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from app.auth.database_models import User
from app.auth.dependencies import require_permission


router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"],
)

# Project root: D:\project\MarketMind-AI
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "analytical"


def load_csv(filename: str) -> pd.DataFrame:
    file_path = DATA_DIR / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"Reporting data file not found: {filename}",
        )

    try:
        return pd.read_csv(file_path)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not read reporting data file: {filename}",
        ) from exc


def check_access(
    current_user: User = Depends(
        require_permission("dashboard:view")
    ),
):
    return current_user


@router.get("/segments")
def get_customer_segments(
    current_user: User = Depends(check_access),
):
    df = load_csv("customer_segments_hierarchical.csv")

    required = {
        "customer_unique_id",
        "hierarchical_cluster",
        "segment_name",
    }

    if not required.issubset(df.columns):
        raise HTTPException(
            status_code=500,
            detail="Customer segmentation CSV is missing required columns.",
        )

    distribution = (
        df.groupby(["hierarchical_cluster", "segment_name"])
        .size()
        .reset_index(name="customer_count")
    )

    return {
        "total_customers": int(df["customer_unique_id"].nunique()),
        "number_of_segments": int(df["hierarchical_cluster"].nunique()),
        "segments": distribution.to_dict(orient="records"),
    }


@router.get("/forecast")
def get_revenue_forecast(
    current_user: User = Depends(check_access),
):
    df = load_csv("future_revenue_forecasts.csv")

    required = {
        "ds",
        "xgboost_forecast",
        "random_forest_forecast",
        "prophet_forecast",
    }

    if not required.issubset(df.columns):
        raise HTTPException(
            status_code=500,
            detail="Revenue forecast CSV is missing required columns.",
        )

    df = df.astype(object).where(pd.notna(df), None)

    return {
        "forecast_days": len(df),
        "forecasts": df.to_dict(orient="records"),
    }


@router.get("/model-comparison")
def get_model_comparison(
    current_user: User = Depends(check_access),
):
    df = load_csv("forecast_model_comparison.csv")

    required = {"model", "MAE", "RMSE", "MAPE"}

    if not required.issubset(df.columns):
        raise HTTPException(
            status_code=500,
            detail="Model comparison CSV is missing required columns.",
        )

    df = df.astype(object).where(pd.notna(df), None)

    return {
        "models_evaluated": len(df),
        "metrics": df.to_dict(orient="records"),
    }
