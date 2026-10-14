
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[4]

FEATURES_PATH = ROOT / "data/analytical/customer_churn_features.csv"
BASE_PREDICTIONS_PATH = ROOT / "data/analytical/customer_churn_predictions.csv"
OUTPUT_PATH = ROOT / "data/analytical/customer_churn_predictions.csv"
MODEL_PATH = ROOT / "backend/app/ai/churn/churn_model.joblib"


def main():
    df = pd.read_csv(FEATURES_PATH)
    base_predictions = pd.read_csv(BASE_PREDICTIONS_PATH)

    excluded = {
        "churn",
        "customer_unique_id",
        "customer_id",
        "snapshot_cutoff",
    }

    feature_columns = [
        c for c in df.select_dtypes(include=np.number).columns
        if c not in excluded
    ]

    X = df[feature_columns].replace([np.inf, -np.inf], np.nan)
    y = df["churn"].astype(int)

    # Refit the selected model on the complete historical dataset.
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(
            class_weight="balanced",
            max_iter=2000,
            random_state=42,
        )),
    ])

    model.fit(X, y)

    classes = list(model.named_steps["model"].classes_)
    probabilities = model.predict_proba(X)

    churn_probability = probabilities[:, classes.index(1)]

    predictions = pd.DataFrame({
        "customer_unique_id": df["customer_unique_id"],
        "churn": y,
        "snapshot_cutoff": (
            df["snapshot_cutoff"]
            if "snapshot_cutoff" in df.columns
            else "2018-05-31"
        ),
        "churn_probability": churn_probability,
    })

    predictions["risk_category"] = pd.cut(
        predictions["churn_probability"],
        bins=[-np.inf, 0.35, 0.65, np.inf],
        labels=["Low", "Medium", "High"],
        right=False,
    ).astype(str)

    # Retain the segment assignments from Milestone 2.
    segment_columns = [
        "customer_unique_id",
        "kmeans_cluster",
        "hierarchical_cluster",
        "segment_name",
        "segment_description",
    ]

    available_columns = [
        c for c in segment_columns
        if c in base_predictions.columns
    ]

    if "customer_unique_id" in available_columns:
        segments = base_predictions[available_columns].drop_duplicates(
            subset=["customer_unique_id"]
        )
        predictions = predictions.merge(
            segments,
            on="customer_unique_id",
            how="left",
            validate="one_to_one",
        )

    predictions["model_name"] = "LogisticRegression"

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(OUTPUT_PATH, index=False)

    # Save the final model separately from the original baseline.
    joblib.dump({
        "pipeline": model,
        "model": model,
        "model_name": "LogisticRegression",
        "feature_columns": feature_columns,
        "target": "churn",
        "snapshot_cutoff": "2018-05-31",
        "feature_window_days": 180,
        "label_window_days": 90,
        "risk_thresholds": {
            "low": "churn_probability < 0.35",
            "medium": "0.35 <= churn_probability < 0.65",
            "high": "churn_probability >= 0.65",
        },
    }, MODEL_PATH)

    print("=" * 60)
    print("FINAL CHURN MODEL")
    print("=" * 60)
    print(f"Selected model: Logistic Regression")
    print(f"Customers scored: {len(predictions):,}")
    print(f"Features used: {len(feature_columns)}")
    print("\nRisk distribution:")
    print(predictions["risk_category"].value_counts().to_string())
    print("\nMean predicted churn probability:")
    print(round(predictions["churn_probability"].mean(), 4))
    print(f"\nPredictions saved: {OUTPUT_PATH}")
    print(f"Model saved: {MODEL_PATH}")
    print("\nSample predictions:")
    print(predictions.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
