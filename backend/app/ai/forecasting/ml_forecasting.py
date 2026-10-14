import os
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

from prophet import Prophet


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = r"D:\project\MarketMind-AI"

INPUT_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "analytical",
    "daily_revenue_prophet.csv"
)

PROPHET_FORECAST_FILE = os.path.join(
    PROJECT_ROOT,
    "data",
    "analytical",
    "prophet_revenue_forecast.csv"
)

OUTPUT_DIR = os.path.join(
    PROJECT_ROOT,
    "data",
    "analytical"
)

COMPARISON_FILE = os.path.join(
    OUTPUT_DIR,
    "forecast_model_comparison.csv"
)

FUTURE_FORECAST_FILE = os.path.join(
    OUTPUT_DIR,
    "future_revenue_forecasts.csv"
)


# ============================================================
# SETTINGS
# ============================================================

TEST_RATIO = 0.20
FORECAST_DAYS = 90
RANDOM_STATE = 42


# ============================================================
# FEATURE CREATION
# ============================================================

def create_features(df):
    """
    Create calendar, lag, and rolling features
    from daily revenue data.
    """

    data = df.copy()

    # Calendar features
    data["year"] = data["ds"].dt.year
    data["month"] = data["ds"].dt.month
    data["day"] = data["ds"].dt.day
    data["day_of_week"] = data["ds"].dt.dayofweek
    data["day_of_year"] = data["ds"].dt.dayofyear
    data["week_of_year"] = data["ds"].dt.isocalendar().week.astype(int)
    data["quarter"] = data["ds"].dt.quarter

    # Lag features
    data["revenue_lag_1"] = data["y"].shift(1)
    data["revenue_lag_7"] = data["y"].shift(7)
    data["revenue_lag_14"] = data["y"].shift(14)
    data["revenue_lag_28"] = data["y"].shift(28)

    # Rolling features
    # shift(1) prevents the current day's revenue
    # from being included in its own prediction.
    data["rolling_mean_7"] = (
        data["y"].shift(1).rolling(window=7).mean()
    )

    data["rolling_mean_14"] = (
        data["y"].shift(1).rolling(window=14).mean()
    )

    data["rolling_mean_28"] = (
        data["y"].shift(1).rolling(window=28).mean()
    )

    return data


# ============================================================
# METRICS
# ============================================================

def calculate_mape(actual, predicted):
    """
    Calculate MAPE only for observations where
    actual revenue is greater than zero.
    """

    actual = np.asarray(actual)
    predicted = np.asarray(predicted)

    non_zero = actual != 0

    if non_zero.sum() == 0:
        return np.nan

    return (
        np.mean(
            np.abs(
                (actual[non_zero] - predicted[non_zero])
                / actual[non_zero]
            )
        )
        * 100
    )


def calculate_metrics(actual, predicted):
    """
    Calculate MAE, RMSE, and MAPE.
    """

    mae = mean_absolute_error(actual, predicted)

    rmse = np.sqrt(
        mean_squared_error(actual, predicted)
    )

    mape = calculate_mape(actual, predicted)

    return mae, rmse, mape


# ============================================================
# PROPHET EVALUATION
# ============================================================

def evaluate_prophet(train_df, test_df):
    """
    Train Prophet only on the training period
    and evaluate it on the same test period
    used by XGBoost and Random Forest.
    """

    print("\n===== PROPHET EVALUATION =====")

    prophet_train = train_df[["ds", "y"]].copy()

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model.fit(prophet_train)

    future_dates = test_df[["ds"]].copy()

    forecast = model.predict(future_dates)

    actual = test_df["y"].values
    predicted = forecast["yhat"].values

    mae, rmse, mape = calculate_metrics(
        actual,
        predicted
    )

    print(f"Prophet MAE : {mae:.2f}")
    print(f"Prophet RMSE: {rmse:.2f}")
    print(f"Prophet MAPE: {mape:.2f}%")

    return {
        "model": "Prophet",
        "MAE": mae,
        "RMSE": rmse,
        "MAPE": mape
    }


# ============================================================
# FUTURE FEATURE CREATION
# ============================================================

