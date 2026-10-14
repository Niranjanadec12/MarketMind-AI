from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[4]

DATA_PATH = ROOT / "data/analytical/customer_churn_features.csv"
METRICS_PATH = ROOT / "data/analytical/churn_model_comparison.csv"
MODEL_PATH = ROOT / "backend/app/ai/churn/churn_model_comparison.joblib"

RANDOM_STATE = 42


def main():
    print("=" * 60)
    print("MARKETMIND AI - CHURN MODEL COMPARISON")
    print("=" * 60)

    df = pd.read_csv(DATA_PATH)

    if "churn" not in df.columns:
        raise ValueError("The input dataset does not contain a 'churn' column.")

    df = df.dropna(subset=["churn"]).copy()
    df["churn"] = df["churn"].astype(int)

    if set(df["churn"].unique()) != {0, 1}:
        raise ValueError("Expected both churn labels: 0 and 1.")

    # Keep numeric behavioral features only.
    # Exclude labels and identifiers to prevent accidental leakage.
    excluded = {
        "churn",
        "customer_unique_id",
        "customer_id",
        "snapshot_cutoff",
    }

    feature_columns = [
        col
        for col in df.select_dtypes(include=np.number).columns
        if col not in excluded
    ]

    if not feature_columns:
        raise ValueError("No numeric feature columns were found.")

    X = df[feature_columns].replace([np.inf, -np.inf], np.nan)
    y = df["churn"]

    print(f"\nCustomers: {len(df):,}")
    print(f"Numeric features: {len(feature_columns)}")
    print(f"Retained customers (0): {(y == 0).sum():,}")
    print(f"Churned customers (1): {(y == 1).sum():,}")
    print("\nFeatures used:")
    print(feature_columns)

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.20,
        random_state=RANDOM_STATE,
        stratify=y,
    )

    models = {
        "LogisticRegression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced",
                    max_iter=2000,
                    random_state=RANDOM_STATE,
                ),
            ),
        ]),
        "RandomForest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=250,
                    min_samples_leaf=3,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]),
        "ExtraTrees": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            (
                "model",
                ExtraTreesClassifier(
                    n_estimators=250,
                    min_samples_leaf=3,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]),
    }

    results = []
    fitted_models = {}

    # Class 0 means retained. We specifically evaluate how well
    # each model identifies these relatively rare customers.
    y_test_retained = (y_test == 0).astype(int)

    for name, model in models.items():
        print(f"\nTraining {name}...")

        model.fit(X_train, y_train)

        probabilities = model.predict_proba(X_test)
        classes = list(model.named_steps["model"].classes_)
        retained_index = classes.index(0)

        p_retained = probabilities[:, retained_index]
        predicted_churn = model.predict(X_test)
        predicted_retained = (predicted_churn == 0).astype(int)

        row = {
            "model": name,
            "accuracy": accuracy_score(y_test, predicted_churn),
            "retained_precision": precision_score(
                y_test_retained,
                predicted_retained,
                zero_division=0,
            ),
            "retained_recall": recall_score(
                y_test_retained,
                predicted_retained,
                zero_division=0,
            ),
            "retained_f1": f1_score(
                y_test_retained,
                predicted_retained,
                zero_division=0,
            ),
            "retained_roc_auc": roc_auc_score(
                y_test_retained,
                p_retained,
            ),
            "retained_average_precision": average_precision_score(
                y_test_retained,
                p_retained,
            ),
        }

        results.append(row)
        fitted_models[name] = model

        print(pd.Series(row).to_string(index=False))

        print("\nClassification report (0 = retained, 1 = churned):")
        print(
            classification_report(
                y_test,
                predicted_churn,
                labels=[0, 1],
                zero_division=0,
            )
        )

    results_df = pd.DataFrame(results).sort_values(
        "retained_average_precision",
        ascending=False,
    )

    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(METRICS_PATH, index=False)

    best_name = results_df.iloc[0]["model"]
    best_model = fitted_models[best_name]

    # Save the comparison winner separately from the original baseline.
    joblib.dump(
        {
            "model": best_model,
            "model_name": best_name,
            "feature_columns": feature_columns,
            "target": "churn",
            "positive_business_class": "retained (churn=0)",
            "selection_metric": "retained_average_precision",
            "random_state": RANDOM_STATE,
        },
        MODEL_PATH,
    )

    print("\n" + "=" * 60)
    print("MODEL COMPARISON SUMMARY")
    print("=" * 60)
    print(results_df.to_string(index=False))
    print(f"\nBest model by retained average precision: {best_name}")
    print(f"Metrics saved to: {METRICS_PATH}")
    print(f"Comparison model saved to: {MODEL_PATH}")


if __name__ == "__main__":
    main()