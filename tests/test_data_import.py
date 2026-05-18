import sys
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "src"))

from data_processing import REQUIRED_COLUMNS, load_sales_data
from database import import_sales_dataframe


def test_import_sales_dataframe_counts():
    data = load_sales_data().head(200).copy()
    result = import_sales_dataframe(data, "test_import.csv")
    assert result["rows_count"] == 200
    assert result["products_count"] > 0


def test_required_columns_declared():
    assert "date" in REQUIRED_COLUMNS
    assert "sales_quantity" in REQUIRED_COLUMNS
