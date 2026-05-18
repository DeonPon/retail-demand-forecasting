from __future__ import annotations

from functools import lru_cache

from data_processing import DEFAULT_DATA_PATH, load_sales_data
from database import save_recommendation_history
from predict import forecast_product


def _priority_for_recommendation(quantity: float, stock_cover_days: float) -> str:
    if quantity > 0 and stock_cover_days < 5:
        return "високий"
    if quantity > 0 and stock_cover_days < 10:
        return "середній"
    return "низький"


def _status_label(priority: str) -> str:
    return {"високий": "терміново закупити", "середній": "бажано закупити"}.get(priority, "запас нормальний")


def purchase_recommendation(product_id: int, days: int = 14, persist_forecast: bool = False) -> dict:
    forecast = forecast_product(product_id, days=days, persist=persist_forecast)
    data = load_sales_data(DEFAULT_DATA_PATH)
    product_data = data[data["product_id"] == product_id].sort_values("date")
    latest = product_data.iloc[-1]

    forecast_total = float(forecast["forecast_total"])
    current_stock = float(latest["stock_quantity"])
    mean_demand = max(float(product_data.tail(14)["sales_quantity"].mean()), 1.0)
    std_demand = float(product_data.tail(14)["sales_quantity"].std() or 0.0)
    supplier_delay_days = float(latest["supplier_delay_days"])
    category_factor = (
        1.2
        if latest["category"] in {"Молочні продукти", "Фрукти та овочі"}
        else 1.05
        if latest["category"] in {"Напої", "Снеки"}
        else 1.0
    )
    safety_stock = (mean_demand * (2 + supplier_delay_days) + std_demand * 0.8) * category_factor
    recommended_order_quantity = max(0, round(forecast_total + safety_stock - current_stock))
    stock_cover_days = current_stock / mean_demand
    priority = _priority_for_recommendation(recommended_order_quantity, stock_cover_days)
    explanation = (
        f"Прогнозований попит: {round(forecast_total)} од. за {days} днів. "
        f"Поточний залишок: {round(current_stock)} од. "
        f"Страховий запас: {round(safety_stock)} од. "
        f"Затримка постачальника: {supplier_delay_days:.0f} дн. "
        f"Рекомендована закупівля: {recommended_order_quantity} од."
    )

    return {
        "product_id": int(product_id),
        "product_name": str(latest["product_name"]),
        "product_icon": str(latest["product_icon"]),
        "category": str(latest["category"]),
        "forecast_days": int(days),
        "forecast_total": round(forecast_total, 2),
        "current_stock": round(current_stock, 2),
        "safety_stock": round(safety_stock, 2),
        "supplier_delay_days": round(supplier_delay_days, 2),
        "recommended_order_quantity": int(recommended_order_quantity),
        "priority": priority,
        "status_label": _status_label(priority),
        "explanation": explanation,
        "stock_cover_days": round(stock_cover_days, 1),
        "forecast_factors": forecast["factors"],
    }


@lru_cache(maxsize=32)
def list_recommendations(days: int = 14) -> list[dict]:
    data = load_sales_data(DEFAULT_DATA_PATH)
    recommendations = [
        purchase_recommendation(int(product_id), days=days, persist_forecast=False)
        for product_id in sorted(data["product_id"].unique().tolist())
    ]
    return sorted(recommendations, key=lambda item: (item["priority"] != "високий", -item["recommended_order_quantity"]))


def clear_recommendations_cache() -> None:
    list_recommendations.cache_clear()


def exportable_recommendations(days: int = 14) -> list[dict]:
    rows = list_recommendations(days=days)
    save_recommendation_history(rows)
    return rows
