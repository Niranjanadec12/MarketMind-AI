
import csv
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from app.auth.database_models import User
from app.auth.dependencies import require_permission

router = APIRouter(
    prefix="/api",
    tags=["Dashboard"]
)

# Project root: D:\project\MarketMind-AI
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "analytical"


@lru_cache(maxsize=1)
def get_real_kpis():
    """Calculate dashboard KPIs from the existing analytical CSV files."""

    sales_file = DATA_DIR / "sales_analytics.csv"
    customers_file = DATA_DIR / "customer_analytics.csv"
    products_file = DATA_DIR / "product_analytics.csv"

    for file_path in (sales_file, customers_file, products_file):
        if not file_path.is_file():
            raise HTTPException(
                status_code=503,
                detail=f"Required analytics file not found: {file_path}"
            )

    # Sales: include only delivered order items.
    # total_item_value includes product price plus freight.
    delivered_sales = 0.0
    delivered_order_ids = set()

    try:
        with sales_file.open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            reader = csv.DictReader(file)

            required_columns = {
                "order_id", "order_status", "total_item_value"
            }
            if not required_columns.issubset(reader.fieldnames or []):
                raise HTTPException(
                    status_code=503,
                    detail="Sales CSV is missing required columns."
                )

            for row in reader:
                if (row.get("order_status") or "").strip().lower() == "delivered":
                    order_id = (row.get("order_id") or "").strip()
                    if order_id:
                        delivered_order_ids.add(order_id)

                    try:
                        delivered_sales += float(
                            row.get("total_item_value") or 0
                        )
                    except ValueError:
                        continue

        # Count unique real-world buyers, not customer records.
        unique_customers = set()
        with customers_file.open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            reader = csv.DictReader(file)
            if "customer_unique_id" not in (reader.fieldnames or []):
                raise HTTPException(
                    status_code=503,
                    detail="Customer CSV is missing customer_unique_id."
                )

            for row in reader:
                customer_id = (row.get("customer_unique_id") or "").strip()
                if customer_id:
                    unique_customers.add(customer_id)

        # Count unique products.
        unique_products = set()
        with products_file.open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            reader = csv.DictReader(file)
            if "product_id" not in (reader.fieldnames or []):
                raise HTTPException(
                    status_code=503,
                    detail="Product CSV is missing product_id."
                )

            for row in reader:
                product_id = (row.get("product_id") or "").strip()
                if product_id:
                    unique_products.add(product_id)

    except HTTPException:
        raise
    except (OSError, csv.Error) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Could not read analytics CSV files: {exc}"
        ) from exc

    return {
        "total_sales": round(delivered_sales, 2),
        "total_orders": len(delivered_order_ids),
        "total_customers": len(unique_customers),
        "total_products": len(unique_products),
        "currency": "BRL",
        "sales_basis": "Delivered order items, including freight"
    }


@router.get("/dashboard")
def get_dashboard(
    current_user: User = Depends(
        require_permission("dashboard:view")
    )
):
    user_roles = [role.name for role in current_user.roles]

    # Keep the existing role-based access and dashboard messages.
    if "Business Owner" in user_roles:
        return {
            "role": "Business Owner",
            "dashboard": "business",
            "message": "Welcome to the Business Owner dashboard",
            **get_real_kpis()
        }

    if "Store Manager" in user_roles:
        kpis = get_real_kpis()
        return {
            "role": "Store Manager",
            "dashboard": "store",
            "message": "Welcome to the Store Manager dashboard",
            "total_sales": kpis["total_sales"],
            "total_orders": kpis["total_orders"],
            "total_products": kpis["total_products"],
            "currency": kpis["currency"]
        }

    if "Sales Executive" in user_roles:
        kpis = get_real_kpis()
        return {
            "role": "Sales Executive",
            "dashboard": "sales",
            "message": "Welcome to the Sales Executive dashboard",
            "total_sales": kpis["total_sales"],
            "total_orders": kpis["total_orders"],
            "total_customers": kpis["total_customers"],
            "currency": kpis["currency"]
        }

    if "Administrator" in user_roles:
        return {
            "role": "Administrator",
            "dashboard": "admin",
            "message": "Welcome to the Administrator dashboard",
            "system_status": "Operational",
            "total_users": 1
        }

    return {
        "role": "Unknown",
        "dashboard": "none",
        "message": "No dashboard access assigned"
    }