def create_future_ml_forecast(
    model,
    historical_data,
    feature_columns,
    forecast_days,
    model_name
):
    """
    Generate recursive future predictions for
    XGBoost or Random Forest.
    """

    history = historical_data[["ds", "y"]].copy()

    future_predictions = []

    for _ in range(forecast_days):

        next_date = history["ds"].iloc[-1] + pd.Timedelta(days=1)

        temp = pd.concat(
            [
                history,
                pd.DataFrame(
                    {
                        "ds": [next_date],
                        "y": [np.nan]
                    }
                )
            ],
            ignore_index=True
        )

        # Calendar features
        temp["year"] = temp["ds"].dt.year
        temp["month"] = temp["ds"].dt.month
        temp["day"] = temp["ds"].dt.day
        temp["day_of_week"] = temp["ds"].dt.dayofweek
        temp["day_of_year"] = temp["ds"].dt.dayofyear
        temp["week_of_year"] = (
            temp["ds"].dt.isocalendar().week.astype(int)
        )
        temp["quarter"] = temp["ds"].dt.quarter

        # Lag features
        temp["revenue_lag_1"] = temp["y"].shift(1)
        temp["revenue_lag_7"] = temp["y"].shift(7)
        temp["revenue_lag_14"] = temp["y"].shift(14)
        temp["revenue_lag_28"] = temp["y"].shift(28)

        # Rolling features
        temp["rolling_mean_7"] = (
            temp["y"].shift(1).rolling(7).mean()
        )

        temp["rolling_mean_14"] = (
            temp["y"].shift(1).rolling(14).mean()
        )

        temp["rolling_mean_28"] = (
            temp["y"].shift(1).rolling(28).mean()
        )

        row = temp.iloc[-1:]

        X_future = row[feature_columns]

        prediction = model.predict(X_future)[0]

        # Revenue cannot be negative
        prediction = max(0, float(prediction))

        future_predictions.append(
            {
                "ds": next_date,
                model_name: prediction
            }
        )

        # Add prediction to history so that it can
        # become a future lag value.
        history = pd.concat(
            [
                history,
                pd.DataFrame(
                    {
                        "ds": [next_date],
                        "y": [prediction]
                    }
                )
            ],
            ignore_index=True
        )

    return pd.DataFrame(future_predictions)


# ============================================================
# MAIN
# ============================================================

