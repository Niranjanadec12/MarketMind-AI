FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY data/analytical/sales_analytics.csv ./data/analytical/sales_analytics.csv
COPY data/analytical/customer_analytics.csv ./data/analytical/customer_analytics.csv
COPY data/analytical/product_analytics.csv ./data/analytical/product_analytics.csv
COPY data/analytical/customer_segments_hierarchical.csv ./data/analytical/customer_segments_hierarchical.csv
COPY data/analytical/future_revenue_forecasts.csv ./data/analytical/future_revenue_forecasts.csv
COPY data/analytical/forecast_model_comparison.csv ./data/analytical/forecast_model_comparison.csv

COPY data/analytical/inventory_analytics.csv ./data/analytical/inventory_analytics.csv
COPY data/analytical/anomaly_alerts.csv ./data/analytical/anomaly_alerts.csv
COPY data/analytical/customer_sales_suggestions.csv ./data/analytical/customer_sales_suggestions.csv
WORKDIR /app/backend

EXPOSE 8000

CMD ["sh", "-c", "python -c 'from app.main import app' && python -m app.auth.seed_data && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

