from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from werkzeug.security import generate_password_hash

from data_processing import DEFAULT_DATA_PATH, get_product_catalog, load_sales_data


ROOT_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT_DIR / "retail_demand.db"
SCHEMA_PATH = ROOT_DIR / "docs" / "database_schema.sql"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'manager',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    product_icon TEXT,
    price REAL NOT NULL,
    stock_quantity REAL NOT NULL,
    base_demand REAL DEFAULT 0,
    seasonality_type TEXT DEFAULT 'stable',
    shelf_life_days INTEGER DEFAULT 365,
    supplier_name TEXT,
    region TEXT
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    stock_quantity REAL NOT NULL,
    promo INTEGER NOT NULL DEFAULT 0,
    holiday INTEGER NOT NULL DEFAULT 0,
    supplier_delay_days REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    forecast_date TEXT NOT NULL,
    predicted_quantity REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS model_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_name TEXT NOT NULL,
    mae REAL NOT NULL,
    rmse REAL NOT NULL,
    mape REAL NOT NULL,
    created_at TEXT NOT NULL,
    raw_metrics_json TEXT
);

CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    rows_count INTEGER NOT NULL,
    products_count INTEGER NOT NULL,
    imported_at TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    forecast_days INTEGER NOT NULL,
    forecast_quantity REAL NOT NULL,
    current_stock REAL NOT NULL,
    safety_stock REAL NOT NULL,
    recommended_order_quantity REAL NOT NULL,
    explanation TEXT NOT NULL,
    priority TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def create_schema() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as connection:
        connection.executescript(SCHEMA_SQL)
    SCHEMA_PATH.write_text(SCHEMA_SQL.strip() + "\n", encoding="utf-8")


def ensure_demo_user() -> None:
    with get_connection() as connection:
        user = connection.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
        if user is None:
            connection.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                ("admin", generate_password_hash("admin123"), "admin", datetime.now(UTC).isoformat()),
            )


def log_import(filename: str, rows_count: int, products_count: int, status: str, error_message: str = "") -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO imports (filename, rows_count, products_count, imported_at, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (filename, rows_count, products_count, datetime.now(UTC).isoformat(), status, error_message),
        )


def import_sales_dataframe(data: pd.DataFrame, filename: str) -> dict:
    catalog = (
        data.sort_values("date")
        .groupby("product_id")
        .tail(1)[
            [
                "product_id",
                "product_name",
                "category",
                "product_icon",
                "price",
                "stock_quantity",
                "base_demand",
                "seasonality_type",
                "shelf_life_days",
                "supplier_name",
                "region",
            ]
        ]
    )

    with get_connection() as connection:
        connection.execute("DELETE FROM sales")
        connection.execute("DELETE FROM products")

        for row in catalog.to_dict("records"):
            connection.execute(
                """
                INSERT OR REPLACE INTO products (
                    id, name, category, product_icon, price, stock_quantity, base_demand,
                    seasonality_type, shelf_life_days, supplier_name, region
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(row["product_id"]),
                    str(row["product_name"]),
                    str(row["category"]),
                    str(row.get("product_icon", "")),
                    float(row["price"]),
                    float(row["stock_quantity"]),
                    float(row.get("base_demand", 0)),
                    str(row.get("seasonality_type", "stable")),
                    int(row.get("shelf_life_days", 365)),
                    str(row.get("supplier_name", "")),
                    str(row.get("region", "")),
                ),
            )

        for row in data.to_dict("records"):
            connection.execute(
                """
                INSERT INTO sales (
                    product_id, date, quantity, price, stock_quantity, promo, holiday, supplier_delay_days
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(row["product_id"]),
                    str(row["date"]),
                    float(row["sales_quantity"]),
                    float(row["price"]),
                    float(row["stock_quantity"]),
                    int(row["promo"]),
                    int(row["holiday"]),
                    float(row["supplier_delay_days"]),
                ),
            )

    result = {
        "rows_count": int(len(data)),
        "products_count": int(data["product_id"].nunique()),
        "message": f"Дані продажів завантажено: {int(data['product_id'].nunique())} товарів і {len(data)} записів. Система готова до аналізу.",
    }
    log_import(filename, result["rows_count"], result["products_count"], "success")
    return result


def seed_from_csv(csv_path: Path = DEFAULT_DATA_PATH) -> dict | None:
    if not csv_path.exists():
        return None
    data = load_sales_data(csv_path)
    return import_sales_dataframe(data, csv_path.name)


def initialize_database(seed: bool = False) -> None:
    create_schema()
    ensure_demo_user()
    with get_connection() as connection:
        products_count = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        sales_count = connection.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    if seed and (products_count == 0 or sales_count == 0):
        seed_from_csv()


def get_user_by_username(username: str) -> dict | None:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def save_forecast_rows(product_id: int, rows: list[dict]) -> None:
    created_at = datetime.now(UTC).isoformat()
    with get_connection() as connection:
        for row in rows:
            connection.execute(
                "INSERT INTO forecasts (product_id, forecast_date, predicted_quantity, created_at) VALUES (?, ?, ?, ?)",
                (product_id, row["date"], float(row["predicted_quantity"]), created_at),
            )


def save_model_metrics(metrics: dict) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO model_metrics (model_name, mae, rmse, mape, created_at, raw_metrics_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(metrics.get("best_model_name", metrics.get("model", "unknown"))),
                float(metrics.get("MAE", 0)),
                float(metrics.get("RMSE", 0)),
                float(metrics.get("MAPE", 0)),
                datetime.now(UTC).isoformat(),
                pd.Series(metrics).to_json(force_ascii=False),
            ),
        )


def save_recommendation_history(items: list[dict]) -> None:
    created_at = datetime.now(UTC).isoformat()
    with get_connection() as connection:
        for item in items:
            connection.execute(
                """
                INSERT INTO recommendations (
                    product_id, forecast_days, forecast_quantity, current_stock, safety_stock,
                    recommended_order_quantity, explanation, priority, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(item["product_id"]),
                    int(item["forecast_days"]),
                    float(item["forecast_total"]),
                    float(item["current_stock"]),
                    float(item["safety_stock"]),
                    float(item["recommended_order_quantity"]),
                    str(item["explanation"]),
                    str(item["priority"]),
                    created_at,
                ),
            )


def get_import_history(limit: int = 20) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM imports ORDER BY imported_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


def get_system_overview() -> dict:
    data = load_sales_data(DEFAULT_DATA_PATH)
    with get_connection() as connection:
        last_import = connection.execute("SELECT * FROM imports ORDER BY imported_at DESC LIMIT 1").fetchone()
        last_metrics = connection.execute("SELECT * FROM model_metrics ORDER BY created_at DESC LIMIT 1").fetchone()
    return {
        "products_count": int(data["product_id"].nunique()),
        "categories_count": int(data["category"].nunique()),
        "sales_rows_count": int(len(data)),
        "last_import_at": last_import["imported_at"] if last_import else None,
        "last_import_status": last_import["status"] if last_import else "not_imported",
        "last_training_at": last_metrics["created_at"] if last_metrics else None,
        "best_model_name": last_metrics["model_name"] if last_metrics else None,
    }


def get_product_detail(product_id: int) -> dict | None:
    catalog = get_product_catalog(DEFAULT_DATA_PATH)
    matches = catalog[catalog["product_id"] == product_id]
    if matches.empty:
        return None
    return matches.iloc[0].to_dict()
