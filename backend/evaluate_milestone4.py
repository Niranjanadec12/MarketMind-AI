
import warnings

import numpy as np
import pandas as pd

from prophet import Prophet
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score, silhouette_score
from xgboost import XGBRegressor
from sklearn.ensemble import RandomForestRegressor

from app.ai.forecasting.ml_forecasting import (
    INPUT_FILE,
    TEST_RATIO,
    RANDOM_STATE,
    create_features,
)

from app.ai.segmentation.data_preparation import (
    prepare_segmentation_features,
)


def evaluate_forecasting():
    print("\n" + "=" * 60)
    print("FORECASTING MODEL EVALUATION")
    print("=" * 60)

    df = pd.read_csv(INPUT_FILE, parse_dates=["ds"])
    df = df.sort_values("ds").reset_index(drop=True)

    feature_columns = [
        "year", "month", "day", "day_of_week",
        "day_of_year", "week_of_year", "quarter",
        "revenue_lag_1", "revenue_lag_7",
        "revenue_lag_14", "revenue_lag_28",
        "rolling_mean_7", "rolling_mean_14",
        "rolling_mean_28",
    ]

    featured = create_features(df)

    model_data = featured.dropna(
        subset=feature_columns + ["y"]
    ).reset_index(drop=True)

    test_size = int(len(df) * TEST_RATIO)
    split_date = df.iloc[-test_size]["ds"]

    train_original = df[df["ds"] < split_date].copy()
    test_original = df[df["ds"] >= split_date].copy()

    train_ml = model_data[model_data["ds"] < split_date]
    test_ml = model_data[model_data["ds"] >= split_date]

    X_train = train_ml[feature_columns]
    y_train = train_ml["y"]
    X_test = test_ml[feature_columns]
    y_test = test_ml["y"]

    print(f"Training ends: {train_original['ds'].max().date()}")
    print(f"Testing starts: {test_original['ds'].min().date()}")
    print(f"Forecast test rows: {len(test_ml)}")

    results = []

    models = [
        (
            "XGBoost",
            XGBRegressor(
                n_estimators=300,
                learning_rate=0.05,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.8,
                objective="reg:squarederror",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
        ),
        (
            "Random Forest",
            RandomForestRegressor(
                n_estimators=300,
                max_depth=12,
                min_samples_leaf=2,
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
        ),
    ]

    for name, model in models:
        model.fit(X_train, y_train)
        predictions = np.maximum(model.predict(X_test), 0)

        results.append({
            "Model": name,
            "MAE": np.mean(np.abs(y_test.to_numpy() - predictions)),
            "RMSE": np.sqrt(np.mean((y_test.to_numpy() - predictions) ** 2)),
            "R2": r2_score(y_test, predictions),
        })

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        prophet_model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
        )
        prophet_model.fit(train_original[["ds", "y"]])

        prophet_predictions = prophet_model.predict(
            test_original[["ds"]]
        )["yhat"].to_numpy()

    actual = test_original["y"].to_numpy()

    results.append({
        "Model": "Prophet",
        "MAE": np.mean(np.abs(actual - prophet_predictions)),
        "RMSE": np.sqrt(np.mean((actual - prophet_predictions) ** 2)),
        "R2": r2_score(actual, prophet_predictions),
    })

    print("\nForecasting results:")
    print(pd.DataFrame(results).round(4).to_string(index=False))


def evaluate_segmentation():
    print("\n" + "=" * 60)
    print("CUSTOMER SEGMENTATION EVALUATION")
    print("=" * 60)

    features = prepare_segmentation_features()

    columns = [
        "purchase_frequency",
        "purchase_value",
        "customer_activity",
    ]

    X = features[columns].copy()

    if X.isna().any().any():
        raise ValueError(
            "Segmentation features contain missing values. "
            "Investigate before calculating Silhouette Scores."
        )

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Reproduce the existing K-Means configuration.
    kmeans = KMeans(
        n_clusters=3,
        random_state=42,
        n_init=10,
    )
    kmeans_labels = kmeans.fit_predict(X_scaled)

    kmeans_score = silhouette_score(
        X_scaled,
        kmeans_labels,
        sample_size=min(2000, len(X_scaled)),
        random_state=42,
    )

    print(f"K-Means Silhouette Score (sample up to 2,000): {kmeans_score:.4f}")

    # Reproduce the hierarchical model's 5,000-customer sample.
    sample_size = min(5000, len(X))
    sample = X.sample(n=sample_size, random_state=42)

    sample_scaler = StandardScaler()
    sample_scaled = sample_scaler.fit_transform(sample)

    hierarchical = AgglomerativeClustering(
        n_clusters=3,
        linkage="ward",
    )
    hierarchical_labels = hierarchical.fit_predict(sample_scaled)

    hierarchical_score = silhouette_score(
        sample_scaled,
        hierarchical_labels,
        sample_size=min(2000, sample_size),
        random_state=42,
    )

    print(
        "Hierarchical Silhouette Score "
        f"(model sample {sample_size}; score sample up to 2,000): "
        f"{hierarchical_score:.4f}"
    )


if __name__ == "__main__":
    evaluate_forecasting()
    evaluate_segmentation()
