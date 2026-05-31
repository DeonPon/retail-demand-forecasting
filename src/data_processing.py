from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = ROOT_DIR / "data" / "sales_sample.csv"

REQUIRED_COLUMNS = [
    "date",
    "product_id",
    "product_name",
    "category",
    "sales_quantity",
    "price",
    "stock_quantity",
    "promo",
    "holiday",
    "supplier_delay_days",
]

OPTIONAL_COLUMNS = [
    "product_icon",
    "base_demand",
    "seasonality_type",
    "shelf_life_days",
    "supplier_name",
    "region",
]


def normalize_legacy_columns(data: pd.DataFrame) -> pd.DataFrame:
    return data.rename(columns={"sales": "sales_quantity", "stock": "stock_quantity"})


def validate_sales_dataframe(data: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        columns = ", ".join(missing)
        raise ValueError(
            "CSV має неправильну структуру. Обов'язкові колонки: "
            + ", ".join(REQUIRED_COLUMNS)
            + f". Відсутні: {columns}."
        )


def _apply_default_optional_columns(data: pd.DataFrame) -> pd.DataFrame:
    defaults = {
        "product_icon": "📦",
        "base_demand": 0,
        "seasonality_type": "stable",
        "shelf_life_days": 365,
        "supplier_name": "Невідомий постачальник",
        "region": "Україна",
    }
    result = data.copy()
    for column, default_value in defaults.items():
        if column not in result.columns:
            result[column] = default_value
    return result


@lru_cache(maxsize=8)
def load_sales_data(path: Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError("Файл з даними продажів не знайдено.")

    data = pd.read_csv(path)
    data = _apply_default_optional_columns(normalize_legacy_columns(data))
    validate_sales_dataframe(data)

    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    numeric_columns = [
        "product_id",
        "sales_quantity",
        "price",
        "stock_quantity",
        "promo",
        "holiday",
        "supplier_delay_days",
        "base_demand",
        "shelf_life_days",
    ]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(subset=["date", *numeric_columns, "product_name", "category"])
    data["product_id"] = data["product_id"].astype(int)
    data["sales_quantity"] = data["sales_quantity"].clip(lower=0)
    data["stock_quantity"] = data["stock_quantity"].clip(lower=0)
    data["promo"] = data["promo"].astype(int).clip(0, 1)
    data["holiday"] = data["holiday"].astype(int).clip(0, 1)
    data["supplier_delay_days"] = data["supplier_delay_days"].clip(lower=0)
    data["base_demand"] = data["base_demand"].clip(lower=0)
    data["shelf_life_days"] = data["shelf_life_days"].fillna(365).clip(lower=1)
    data["product_icon"] = data["product_icon"].fillna("📦")
    data["seasonality_type"] = data["seasonality_type"].fillna("stable")
    data["supplier_name"] = data["supplier_name"].fillna("Невідомий постачальник")
    data["region"] = data["region"].fillna("Україна")
    return data.sort_values(["product_id", "date"]).reset_index(drop=True)


def clear_data_cache() -> None:
    load_sales_data.cache_clear()


def save_uploaded_dataset(data: pd.DataFrame, path: Path = DEFAULT_DATA_PATH) -> None:
    prepared = _apply_default_optional_columns(normalize_legacy_columns(data))
    validate_sales_dataframe(prepared)
    path.parent.mkdir(parents=True, exist_ok=True)
    prepared.to_csv(path, index=False, encoding="utf-8-sig")
    clear_data_cache()


def get_product_catalog(path: Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    data = load_sales_data(path)
    latest_rows = data.sort_values("date").groupby("product_id").tail(1)
    columns = [
        "product_id",
        "product_name",
        "category",
        "product_icon",
        "price",
        "stock_quantity",
        "promo",
        "base_demand",
        "seasonality_type",
        "shelf_life_days",
        "supplier_name",
        "region",
    ]
    return latest_rows[columns].sort_values("product_id").reset_index(drop=True)


def summarize_dataset(path: Path = DEFAULT_DATA_PATH) -> dict:
    data = load_sales_data(path)
    return {
        "products_count": int(data["product_id"].nunique()),
        "categories_count": int(data["category"].nunique()),
        "sales_rows_count": int(len(data)),
        "date_from": data["date"].min().date().isoformat(),
        "date_to": data["date"].max().date().isoformat(),
    }
