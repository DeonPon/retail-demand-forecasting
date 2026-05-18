import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from werkzeug.security import generate_password_hash


ROOT_DIR = Path(__file__).resolve().parents[1]
DATABASE_PATH = ROOT_DIR / "retail_demand.db"
SCHEMA_PATH = ROOT_DIR / "docs" / "database_schema.sql"
DATA_PATH = ROOT_DIR / "data" / "sales_sample.csv"


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
    price REAL NOT NULL,
    stock_quantity REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    quantity REAL NOT NULL,
    promo INTEGER NOT NULL DEFAULT 0,
    holiday INTEGER NOT NULL DEFAULT 0,
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
    mae REAL NOT NULL,
    rmse REAL NOT NULL,
    mape REAL NOT NULL,
    created_at TEXT NOT NULL
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
    SCHEMA_PATH.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_PATH.write_text(SCHEMA_SQL.strip() + "\n", encoding="utf-8")


def ensure_demo_user() -> None:
    with get_connection() as connection:
        user = connection.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
        if user is None:
            connection.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                ("admin", generate_password_hash("admin123"), "admin", datetime.now(UTC).isoformat()),
            )


def seed_from_csv(csv_path: Path = DATA_PATH) -> None:
    if not csv_path.exists():
        return

    data = pd.read_csv(csv_path)
    with get_connection() as connection:
        connection.execute("DELETE FROM sales")
        connection.execute("DELETE FROM products")

        products = (
            data.sort_values("date")
            .groupby("product_id")
            .tail(1)[["product_id", "product_name", "category", "price", "stock_quantity"]]
        )
        for row in products.to_dict("records"):
            connection.execute(
                """
                INSERT OR REPLACE INTO products (id, name, category, price, stock_quantity)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    int(row["product_id"]),
                    str(row["product_name"]),
                    str(row["category"]),
                    float(row["price"]),
                    float(row["stock_quantity"]),
                ),
            )

        for row in data.to_dict("records"):
            connection.execute(
                """
                INSERT INTO sales (product_id, date, quantity, promo, holiday)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    int(row["product_id"]),
                    str(row["date"]),
                    float(row["sales_quantity"]),
                    int(row["promo"]),
                    int(row["holiday"]),
                ),
            )


def initialize_database(seed: bool = False) -> None:
    create_schema()
    ensure_demo_user()
    if seed:
        seed_from_csv()


def get_user_by_username(username: str) -> dict | None:
    with get_connection() as connection:
        row = connection.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    return dict(row) if row else None


def read_products_from_db() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute("SELECT * FROM products ORDER BY id").fetchall()
    return [dict(row) for row in rows]


def save_forecast_rows(product_id: int, rows: list[dict]) -> None:
    created_at = datetime.now(UTC).isoformat()
    with get_connection() as connection:
        for row in rows:
            connection.execute(
                """
                INSERT INTO forecasts (product_id, forecast_date, predicted_quantity, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (product_id, row["date"], float(row["predicted_quantity"]), created_at),
            )


def save_model_metrics(metrics: dict) -> None:
    with get_connection() as connection:
        connection.execute(
            "INSERT INTO model_metrics (mae, rmse, mape, created_at) VALUES (?, ?, ?, ?)",
            (
                float(metrics.get("MAE", 0)),
                float(metrics.get("RMSE", 0)),
                float(metrics.get("MAPE", 0)),
                datetime.now(UTC).isoformat(),
            ),
        )


if __name__ == "__main__":
    initialize_database(seed=True)
    print(f"Базу даних ініціалізовано: {DATABASE_PATH}")
