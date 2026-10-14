import pandas as pd
from pathlib import Path


def load_processed_data():
    """
    Load the existing processed Olist datasets.
    """

    project_root = Path(__file__).resolve().parents[4]
    data_path = project_root / "data" / "processed"

    customers = pd.read_csv(
        data_path / "customers_clean.csv"
    )

    orders = pd.read_csv(
        data_path / "orders_cleaned.csv"
    )

    payments = pd.read_csv(
        data_path / "order_payments_clean.csv"
    )

    return customers, orders, payments


def prepare_segmentation_features():
    """
    Create customer-level segmentation features.

    Features:
    - Purchase Frequency
    - Purchase Value
    - Customer Activity
    """

    customers, orders, payments = load_processed_data()

    # ---------------------------------------------------------
    # 1. Convert order purchase timestamp to datetime
    # ---------------------------------------------------------

    orders["order_purchase_timestamp"] = pd.to_datetime(
        orders["order_purchase_timestamp"],
        errors="coerce"
    )

    # ---------------------------------------------------------
    # 2. Keep completed purchases
    # ---------------------------------------------------------

    orders = orders[
        orders["order_status"] == "delivered"
    ].copy()

    # ---------------------------------------------------------
    # 3. Connect customer_id with customer_unique_id
    # ---------------------------------------------------------

    orders = orders.merge(
        customers[
            ["customer_id", "customer_unique_id"]
        ],
        on="customer_id",
        how="left"
    )

    # ---------------------------------------------------------
    # 4. Calculate purchase frequency
    # ---------------------------------------------------------

    frequency = (
        orders
        .groupby("customer_unique_id")["order_id"]
        .nunique()
        .reset_index(name="purchase_frequency")
    )

    # ---------------------------------------------------------
    # 5. Calculate purchase value
    # ---------------------------------------------------------

    payment_totals = (
        payments
        .groupby("order_id")["payment_value"]
        .sum()
        .reset_index()
    )

    orders_with_payment = orders.merge(
        payment_totals,
        on="order_id",
        how="left"
    )

    value = (
        orders_with_payment
        .groupby("customer_unique_id")["payment_value"]
        .sum()
        .reset_index(name="purchase_value")
    )

    # ---------------------------------------------------------
    # 6. Calculate last purchase date
    # ---------------------------------------------------------

    last_purchase = (
        orders
        .groupby("customer_unique_id")[
            "order_purchase_timestamp"
        ]
        .max()
        .reset_index(name="last_purchase_date")
    )

    # ---------------------------------------------------------
    # 7. Calculate customer activity / recency
    # ---------------------------------------------------------

    analysis_date = orders[
        "order_purchase_timestamp"
    ].max()

    last_purchase["customer_activity"] = (
        analysis_date -
        last_purchase["last_purchase_date"]
    ).dt.days

    # ---------------------------------------------------------
    # 8. Combine all three features
    # ---------------------------------------------------------

    features = frequency.merge(
        value,
        on="customer_unique_id",
        how="inner"
    )

    features = features.merge(
        last_purchase[
            [
                "customer_unique_id",
                "last_purchase_date",
                "customer_activity"
            ]
        ],
        on="customer_unique_id",
        how="inner"
    )

    # ---------------------------------------------------------
    # 9. Remove invalid values
    # ---------------------------------------------------------

    features = features.dropna(
        subset=[
            "purchase_frequency",
            "purchase_value",
            "customer_activity"
        ]
    )

    features = features[
        (features["purchase_frequency"] > 0) &
        (features["purchase_value"] > 0) &
        (features["customer_activity"] >= 0)
    ]

    return features


if __name__ == "__main__":

    features = prepare_segmentation_features()

    print("\n===== CUSTOMER SEGMENTATION FEATURES =====")

    print(f"Customers: {len(features)}")

    print(
        f"Columns: {list(features.columns)}"
    )

    print("\n===== SAMPLE =====")

    print(
        features.head(10).to_string(index=False)
    )

    print("\n===== FEATURE SUMMARY =====")

    print(
        features[
            [
                "purchase_frequency",
                "purchase_value",
                "customer_activity"
            ]
        ].describe()
    )

    print("\n===== FREQUENCY DISTRIBUTION =====")

    print(
        features["purchase_frequency"]
        .value_counts()
        .sort_index()
        .head(20)
    )