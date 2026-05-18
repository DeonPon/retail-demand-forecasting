from __future__ import annotations

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
        raise ModelNotTrainedError("Модель ще не навчена. Спочатку виконайте перенавчання.")
    return joblib.load(MODEL_PATH)


def clear_model_cache() -> None:
    load_model_artifact.cache_clear()
    _forecast_product_cached.cache_clear()


def get_metrics() -> dict:
    if not METRICS_PATH.exists():
        return {}
    return json.loads(METRICS_PATH.read_text(encoding="utf-8"))


def get_products() -> list[dict]:
    return get_product_catalog(DEFAULT_DATA_PATH).to_dict("records")


def _extract_influence_factors(product_row: pd.Series, history: pd.DataFrame, forecast_total: float) -> list[str]:
    factors: list[str] = []
    last_7 = float(history.tail(7)["sales_quantity"].mean())
    last_14 = float(history.tail(14)["sales_quantity"].mean())

    if int(product_row["promo"]) == 1:
        factors.append("Акція активна: попит на товар підсилюється.")
    else:
        factors.append("Акція зараз не активна, тому прогноз спирається на звичайний попит.")

    if history.tail(14)["date"].dt.dayofweek.isin([5, 6]).mean() > 0.25:
        factors.append("Вихідні дні впливають на попит у цій категорії.")

    if last_7 > last_14 * 1.05:
        factors.append("За останній тиждень продажі зростали.")
    elif last_7 < last_14 * 0.95:
        factors.append("Останній тиждень показує помірний спад попиту.")
    else:
        factors.append("Попит за останні 14 днів залишається відносно стабільним.")

    if float(product_row["stock_quantity"]) < last_7 * 3:
        factors.append("Поточний залишок низький відносно недавнього попиту.")
    else:
        factors.append("Поточний залишок не обмежує продажі в короткому горизонті.")

    if float(product_row["supplier_delay_days"]) > 1:
        factors.append("Затримка постачальника підвищує важливість страхового запасу.")

    if float(product_row["price"]) > float(product_row["base_demand"]) * 4:
        factors.append("Поточна ціна може стримувати частину попиту.")

    return factors[:6]


def _build_plain_explanation(latest: pd.Series, product_data: pd.DataFrame, total: float, days: int) -> str:
    last_14 = product_data.tail(14)["sales_quantity"].astype(float)
    mean_14 = float(last_14.mean())
    std_14 = float(last_14.std() or 0.0)
    current_stock = float(latest["stock_quantity"])

    if std_14 <= max(mean_14 * 0.2, 1.0):
        dynamics = "стабільний попит за останні 14 днів"
    elif last_14.iloc[-7:].mean() > last_14.iloc[:7].mean():
        dynamics = "зростання попиту за останні два тижні"
    else:
        dynamics = "помірні коливання попиту без різких стрибків"

    stock_phrase = (
        "Поточний залишок виглядає достатнім для покриття прогнозованого попиту."
        if current_stock >= total
        else "Поточний залишок нижчий за прогнозований попит на вибраний період."
    )

    return (
        f"Для товару «{latest['product_name']}» система врахувала {dynamics}, "
        f"вплив дня тижня, поточну ціну, залишок на складі та сезонність категорії. "
        f"Прогноз сформовано на період після останньої доступної дати продажів. "
        f"Очікуваний попит на {days} днів становить {round(total)} одиниць. {stock_phrase}"
    )


def _build_forecast(product_id: int, days: int, persist: bool) -> dict:
    artifact = load_model_artifact()
    model = artifact["model"]
    category_mapping = artifact["category_mapping"]
    data = load_sales_data(DEFAULT_DATA_PATH)
    product_data = data[data["product_id"] == product_id].sort_values("date").tail(60).copy()

    if product_data.empty:
        raise ProductNotFoundError("Товар не знайдено.")
    if len(product_data) < 30:
        raise NotEnoughDataError("Недостатньо історичних даних для прогнозування.")

    latest = product_data.iloc[-1]
    sales_history = product_data["sales_quantity"].astype(float).tolist()
    price_history = product_data["price"].astype(float).tolist()
    promo_history = product_data["promo"].astype(int).tolist()
    current_stock = float(latest["stock_quantity"])
    last_date = pd.Timestamp(product_data["date"].max())
    forecast_rows: list[dict] = []

    for step in range(1, days + 1):
        forecast_date = last_date + pd.Timedelta(days=step)
        future_row = build_future_feature_row(
            row=latest,
            forecast_date=forecast_date,
            sales_history=sales_history,
            price_history=price_history,
            promo_history=promo_history,
            category_mapping=category_mapping,
        )
        predicted = max(0.0, float(model.predict(future_row[FEATURE_COLUMNS])[0]))
        sales_history.append(predicted)
        if len(sales_history) > 60:
            sales_history.pop(0)
        price_history.append(float(latest["price"]))
        if len(price_history) > 60:
            price_history.pop(0)
        promo_history.append(0)
        if len(promo_history) > 60:
            promo_history.pop(0)
        current_stock = max(0.0, current_stock - predicted)
        forecast_rows.append({"date": forecast_date.date().isoformat(), "predicted_quantity": round(predicted, 2)})

    if persist:
        save_forecast_rows(product_id, forecast_rows)

    total = float(sum(item["predicted_quantity"] for item in forecast_rows))
    values = [item["predicted_quantity"] for item in forecast_rows]

    return {
        "product_id": int(product_id),
        "product_name": str(latest["product_name"]),
        "category": str(latest["category"]),
        "forecast_days": int(days),
        "history_last_date": last_date.date().isoformat(),
        "forecast_start_date": forecast_rows[0]["date"],
        "forecast_end_date": forecast_rows[-1]["date"],
        "forecast": forecast_rows,
        "forecast_total": round(total, 2),
        "forecast_min": round(min(values), 2),
        "forecast_max": round(max(values), 2),
        "forecast_avg": round(total / max(len(values), 1), 2),
        "trend": "зростає" if values[-1] > values[0] * 1.06 else "падає" if values[-1] < values[0] * 0.94 else "стабільний",
        "factors": _extract_influence_factors(latest, product_data, total),
        "plain_explanation": _build_plain_explanation(latest, product_data, total, days),
        "feature_importance": artifact.get("metrics", {}).get("feature_importance", []),
    }


@lru_cache(maxsize=256)
def _forecast_product_cached(product_id: int, days: int) -> dict:
    return _build_forecast(product_id, days, persist=False)


def forecast_product(product_id: int, days: int = 14, persist: bool = False) -> dict:
    return _build_forecast(product_id, days, persist=True) if persist else _forecast_product_cached(product_id, days)
