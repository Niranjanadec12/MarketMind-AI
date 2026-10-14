
from pathlib import Path

import pandas as pd

from backend.app.ai.recommendation_engine import (
    ProductRecommendationEngine,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]

SALES_PATH = PROJECT_ROOT / "data" / "analytical" / "sales_analytics.csv"
CUSTOMERS_PATH = PROJECT_ROOT / "data" / "processed" / "customers_clean.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "analytical"

INTERACTIONS_OUTPUT = OUTPUT_DIR / "customer_product_interactions.csv"
RECOMMENDATIONS_OUTPUT = OUTPUT_DIR / "product_recommendations.csv"


def prepare_interactions():
    """Create one row per actual customer-product purchase interaction."""

    sales = pd.read_csv(
        SALES_PATH,
        usecols=[
            "customer_id",
            "product_id",
            "order_id",
            "order_status",
        ],
    )

    customers = pd.read_csv(
        CUSTOMERS_PATH,
        usecols=["customer_id", "customer_unique_id"],
    )

    sales = sales[sales["order_status"] == "delivered"].copy()
    sales = sales.dropna(subset=["customer_id", "product_id"])
    customers = customers.dropna(
        subset=["customer_id", "customer_unique_id"]
    )

    sales["customer_id"] = sales["customer_id"].astype(str)
    sales["product_id"] = sales["product_id"].astype(str)
    customers["customer_id"] = customers["customer_id"].astype(str)
    customers["customer_unique_id"] = (
        customers["customer_unique_id"].astype(str)
    )

    data = sales.merge(
        customers,
        on="customer_id",
        how="left",
        validate="many_to_one",
    )

    data = data.dropna(subset=["customer_unique_id"])

    interactions = (
        data.groupby(["customer_unique_id", "product_id"])
        .agg(
            purchase_count=("order_id", "nunique"),
        )
        .reset_index()
        .rename(
            columns={
                "customer_unique_id": "customer_id",
            }
        )
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    interactions.to_csv(INTERACTIONS_OUTPUT, index=False)

    print(f"Saved interactions: {INTERACTIONS_OUTPUT}")
    print(f"Interaction rows: {len(interactions)}")
    print(f"Customers: {interactions['customer_id'].nunique()}")
    print(f"Products: {interactions['product_id'].nunique()}")

    return interactions


def generate_recommendations(sample_size=100):
    """Train the existing engine and save recommendations for sample customers."""

    engine = ProductRecommendationEngine()
    summary = engine.fit()

    print("\n===== MODEL TRAINING SUMMARY =====")
    for key, value in summary.items():
        print(f"{key}: {value}")

    # Prefer customers with multiple distinct purchased products.
    eligible_customers = [
        customer_id
        for customer_id, products in engine.customer_products.items()
        if len(products) >= 2
    ]

    selected_customers = eligible_customers[:sample_size]
    records = []

    for customer_id in selected_customers:
        recommendations = engine.recommend_for_customer(
            customer_id,
            n=5,
        )

        for rank, item in enumerate(recommendations, start=1):
            records.append(
                {
                    "customer_id": customer_id,
                    "rank": rank,
                    "product_id": item["product_id"],
                    "score": item["score"],
                    "category": item["category"],
                    "reason": item["reason"],
                }
            )

    recommendations_df = pd.DataFrame(records)
    recommendations_df.to_csv(RECOMMENDATIONS_OUTPUT, index=False)

    print(f"\nSaved recommendations: {RECOMMENDATIONS_OUTPUT}")
    print(f"Customers recommended: {len(selected_customers)}")
    print(f"Recommendation rows: {len(recommendations_df)}")

    if not recommendations_df.empty:
        print("\n===== SAMPLE RECOMMENDATIONS =====")
        print(recommendations_df.head(10).to_string(index=False))

    return recommendations_df


def run():
    prepare_interactions()
    generate_recommendations()


if __name__ == "__main__":
    run()
