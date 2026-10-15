from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import require_permission


router = APIRouter(prefix="/api/sales", tags=["Sales"])

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SALES_FILE = PROJECT_ROOT / "data" / "analytical" / "sales_analytics.csv"

REQUIRED_COLUMNS = {
    "order_id",
    "customer_id",
    "product_id",
    "order_status",
    "order_purchase_timestamp",
    "product_category_name_english",
    "price",
    "freight_value",
    "total_item_value",
}


def load_sales() -> pd.DataFrame:
    if not SALES_FILE.exists():
        raise HTTPException(
            status_code=503,
            detail="Historical sales dataset is not available.",
        )

    try:
        df = pd.read_csv(SALES_FILE)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Could not read the historical sales dataset.",
        ) from exc

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=500,
            detail=f"Sales dataset is missing required columns: {sorted(missing)}",
        )

    for column in ("price", "freight_value", "total_item_value"):
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df


@router.get("/summary")
def sales_summary(
    _user=Depends(require_permission("dashboard:view")),
):
    df = load_sales()
    delivered = df[df["order_status"].eq("delivered")]

    return {
        "source": "sales_analytics.csv",
        "currency": "BRL",
        "total_records": int(len(df)),
        "delivered_line_items": int(len(delivered)),
        "delivered_orders": int(delivered["order_id"].nunique()),
        "total_sales": round(
            float(delivered["total_item_value"].sum()), 2
        ),
        "average_item_value": round(
            float(delivered["total_item_value"].mean()), 2
        ) if not delivered.empty else 0,
        "order_status_counts": {
            str(key): int(value)
            for key, value in df["order_status"].fillna("unknown")
            .value_counts().items()
        },
    }


@router.get("/records")
def sales_records(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None, max_length=50),
    search: str | None = Query(default=None, max_length=100),
    _user=Depends(require_permission("dashboard:view")),
):
    df = load_sales()

    if status and status.strip():
        df = df[
            df["order_status"].str.casefold()
            == status.strip().casefold()
        ]

    if search and search.strip():
        term = search.strip()
        mask = pd.Series(False, index=df.index)

        for column in ("order_id", "customer_id", "product_id"):
            mask |= df[column].astype(str).str.contains(
                term, case=False, regex=False, na=False
            )

        df = df[mask]

    total = len(df)

    df = df.sort_values(
        "order_purchase_timestamp",
        ascending=False,
        na_position="last",
    )

    columns = [
        "order_id",
        "customer_id",
        "product_id",
        "product_category_name_english",
        "order_status",
        "order_purchase_timestamp",
        "price",
        "freight_value",
        "total_item_value",
    ]

    page = df.iloc[offset:offset + limit][columns].copy()
    page = page.astype(object).where(pd.notna(page), None)

    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "records": page.to_dict(orient="records"),
    }

