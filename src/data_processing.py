from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATA_PATH = ROOT_DIR / "data" / "sales_sample.csv"

REQUIRED_COLUMNS = {
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
}


def normalize_legacy_columns(data: pd.DataFrame) -> pd.DataFrame:
    """Підтримує старі назви колонок, якщо користувач завантажить попередній CSV."""
    rename_map = {
        "sales": "sales_quantity",
        "stock": "stock_quantity",
    }
    return data.rename(columns=rename_map)


def validate_sales_dataframe(data: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(data.columns)
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise ValueError(f"У CSV відсутні обов'язкові колонки: {missing_list}")


def load_sales_data(path: Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """Завантажує продажі з CSV, перевіряє структуру та приводить типи."""
    if not path.exists():
        raise FileNotFoundError("Файл з даними продажів не знайдено.")

    data = normalize_legacy_columns(pd.read_csv(path))
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
    return data.sort_values(["product_id", "date"]).reset_index(drop=True)


def save_uploaded_dataset(data: pd.DataFrame, path: Path = DEFAULT_DATA_PATH) -> None:
    """Зберігає новий CSV після перевірки структури."""
    data = normalize_legacy_columns(data)
    validate_sales_dataframe(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(path, index=False, encoding="utf-8")


def get_product_catalog(path: Path = DEFAULT_DATA_PATH) -> pd.DataFrame:
    data = load_sales_data(path)
    latest_stock = (
        data.sort_values("date")
        .groupby("product_id")
        .tail(1)[["product_id", "price", "stock_quantity"]]
    )
    catalog = data[["product_id", "product_name", "category"]].drop_duplicates()
    return catalog.merge(latest_stock, on="product_id", how="left").sort_values("product_id")
