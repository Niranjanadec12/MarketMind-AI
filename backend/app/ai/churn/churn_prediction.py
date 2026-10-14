
from pathlib import Path
import warnings
import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    classification_report,
)

warnings.filterwarnings("ignore", category=FutureWarning)

# Run this script from the MarketMind-AI project root.
ROOT = Path(__file__).resolve().parents[4]
DATA = ROOT / "data"
ANALYTICAL = DATA / "analytical"
PROCESSED = DATA / "processed"

SALES_FILE = ANALYTICAL / "sales_analytics.csv"
CUSTOMERS_FILE = PROCESSED / "customers_clean.csv"

FEATURES_OUT = ANALYTICAL / "customer_churn_features.csv"
METRICS_OUT = ANALYTICAL / "churn_model_metrics.csv"
PREDICTIONS_OUT = ANALYTICAL / "customer_churn_predictions.csv"
MODEL_OUT = Path(__file__).resolve().parent / "churn_model.joblib"


def main():
    print("=" * 60)
    print("MARKETMIND AI - CHURN PREDICTION")
    print("=" * 60)

    # 1. Load data and map order-level IDs to unique customers.
    sales = pd.read_csv(SALES_FILE)
    customers = pd.read_csv(
        CUSTOMERS_FILE,
        usecols=["customer_id", "customer_unique_id"],
    )

    customers = customers.dropna(
        subset=["customer_id", "customer_unique_id"]
    ).drop_duplicates("customer_id")

    sales = sales.merge(
        customers,
        on="customer_id",
        how="left",
        validate="many_to_one",
    )

    sales["order_purchase_timestamp"] = pd.to_datetime(
        sales["order_purchase_timestamp"], errors="coerce"
    )

    sales = sales.dropna(
        subset=[
            "customer_unique_id",
            "order_id",
            "order_purchase_timestamp",
        ]
    )

    sales["purchase_day"] = (
        sales["order_purchase_timestamp"].dt.normalize()
    )

    # Only completed purchases count as customer purchases.
    delivered = sales[
        sales["order_status"].eq("delivered")
    ].copy()

    if delivered.empty:
        raise ValueError("No delivered orders found in sales data.")

    delivered["total_item_value"] = pd.to_numeric(
        delivered["total_item_value"], errors="coerce"
    ).fillna(0)

    latest_date = delivered["purchase_day"].max()

    # Reserve the final 90 days for the future churn label.
    cutoff = latest_date - pd.Timedelta(days=90)
    feature_start = cutoff - pd.Timedelta(days=180)
    label_end = cutoff + pd.Timedelta(days=90)

    print(f"Latest delivered purchase: {latest_date.date()}")
    print(f"Feature window starts:     {feature_start.date()}")
    print(f"Prediction cutoff:         {cutoff.date()}")
    print(f"Label window ends:         {label_end.date()}")

    # 2. Build features using only purchases before the cutoff.
    history = delivered[
        (delivered["purchase_day"] >= feature_start)
        & (delivered["purchase_day"] < cutoff)
    ].copy()

    if history.empty:
        raise ValueError("No delivered orders in the feature window.")

    # One row per order avoids counting an order's items as separate orders.
    order_keys = ["customer_unique_id", "order_id"]

    order_agg = {
        "purchase_day": ("purchase_day", "min"),
        "order_value": ("total_item_value", "sum"),
        "item_count": ("order_item_id", "count"),
    }

    orders = history.groupby(order_keys).agg(**order_agg).reset_index()

    grouped = history.groupby("customer_unique_id")

    features = grouped.agg(
        order_count=("order_id", "nunique"),
        total_spend=("total_item_value", "sum"),
        average_item_value=("total_item_value", "mean"),
        maximum_item_value=("total_item_value", "max"),
        unique_products=("product_id", "nunique"),
        unique_categories=("product_category_name", "nunique"),
        purchase_days=("purchase_day", "nunique"),
        first_purchase=("purchase_day", "min"),
        last_purchase=("purchase_day", "max"),
        total_items=("order_item_id", "count"),
    ).reset_index()

    order_stats = orders.groupby("customer_unique_id").agg(
        average_order_value=("order_value", "mean"),
        maximum_order_value=("order_value", "max"),
        average_items_per_order=("item_count", "mean"),
    ).reset_index()

    features = features.merge(
        order_stats, on="customer_unique_id", how="left"
    )

    features["days_since_last_order"] = (
        cutoff - features["last_purchase"]
    ).dt.days

    features["customer_tenure_days"] = (
        features["last_purchase"] - features["first_purchase"]
    ).dt.days

    # Average gap between distinct orders, in days.
    orders = orders.sort_values(
        ["customer_unique_id", "purchase_day", "order_id"]
    )
    orders["gap_days"] = (
        orders.groupby("customer_unique_id")["purchase_day"]
        .diff()
        .dt.days
    )

    gaps = orders.groupby("customer_unique_id")["gap_days"].mean()
    features["average_days_between_orders"] = (
        features["customer_unique_id"].map(gaps)
    )

    features["active_months"] = (
        history.assign(
            month=history["purchase_day"].dt.to_period("M").astype(str)
        )
        .groupby("customer_unique_id")["month"]
        .nunique()
        .reindex(features["customer_unique_id"])
        .to_numpy()
    )

    features["snapshot_cutoff"] = cutoff.strftime("%Y-%m-%d")
    features["label_window_end"] = label_end.strftime("%Y-%m-%d")

    # 3. Create the target from purchases strictly after the cutoff.
    future = delivered[
        (delivered["purchase_day"] >= cutoff)
        & (delivered["purchase_day"] <= label_end)
    ]

    future_customers = set(future["customer_unique_id"].unique())

    features["churn"] = (
        ~features["customer_unique_id"].isin(future_customers)
    ).astype(int)

    print(f"\nCustomers in feature dataset: {len(features):,}")
    print(f"Churned (no future purchase): {features['churn'].sum():,}")
    print(f"Retained (future purchase):    {(features['churn'] == 0).sum():,}")

    if features["churn"].nunique() < 2:
        raise ValueError(
            "The data contains only one target class; "
            "classification cannot be trained."
        )

    # Save the complete feature dataset, including the target.
    FEATURES_OUT.parent.mkdir(parents=True, exist_ok=True)
    features.to_csv(FEATURES_OUT, index=False)

    # 4. Train an initial Logistic Regression baseline.
    feature_columns = [
        "order_count",
        "total_spend",
        "average_item_value",
        "maximum_item_value",
        "unique_products",
        "unique_categories",
        "purchase_days",
        "total_items",
        "average_order_value",
        "maximum_order_value",
        "average_items_per_order",
        "days_since_last_order",
        "customer_tenure_days",
        "average_days_between_orders",
        "active_months",
    ]

    X = features[feature_columns].replace([np.inf, -np.inf], np.nan)
    y = features["churn"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=42,
        stratify=y,
    )

    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("classifier", LogisticRegression(
            max_iter=2000,
            class_weight="balanced",
            random_state=42,
        )),
    ])

    model.fit(X_train, y_train)

    test_predictions = model.predict(X_test)
    test_probabilities = model.predict_proba(X_test)[:, 1]

    metrics = {
        "model": "LogisticRegression",
        "snapshot_cutoff": cutoff.strftime("%Y-%m-%d"),
        "feature_window_days": 180,
        "label_window_days": 90,
        "customers": len(features),
        "train_customers": len(X_train),
        "test_customers": len(X_test),
        "churn_rate": float(y.mean()),
        "accuracy": accuracy_score(y_test, test_predictions),
        "precision": precision_score(
            y_test, test_predictions, zero_division=0
        ),
        "recall": recall_score(
            y_test, test_predictions, zero_division=0
        ),
        "f1_score": f1_score(
            y_test, test_predictions, zero_division=0
        ),
        "roc_auc": roc_auc_score(y_test, test_probabilities),
        "average_precision": average_precision_score(
            y_test, test_probabilities
        ),
    }

    pd.DataFrame([metrics]).to_csv(METRICS_OUT, index=False)

    print("\nHeld-out test metrics:")
    print(pd.Series(metrics).to_string())
    print("\nClassification report:")
    print(classification_report(
        y_test, test_predictions, zero_division=0
    ))

    # 5. Fit the final baseline on all labeled snapshot customers.
    model.fit(X, y)
    probabilities = model.predict_proba(X)[:, 1]

    predictions = features[[
        "customer_unique_id",
        "churn",
        "snapshot_cutoff",
    ]].copy()

    predictions["churn_probability"] = probabilities
    predictions["risk_category"] = pd.cut(
        probabilities,
        bins=[-0.001, 0.35, 0.65, 1.001],
        labels=["Low", "Medium", "High"],
        include_lowest=True,
    ).astype(str)

    # 6. Attach existing Milestone 2 customer segments.
    kmeans_file = ANALYTICAL / "customer_segments_kmeans.csv"
    if kmeans_file.exists():
        kmeans = pd.read_csv(kmeans_file)
        kmeans = kmeans[
            ["customer_unique_id", "cluster"]
        ].drop_duplicates("customer_unique_id")
        predictions = predictions.merge(
            kmeans,
            on="customer_unique_id",
            how="left",
            validate="one_to_one",
        )
        predictions = predictions.rename(
            columns={"cluster": "kmeans_cluster"}
        )

    hierarchical_file = (
        ANALYTICAL / "customer_segments_hierarchical.csv"
    )
    if hierarchical_file.exists():
        cols = [
            "customer_unique_id",
            "hierarchical_cluster",
            "segment_name",
            "segment_description",
        ]
        hierarchical = pd.read_csv(hierarchical_file)
        hierarchical = hierarchical[
            [c for c in cols if c in hierarchical.columns]
        ].drop_duplicates("customer_unique_id")
        predictions = predictions.merge(
            hierarchical,
            on="customer_unique_id",
            how="left",
            validate="one_to_one",
        )

    predictions = predictions.sort_values(
        "churn_probability", ascending=False
    )
    predictions.to_csv(PREDICTIONS_OUT, index=False)

    joblib.dump(
        {
            "model": model,
            "feature_columns": feature_columns,
            "snapshot_cutoff": cutoff.strftime("%Y-%m-%d"),
            "feature_window_days": 180,
            "label_window_days": 90,
            "positive_class": "no delivered purchase in label window",
        },
        MODEL_OUT,
    )

    print("\nSaved outputs:")
    for path in [
        FEATURES_OUT,
        METRICS_OUT,
        PREDICTIONS_OUT,
        MODEL_OUT,
    ]:
        print(f"  {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")

    print("\nRisk distribution:")
    print(predictions["risk_category"].value_counts(dropna=False).to_string())

    print("\nTop 10 highest-risk customers:")
    print(predictions[[
        "customer_unique_id",
        "churn_probability",
        "risk_category",
    ]].head(10).to_string(index=False))

    print("\nDay 5-6 churn baseline completed.")


if __name__ == "__main__":
    main()
