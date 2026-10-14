import pandas as pd
from pathlib import Path
from prophet import Prophet


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
ANALYTICAL_DIR = PROJECT_ROOT / "data" / "analytical"

ORDERS_FILE = PROCESSED_DIR / "orders_cleaned.csv"
PAYMENTS_FILE = PROCESSED_DIR / "order_payments_clean.csv"

FORECAST_INPUT_FILE = (
    ANALYTICAL_DIR / "daily_revenue_prophet.csv"
)

FORECAST_OUTPUT_FILE = (
    ANALYTICAL_DIR / "prophet_revenue_forecast.csv"
)


# ============================================================
# PREPARE HISTORICAL REVENUE
# ============================================================

def prepare_revenue_data():
    """
    Prepare daily revenue data for Prophet.

    Prophet requires:
        ds = date
        y  = value to forecast
    """

    orders = pd.read_csv(ORDERS_FILE)
    payments = pd.read_csv(PAYMENTS_FILE)

    # Convert data types
    orders["order_purchase_timestamp"] = pd.to_datetime(
        orders["order_purchase_timestamp"],
        errors="coerce"
    )

    payments["payment_value"] = pd.to_numeric(
        payments["payment_value"],
        errors="coerce"
    )

    # Keep required order columns
    orders = orders[
        [
            "order_id",
            "order_status",
            "order_purchase_timestamp"
        ]
    ]

    # Merge orders with payments
    merged = orders.merge(
        payments[
            [
                "order_id",
                "payment_value"
            ]
        ],
        on="order_id",
        how="inner"
    )

    # Use delivered orders for historical revenue
    merged = merged[
        merged["order_status"] == "delivered"
    ].copy()

    # Convert timestamp to daily date
    merged["ds"] = (
        merged["order_purchase_timestamp"]
        .dt.floor("D")
    )

    # Aggregate revenue by day
    daily_revenue = (
        merged.groupby("ds")["payment_value"]
        .sum()
        .reset_index()
        .rename(
            columns={
                "payment_value": "y"
            }
        )
    )

    # Create continuous calendar
    full_dates = pd.DataFrame(
        {
            "ds": pd.date_range(
                start=daily_revenue["ds"].min(),
                end=daily_revenue["ds"].max(),
                freq="D"
            )
        }
    )

    # Add missing dates with zero revenue
    daily_revenue = full_dates.merge(
        daily_revenue,
        on="ds",
        how="left"
    )

    daily_revenue["y"] = (
        daily_revenue["y"]
        .fillna(0)
    )

    # Ensure correct ordering
    daily_revenue = (
        daily_revenue
        .sort_values("ds")
        .reset_index(drop=True)
    )

    return daily_revenue


# ============================================================
# TRAIN PROPHET MODEL
# ============================================================

def train_prophet_model(history):
    """
    Train a basic Prophet forecasting model.
    """

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False
    )

    model.fit(history)

    return model


# ============================================================
# GENERATE FORECAST
# ============================================================

def generate_forecast(
    model,
    periods=90
):
    """
    Generate a 90-day future revenue forecast.
    """

    future = model.make_future_dataframe(
        periods=periods,
        freq="D"
    )

    forecast = model.predict(future)

    return forecast


# ============================================================
# SAVE DATA
# ============================================================

def save_data(
    history,
    forecast
):
    """
    Save Prophet input data and forecast results.
    """

    ANALYTICAL_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    # Save historical Prophet input
    history.to_csv(
        FORECAST_INPUT_FILE,
        index=False
    )

    # Save forecast
    forecast[
        [
            "ds",
            "yhat",
            "yhat_lower",
            "yhat_upper"
        ]
    ].to_csv(
        FORECAST_OUTPUT_FILE,
        index=False
    )

    return (
        FORECAST_INPUT_FILE,
        FORECAST_OUTPUT_FILE
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "\n===== PROPHET REVENUE FORECASTING ====="
    )

    # Prepare historical data
    history = prepare_revenue_data()

    print(
        f"\nHistorical observations: "
        f"{len(history)}"
    )

    print(
        f"Historical date range: "
        f"{history['ds'].min().date()} "
        f"to "
        f"{history['ds'].max().date()}"
    )

    print(
        f"Total historical revenue: "
        f"₹{history['y'].sum():,.2f}"
    )

    print(
        f"Zero-revenue dates: "
        f"{(history['y'] == 0).sum()}"
    )

    # Train model
    print(
        "\nTraining Prophet model..."
    )

    model = train_prophet_model(
        history
    )

    print(
        "Prophet model trained successfully."
    )

    # Generate 90-day forecast
    print(
        "\nGenerating 90-day forecast..."
    )

    forecast = generate_forecast(
        model,
        periods=90
    )

    # Save results
    input_file, output_file = save_data(
        history,
        forecast
    )

    # Separate future forecast
    future_forecast = forecast[
        forecast["ds"] > history["ds"].max()
    ].copy()

    print(
        "\n===== FORECAST SUMMARY ====="
    )

    print(
        f"Future forecast days: "
        f"{len(future_forecast)}"
    )

    print(
        f"Forecast start: "
        f"{future_forecast['ds'].min().date()}"
    )

    print(
        f"Forecast end: "
        f"{future_forecast['ds'].max().date()}"
    )

    print(
        "\n===== FIRST 10 FORECAST VALUES ====="
    )

    print(
        future_forecast[
            [
                "ds",
                "yhat",
                "yhat_lower",
                "yhat_upper"
            ]
        ]
        .head(10)
        .round(2)
        .to_string(index=False)
    )

    print(
        "\n===== OUTPUT FILES ====="
    )

    print(
        f"Prophet input:\n{input_file}"
    )

    print(
        f"\nForecast output:\n{output_file}"
    )