def main():

    print("================================================")
    print("DAY 7-8: FORECASTING MODELS")
    print("================================================")

    # --------------------------------------------------------
    # Load data
    # --------------------------------------------------------

    print("\n===== LOADING DATA =====")

    df = pd.read_csv(
        INPUT_FILE,
        parse_dates=["ds"]
    )

    df = df.sort_values("ds").reset_index(drop=True)

    print(f"Rows: {len(df)}")
    print(f"Date range: {df['ds'].min().date()} -> {df['ds'].max().date()}")

    # --------------------------------------------------------
    # Create features
    # --------------------------------------------------------

    print("\n===== CREATING FEATURES =====")

    featured_df = create_features(df)

    feature_columns = [
        "year",
        "month",
        "day",
        "day_of_week",
        "day_of_year",
        "week_of_year",
        "quarter",
        "revenue_lag_1",
        "revenue_lag_7",
        "revenue_lag_14",
        "revenue_lag_28",
        "rolling_mean_7",
        "rolling_mean_14",
        "rolling_mean_28"
    ]

    # Remove rows where lag/rolling values don't exist.
    model_data = featured_df.dropna(
        subset=feature_columns + ["y"]
    ).reset_index(drop=True)

    print(f"Rows after feature creation: {len(model_data)}")
    print(f"Features used: {len(feature_columns)}")

    # --------------------------------------------------------
    # Chronological split
    # --------------------------------------------------------

    print("\n===== TRAIN / TEST SPLIT =====")

    test_size = int(len(df) * TEST_RATIO)

    split_date = df.iloc[-test_size]["ds"]

    train_original = df[
        df["ds"] < split_date
    ].copy()

    test_original = df[
        df["ds"] >= split_date
    ].copy()

    train_ml = model_data[
        model_data["ds"] < split_date
    ].copy()

    test_ml = model_data[
        model_data["ds"] >= split_date
    ].copy()

    print(f"Training period: {train_original['ds'].min().date()} -> {train_original['ds'].max().date()}")
    print(f"Testing period : {test_original['ds'].min().date()} -> {test_original['ds'].max().date()}")

    print(f"Training ML rows: {len(train_ml)}")
    print(f"Testing ML rows : {len(test_ml)}")

    X_train = train_ml[feature_columns]
    y_train = train_ml["y"]

    X_test = test_ml[feature_columns]
    y_test = test_ml["y"]

    # --------------------------------------------------------
    # XGBoost
    # --------------------------------------------------------

    print("\n===== XGBOOST =====")

    xgb_model = XGBRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    xgb_model.fit(
        X_train,
        y_train
    )

    xgb_predictions = xgb_model.predict(X_test)

    xgb_predictions = np.maximum(
        xgb_predictions,
        0
    )

    xgb_mae, xgb_rmse, xgb_mape = calculate_metrics(
        y_test,
        xgb_predictions
    )

    print(f"XGBoost MAE : {xgb_mae:.2f}")
    print(f"XGBoost RMSE: {xgb_rmse:.2f}")
    print(f"XGBoost MAPE: {xgb_mape:.2f}%")

    # --------------------------------------------------------
    # Random Forest
    # --------------------------------------------------------

    print("\n===== RANDOM FOREST =====")

    rf_model = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    rf_model.fit(
        X_train,
        y_train
    )

    rf_predictions = rf_model.predict(X_test)

    rf_predictions = np.maximum(
        rf_predictions,
        0
    )

    rf_mae, rf_rmse, rf_mape = calculate_metrics(
        y_test,
        rf_predictions
    )

    print(f"Random Forest MAE : {rf_mae:.2f}")
    print(f"Random Forest RMSE: {rf_rmse:.2f}")
    print(f"Random Forest MAPE: {rf_mape:.2f}%")

    # --------------------------------------------------------
    # Prophet
    # --------------------------------------------------------

    prophet_result = evaluate_prophet(
        train_original,
        test_original
    )

    # --------------------------------------------------------
    # Model comparison
    # --------------------------------------------------------

    comparison = pd.DataFrame(
        [
            {
                "model": "Prophet",
                "MAE": prophet_result["MAE"],
                "RMSE": prophet_result["RMSE"],
                "MAPE": prophet_result["MAPE"]
            },
            {
                "model": "XGBoost",
                "MAE": xgb_mae,
                "RMSE": xgb_rmse,
                "MAPE": xgb_mape
            },
            {
                "model": "Random Forest",
                "MAE": rf_mae,
                "RMSE": rf_rmse,
                "MAPE": rf_mape
            }
        ]
    )

    comparison.to_csv(
        COMPARISON_FILE,
        index=False
    )

    print("\n===== MODEL COMPARISON =====")
    print(comparison.to_string(index=False))

    print(
        f"\nComparison saved to:\n{COMPARISON_FILE}"
    )

    # --------------------------------------------------------
    # Train ML models on full available data
    # --------------------------------------------------------

    print("\n===== TRAINING FINAL ML MODELS =====")

    full_X = model_data[feature_columns]
    full_y = model_data["y"]

    final_xgb = XGBRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        objective="reg:squarederror",
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    final_xgb.fit(
        full_X,
        full_y
    )

    final_rf = RandomForestRegressor(
        n_estimators=300,
        max_depth=12,
        min_samples_leaf=2,
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    final_rf.fit(
        full_X,
        full_y
    )

    # --------------------------------------------------------
    # Generate future forecasts
    # --------------------------------------------------------

    print("\n===== GENERATING 90-DAY FUTURE FORECASTS =====")

    xgb_future = create_future_ml_forecast(
        final_xgb,
        df,
        feature_columns,
        FORECAST_DAYS,
        "xgboost_forecast"
    )

    rf_future = create_future_ml_forecast(
        final_rf,
        df,
        feature_columns,
        FORECAST_DAYS,
        "random_forest_forecast"
    )

    future = xgb_future.merge(
        rf_future,
        on="ds"
    )

    # --------------------------------------------------------
    # Add existing Prophet future forecast
    # --------------------------------------------------------

    if os.path.exists(PROPHET_FORECAST_FILE):

        prophet_future = pd.read_csv(
            PROPHET_FORECAST_FILE,
            parse_dates=["ds"]
        )

        prophet_future = prophet_future[
            prophet_future["ds"] > df["ds"].max()
        ][
            ["ds", "yhat"]
        ].copy()

        prophet_future = prophet_future.rename(
            columns={
                "yhat": "prophet_forecast"
            }
        )

        future = future.merge(
            prophet_future,
            on="ds",
            how="left"
        )

    future.to_csv(
        FUTURE_FORECAST_FILE,
        index=False
    )

    print(
        f"Future forecasts saved to:\n{FUTURE_FORECAST_FILE}"
    )

    # --------------------------------------------------------
    # Final output preview
    # --------------------------------------------------------

    print("\n===== FUTURE FORECAST PREVIEW =====")
    print(future.head(10).to_string(index=False))

    print("\n===== FORECASTING COMPLETE =====")


if __name__ == "__main__":
    main()