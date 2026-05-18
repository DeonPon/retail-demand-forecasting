import numpy as np
import pandas as pd


FEATURE_COLUMNS = [
    "product_id",
    "category_encoded",
    "price",
    "stock_quantity",
    "promo",
    "holiday",
    "supplier_delay_days",
    "day_of_week",
    "month",
    "day_of_month",
    "is_weekend",
    "lag_1",
    "lag_7",
    "rolling_mean_7",
    "rolling_mean_14",
]


def build_category_mapping(data: pd.DataFrame) -> dict[str, int]:
    categories = sorted(data["category"].dropna().unique().tolist())
    return {category: index for index, category in enumerate(categories)}


def add_calendar_features(data: pd.DataFrame) -> pd.DataFrame:
    result = data.copy()
    result["day_of_week"] = result["date"].dt.dayofweek
    result["month"] = result["date"].dt.month
    result["day_of_month"] = result["date"].dt.day
    result["is_weekend"] = (result["day_of_week"] >= 5).astype(int)
    return result


def add_category_feature(data: pd.DataFrame, mapping: dict[str, int] | None = None) -> pd.DataFrame:
    result = data.copy()
    if mapping is None:
        mapping = build_category_mapping(result)
    result["category_encoded"] = result["category"].map(mapping).fillna(-1).astype(int)
    return result


def add_lag_features(data: pd.DataFrame) -> pd.DataFrame:
    """Створює лаги та рухомі середні окремо для кожного товару."""
    result = data.copy()
    grouped_sales = result.groupby("product_id", group_keys=False)["sales_quantity"]
    result["lag_1"] = grouped_sales.shift(1)
    result["lag_7"] = grouped_sales.shift(7)
    result["rolling_mean_7"] = (
        grouped_sales.shift(1).rolling(7).mean().reset_index(level=0, drop=True)
    )
    result["rolling_mean_14"] = (
        grouped_sales.shift(1).rolling(14).mean().reset_index(level=0, drop=True)
    )
    return result


def prepare_training_data(
    data: pd.DataFrame,
    category_mapping: dict[str, int] | None = None,
) -> tuple[pd.DataFrame, dict[str, int]]:
    mapping = category_mapping or build_category_mapping(data)
    prepared = add_category_feature(add_calendar_features(data), mapping)
    prepared = add_lag_features(prepared)
    prepared = prepared.replace([np.inf, -np.inf], np.nan)
    prepared = prepared.dropna(subset=FEATURE_COLUMNS + ["sales_quantity"]).reset_index(drop=True)
    return prepared, mapping


def build_future_feature_row(
    *,
    product_id: int,
    category: str,
    price: float,
    stock_quantity: float,
    promo: int,
    holiday: int,
    supplier_delay_days: float,
    forecast_date: pd.Timestamp,
    sales_history: list[float],
    category_mapping: dict[str, int],
) -> pd.DataFrame:
    row = pd.DataFrame(
        [
            {
                "date": forecast_date,
                "product_id": product_id,
                "category": category,
                "price": price,
                "stock_quantity": stock_quantity,
                "promo": promo,
                "holiday": holiday,
                "supplier_delay_days": supplier_delay_days,
                "sales_quantity": 0,
            }
        ]
    )
    row = add_category_feature(add_calendar_features(row), category_mapping)
    row["lag_1"] = sales_history[-1]
    row["lag_7"] = sales_history[-7] if len(sales_history) >= 7 else sales_history[-1]
    row["rolling_mean_7"] = pd.Series(sales_history[-7:]).mean()
    row["rolling_mean_14"] = pd.Series(sales_history[-14:]).mean()
    return row
