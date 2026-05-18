import json
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from data_processing import DEFAULT_DATA_PATH, get_product_catalog, load_sales_data
from database import save_forecast_rows
from feature_engineering import FEATURE_COLUMNS, build_future_feature_row


ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "models" / "demand_model.joblib"
METRICS_PATH = ROOT_DIR / "models" / "metrics.json"


class ModelNotTrainedError(RuntimeError):
    pass


class ProductNotFoundError(ValueError):
    pass


class NotEnoughDataError(ValueError):
    pass


@lru_cache(maxsize=1)
def load_model_artifact() -> dict:
    if not MODEL_PATH.exists():
        raise ModelNotTrainedError("Модель ще не навчена. Виконайте перенавчання моделі.")
    return joblib.load(MODEL_PATH)


def get_metrics() -> dict:
    if not METRICS_PATH.exists():
        return {}
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def get_products() -> list[dict]:
    return get_product_catalog(DEFAULT_DATA_PATH).to_dict("records")


def clear_model_cache() -> None:
    load_model_artifact.cache_clear()
    _forecast_product_cached.cache_clear()


def _build_forecast(product_id: int, days: int, persist: bool) -> dict:
    artifact = load_model_artifact()
    model = artifact["model"]
    category_mapping = artifact["category_mapping"]
    data = load_sales_data(DEFAULT_DATA_PATH)
    product_data = data[data["product_id"] == product_id].sort_values("date")

    if product_data.empty:
        raise ProductNotFoundError("Товар не знайдено.")
    if len(product_data) < 14:
        raise NotEnoughDataError("Недостатньо історичних даних для прогнозування.")

    latest = product_data.iloc[-1]
    sales_history = product_data["sales_quantity"].astype(float).tolist()
    current_stock = float(latest["stock_quantity"])
    last_date = product_data["date"].max()
    forecast_rows = []

    for step in range(1, days + 1):
        forecast_date = last_date + pd.Timedelta(days=step)
        feature_row = build_future_feature_row(
            product_id=int(product_id),
            category=str(latest["category"]),
            price=float(latest["price"]),
            stock_quantity=current_stock,
            promo=0,
            holiday=0,
            supplier_delay_days=float(latest["supplier_delay_days"]),
            forecast_date=forecast_date,
            sales_history=sales_history,
            category_mapping=category_mapping,
        )
        predicted = max(0.0, float(model.predict(feature_row[FEATURE_COLUMNS])[0]))
        sales_history.append(predicted)
        current_stock = max(0.0, current_stock - predicted)
        forecast_rows.append(
            {
                "date": forecast_date.date().isoformat(),
                "predicted_quantity": round(predicted, 2),
            }
        )

    if persist:
        save_forecast_rows(product_id, forecast_rows)

    return {
        "product_id": int(product_id),
        "product_name": str(latest["product_name"]),
        "category": str(latest["category"]),
        "forecast_days": int(days),
        "forecast": forecast_rows,
    }


@lru_cache(maxsize=128)
def _forecast_product_cached(product_id: int, days: int) -> dict:
    return _build_forecast(product_id, days, persist=False)


def forecast_product(product_id: int, days: int = 14, persist: bool = False) -> dict:
    if persist:
        return _build_forecast(product_id, days, persist=True)
    return _forecast_product_cached(product_id, days)


def total_forecast_for_product(product_id: int, days: int = 14) -> float:
    forecast = forecast_product(product_id, days=days, persist=False)
    return float(sum(row["predicted_quantity"] for row in forecast["forecast"]))
