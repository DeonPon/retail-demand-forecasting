from data_processing import DEFAULT_DATA_PATH, load_sales_data
from predict import forecast_product


def purchase_recommendation(product_id: int, days: int = 14, safety_factor: float = 0.15) -> dict:
    forecast = forecast_product(product_id, days=days)
    data = load_sales_data(DEFAULT_DATA_PATH)
    latest = data[data["product_id"] == product_id].sort_values("date").iloc[-1]

    forecast_total = float(sum(row["predicted_quantity"] for row in forecast["forecast"]))
    current_stock = float(latest["stock_quantity"])
    safety_stock = forecast_total * safety_factor
    recommended_order_quantity = max(0, round(forecast_total + safety_stock - current_stock))

    explanation = (
        f"Система прогнозує продаж {round(forecast_total)} одиниць за {days} днів. "
        f"Поточний залишок — {round(current_stock)} одиниць. "
        f"З урахуванням страхового запасу рекомендовано закупити "
        f"{recommended_order_quantity} одиниць."
    )

    return {
        "product_id": int(product_id),
        "product_name": str(latest["product_name"]),
        "forecast_days": int(days),
        "forecast_total": round(forecast_total, 2),
        "safety_stock": round(safety_stock, 2),
        "current_stock": round(current_stock, 2),
        "recommended_order_quantity": int(recommended_order_quantity),
        "explanation": explanation,
    }
