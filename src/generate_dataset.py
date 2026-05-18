from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from catalog import CATEGORY_PROFILES, build_product_catalog


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "sales_sample.csv"

HOLIDAY_DATES = {
    "2024-06-28",
    "2024-08-24",
    "2024-10-14",
    "2024-12-06",
    "2024-12-19",
    "2024-12-25",
    "2024-12-31",
    "2025-01-01",
    "2025-03-08",
    "2025-04-20",
}


def seasonal_component(date: pd.Timestamp, seasonality_type: str) -> float:
    month = date.month
    if seasonality_type == "daily":
        return 1.0
    if seasonality_type == "summer":
        return 1.22 if month in [6, 7, 8] else 0.94 if month in [1, 2] else 1.0
    if seasonality_type == "winter":
        return 1.18 if month in [11, 12, 1, 2] else 0.96 if month in [6, 7, 8] else 1.0
    if seasonality_type == "holiday":
        return 1.14 if month in [11, 12] else 1.0
    if seasonality_type == "harvest":
        return 1.18 if month in [7, 8, 9, 10] else 0.95 if month in [2, 3] else 1.0
    if seasonality_type == "weekend":
        return 1.05
    return 1.0


def generate_sales_dataset(start_date: str = "2024-05-01", end_date: str = "2025-04-30") -> pd.DataFrame:
    """Генерує реалістичний демонстраційний датасет продажів для дипломного прототипу."""
    rng = np.random.default_rng(2026)
    dates = pd.date_range(start_date, end_date, freq="D")
    rows: list[dict] = []

    for product in build_product_catalog():
        profile = CATEGORY_PROFILES[product["category"]]
        stock_quantity = int(product["base_demand"] * rng.uniform(10, 18))
        recent_sales: list[float] = [product["base_demand"] * rng.uniform(0.85, 1.15) for _ in range(14)]
        price_level = float(product["base_price"])

        for date in dates:
            if date.day == 1:
                price_level *= rng.uniform(0.995, 1.015)
            holiday = int(date.date().isoformat() in HOLIDAY_DATES)
            is_weekend = int(date.dayofweek >= 5)
            promo_probability = 0.06 if product["category"] in {"Побутова хімія", "Товари для дому"} else 0.1
            promo = int(rng.random() < promo_probability or (holiday and rng.random() < 0.22))
            supplier_delay_days = int(max(0, rng.poisson(0.4) + (1 if rng.random() < 0.08 else 0)))

            seasonal = seasonal_component(date, product["seasonality_type"])
            weekday_factor = profile.weekend_boost if is_weekend else 1.0
            holiday_factor = profile.holiday_boost if holiday else 1.0
            promo_factor = profile.promo_boost if promo else 1.0
            trend_factor = 1.0 + (np.mean(recent_sales[-7:]) - np.mean(recent_sales[-14:-7])) / max(product["base_demand"] * 12, 1)
            trend_factor = float(np.clip(trend_factor, 0.92, 1.15))

            effective_price = price_level * (rng.uniform(0.86, 0.93) if promo else rng.uniform(0.99, 1.01))
            price_factor = 1.0 - ((effective_price - product["base_price"]) / max(product["base_price"], 1)) * profile.price_sensitivity
            price_factor = float(np.clip(price_factor, 0.82, 1.22))

            stock_ratio = stock_quantity / max(product["base_demand"] * 16, 1)
            stock_factor = 1.0 if stock_ratio >= 0.15 else max(0.42, 1.0 - profile.stockout_penalty)
            delay_factor = max(0.72, 1.0 - supplier_delay_days * profile.delay_penalty)
            noise = rng.normal(0, max(product["base_demand"] * 0.08, 1.5))

            demand = (
                product["base_demand"]
                * seasonal
                * weekday_factor
                * holiday_factor
                * promo_factor
                * trend_factor
                * price_factor
                * stock_factor
                * delay_factor
                + noise
            )
            sales_quantity = max(0, int(round(demand)))

            if date.dayofweek == profile.reorder_days % 7:
                replenishment = int(product["base_demand"] * rng.uniform(profile.reorder_days * 0.9, profile.reorder_days * 1.4))
                stock_quantity += max(0, replenishment - supplier_delay_days * max(int(product["base_demand"] * 0.25), 1))

            sales_quantity = min(sales_quantity, stock_quantity)
            stock_quantity = max(0, stock_quantity - sales_quantity)
            recent_sales.append(sales_quantity)

            rows.append(
                {
                    "date": date.date().isoformat(),
                    "product_id": product["product_id"],
                    "product_name": product["product_name"],
                    "category": product["category"],
                    "sales_quantity": sales_quantity,
                    "price": round(effective_price, 2),
                    "stock_quantity": int(stock_quantity),
                    "promo": promo,
                    "holiday": holiday,
                    "supplier_delay_days": supplier_delay_days,
                    "product_icon": product["product_icon"],
                    "base_demand": product["base_demand"],
                    "seasonality_type": product["seasonality_type"],
                    "shelf_life_days": product["shelf_life_days"],
                    "supplier_name": product["supplier_name"],
                    "region": product["region"],
                }
            )

    return pd.DataFrame(rows)


def main() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataset = generate_sales_dataset()
    dataset.to_csv(DATA_PATH, index=False, encoding="utf-8")
    print(f"Створено демонстраційний датасет: {DATA_PATH}")
    print(f"Товарів: {dataset['product_id'].nunique()}")
    print(f"Кількість рядків: {len(dataset)}")


if __name__ == "__main__":
    main()
