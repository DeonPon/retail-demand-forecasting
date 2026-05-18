from __future__ import annotations

import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "product_id",
    "category_encoded",
    "base_demand",
    "price",
    "stock_quantity",
    "supplier_delay_days",
    "promo",
    "holiday",
    "day_of_week",
    "month",
    "day_of_month",
    "is_weekend",
    "quarter",
    "lag_1",
    "lag_7",
    "lag_14",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_std_7",
    "price_change",
    "promo_last_7_days",
    "stock_ratio",
    "trend_7",
]


def build_category_mapping(data: pd.DataFrame) -> dict[str, int]:
    categories = sorted(data["category"].dropna().unique().tolist())
    return {category: index for index, category in enumerate(categories)}


def add_calendar_features(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    date_series = pd.to_datetime(result["date"], errors="coerce")
    day_of_week = date_series.dt.dayofweek.fillna(0).astype(int)
    result["date"] = date_series
    result["day_of_week"] = day_of_week
    result["month"] = date_series.dt.month.fillna(1).astype(int)
    result["day_of_month"] = date_series.dt.day.fillna(1).astype(int)
    result["quarter"] = date_series.dt.quarter.fillna(1).astype(int)
    result["is_weekend"] = day_of_week.isin([5, 6]).astype(int)
    return result


def add_category_feature(data: pd.DataFrame, mapping: dict[str, int] | None = None) -> pd.DataFrame:
    result = data.copy()
    mapping = mapping or build_category_mapping(result)
    result["category_encoded"] = result["category"].map(mapping).fillna(-1).astype(int)
    return result


def add_lag_features(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    grouped_sales = result.groupby("product_id", group_keys=False)["sales_quantity"]
    grouped_price = result.groupby("product_id", group_keys=False)["price"]
    grouped_promo = result.groupby("product_id", group_keys=False)["promo"]

    result["lag_1"] = grouped_sales.shift(1)
    result["lag_7"] = grouped_sales.shift(7)
    result["lag_14"] = grouped_sales.shift(14)
    result["rolling_mean_7"] = grouped_sales.shift(1).rolling(7).mean().reset_index(level=0, drop=True)
    result["rolling_mean_14"] = grouped_sales.shift(1).rolling(14).mean().reset_index(level=0, drop=True)
    result["rolling_std_7"] = grouped_sales.shift(1).rolling(7).std().reset_index(level=0, drop=True)
    result["price_change"] = grouped_price.pct_change().replace([np.inf, -np.inf], 0).fillna(0)
    result["promo_last_7_days"] = grouped_promo.shift(1).rolling(7).sum().reset_index(level=0, drop=True).fillna(0)
    result["stock_ratio"] = result["stock_quantity"] / result["base_demand"].replace(0, 1)
    result["trend_7"] = result["rolling_mean_7"] - result["rolling_mean_14"]
    return result


def ensure_feature_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in FEATURE_COLUMNS:
        if column not in result.columns:
            result[column] = 0
    return result[FEATURE_COLUMNS]


def prepare_training_data(
    data: pd.DataFrame,
    category_mapping: dict[str, int] | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    mapping = category_mapping or build_category_mapping(data)
    prepared = add_lag_features(add_category_feature(add_calendar_features(data), mapping))
    prepared = prepared.replace([np.inf, -np.inf], np.nan)
    prepared["rolling_std_7"] = prepared["rolling_std_7"].fillna(0)
    prepared = prepared.dropna(subset=FEATURE_COLUMNS + ["sales_quantity"]).reset_index(drop=True)
    prepared = prepared.assign(is_weekend=prepared["is_weekend"].fillna(0).astype(int))
    return prepared, mapping


def build_future_feature_row(
    *,
    row: pd.Series,
    forecast_date: pd.Timestamp,
    sales_history: list[float],
    price_history: list[float],
    promo_history: list[int],
    category_mapping: dict[str, int],
) -> pd.DataFrame:
    date_value = pd.Timestamp(forecast_date)
    day_of_week = int(date_value.dayofweek)
    last_price = float(price_history[-1])
    prev_price = float(price_history[-2] if len(price_history) >= 2 else price_history[-1])
    base_demand = max(float(row["base_demand"]), 1.0)
    rolling_mean_7 = float(np.mean(sales_history[-7:]))
    rolling_mean_14 = float(np.mean(sales_history[-14:]))
    rolling_std_7 = float(np.std(sales_history[-7:], ddof=1)) if len(sales_history[-7:]) > 1 else 0.0

    feature_values = {
        "product_id": int(row["product_id"]),
        "category_encoded": int(category_mapping.get(str(row["category"]), -1)),
        "base_demand": float(row["base_demand"]),
        "price": last_price,
        "stock_quantity": float(row["stock_quantity"]),
        "supplier_delay_days": float(row["supplier_delay_days"]),
        "promo": 0,
        "holiday": 0,
        "day_of_week": day_of_week,
        "month": int(date_value.month),
        "day_of_month": int(date_value.day),
        "is_weekend": 1 if day_of_week >= 5 else 0,
        "quarter": int(date_value.quarter),
        "lag_1": float(sales_history[-1]),
        "lag_7": float(sales_history[-7] if len(sales_history) >= 7 else sales_history[-1]),
        "lag_14": float(sales_history[-14] if len(sales_history) >= 14 else sales_history[-1]),
        "rolling_mean_7": rolling_mean_7,
        "rolling_mean_14": rolling_mean_14,
        "rolling_std_7": rolling_std_7,
        "price_change": ((last_price - prev_price) / prev_price) if prev_price else 0.0,
        "promo_last_7_days": int(sum(promo_history[-7:])),
        "stock_ratio": float(row["stock_quantity"]) / base_demand,
        "trend_7": rolling_mean_7 - rolling_mean_14,
    }
    return ensure_feature_columns(pd.DataFrame([feature_values]))
