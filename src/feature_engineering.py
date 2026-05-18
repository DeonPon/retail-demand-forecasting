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
    result["day_of_week"] = result["date"].dt.dayofweek
    result["month"] = result["date"].dt.month
    result["day_of_month"] = result["date"].dt.day
    result["quarter"] = result["date"].dt.quarter
    result["is_weekend"] = (result["day_of_week"] >= 5).astype(int)
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


def prepare_training_data(
    data: pd.DataFrame,
    category_mapping: dict[str, int] | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    mapping = category_mapping or build_category_mapping(data)
    prepared = add_lag_features(add_category_feature(add_calendar_features(data), mapping))
    prepared = prepared.replace([np.inf, -np.inf], np.nan)
    prepared["rolling_std_7"] = prepared["rolling_std_7"].fillna(0)
    prepared = prepared.dropna(subset=FEATURE_COLUMNS + ["sales_quantity"]).reset_index(drop=True)
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
    history_mean_7 = float(pd.Series(sales_history[-7:]).mean())
    history_mean_14 = float(pd.Series(sales_history[-14:]).mean())
    last_price = float(price_history[-1])
    prev_price = float(price_history[-2] if len(price_history) >= 2 else price_history[-1])
    current_price_change = ((last_price - prev_price) / prev_price) if prev_price else 0.0

    future_row = pd.DataFrame(
        [
            {
                "date": forecast_date,
                "product_id": int(row["product_id"]),
                "product_name": row["product_name"],
                "category": row["category"],
                "base_demand": float(row["base_demand"]),
                "price": last_price,
                "stock_quantity": float(row["stock_quantity"]),
                "supplier_delay_days": float(row["supplier_delay_days"]),
                "promo": 0,
                "holiday": 0,
                "sales_quantity": 0,
            }
        ]
    )
    future_row = add_category_feature(add_calendar_features(future_row), category_mapping)
    future_row["lag_1"] = sales_history[-1]
    future_row["lag_7"] = sales_history[-7]
    future_row["lag_14"] = sales_history[-14]
    future_row["rolling_mean_7"] = history_mean_7
    future_row["rolling_mean_14"] = history_mean_14
    future_row["rolling_std_7"] = float(pd.Series(sales_history[-7:]).std() or 0)
    future_row["price_change"] = current_price_change
    future_row["promo_last_7_days"] = int(sum(promo_history[-7:]))
    future_row["stock_ratio"] = float(row["stock_quantity"]) / max(float(row["base_demand"]), 1.0)
    future_row["trend_7"] = history_mean_7 - history_mean_14
    return future_row
