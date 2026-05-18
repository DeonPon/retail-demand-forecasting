from pathlib import Path

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "sales_sample.csv"

PRODUCTS = [
    {"product_id": 1, "product_name": "Кава мелена 250 г", "category": "Бакалія", "base_price": 145, "base_demand": 42},
    {"product_id": 2, "product_name": "Молоко 2.5% 1 л", "category": "Молочні продукти", "base_price": 44, "base_demand": 84},
    {"product_id": 3, "product_name": "Шоколад чорний 90 г", "category": "Кондитерські вироби", "base_price": 68, "base_demand": 51},
    {"product_id": 4, "product_name": "Пральний порошок 3 кг", "category": "Побутова хімія", "base_price": 285, "base_demand": 22},
    {"product_id": 5, "product_name": "Яблука українські 1 кг", "category": "Фрукти", "base_price": 38, "base_demand": 63},
    {"product_id": 6, "product_name": "Корм для котів 1.5 кг", "category": "Зоотовари", "base_price": 230, "base_demand": 27},
]

HOLIDAY_DATES = {
    "2024-01-01",
    "2024-03-08",
    "2024-05-01",
    "2024-08-24",
    "2024-12-25",
    "2024-12-31",
    "2025-01-01",
    "2025-03-08",
    "2025-04-20",
}


def generate_sales_dataset(start_date: str = "2024-01-01", end_date: str = "2025-04-30") -> pd.DataFrame:
    """Генерує демонстраційні продажі з сезонністю, акціями, святами та затримками постачальників."""
    rng = np.random.default_rng(121)
    dates = pd.date_range(start_date, end_date, freq="D")
    rows = []

    for product in PRODUCTS:
        stock_quantity = int(product["base_demand"] * rng.uniform(8, 12))

        for date in dates:
            is_weekend = int(date.dayofweek >= 5)
            holiday = int(date.date().isoformat() in HOLIDAY_DATES)
            promo = int(rng.random() < (0.14 if not holiday else 0.25))
            supplier_delay_days = int(max(0, rng.poisson(0.35) - (1 if rng.random() < 0.75 else 0)))

            weekly_factor = 1.16 if is_weekend else 1.0
            holiday_factor = 1.28 if holiday else 1.0
            winter_factor = 1.13 if date.month in [11, 12, 1] else 1.0
            summer_factor = 0.92 if date.month in [6, 7, 8] else 1.0
            promo_factor = 1.32 if promo else 1.0
            delay_factor = max(0.7, 1 - supplier_delay_days * 0.06)
            noise = rng.normal(0, product["base_demand"] * 0.13)

            expected_demand = (
                product["base_demand"]
                * weekly_factor
                * holiday_factor
                * winter_factor
                * summer_factor
                * promo_factor
                * delay_factor
                + noise
            )
            sales_quantity = max(0, int(round(expected_demand)))

            if date.dayofweek == 0:
                stock_quantity += int(product["base_demand"] * rng.uniform(5.5, 8.5))
                stock_quantity = max(0, stock_quantity - supplier_delay_days * int(product["base_demand"] * 0.35))

            sales_quantity = min(sales_quantity, stock_quantity)
            stock_quantity -= sales_quantity
            price = product["base_price"] * (0.9 if promo else 1.0)

            rows.append(
                {
                    "date": date.date().isoformat(),
                    "product_id": product["product_id"],
                    "product_name": product["product_name"],
                    "category": product["category"],
                    "sales_quantity": sales_quantity,
                    "price": round(price, 2),
                    "stock_quantity": int(stock_quantity),
                    "promo": promo,
                    "holiday": holiday,
                    "supplier_delay_days": supplier_delay_days,
                }
            )

    return pd.DataFrame(rows)


def main() -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    dataset = generate_sales_dataset()
    dataset.to_csv(DATA_PATH, index=False, encoding="utf-8")
    print(f"Створено демонстраційний датасет: {DATA_PATH}")
    print(f"Кількість рядків: {len(dataset)}")


if __name__ == "__main__":
    main()
