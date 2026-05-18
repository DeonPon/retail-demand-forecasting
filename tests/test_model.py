import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "src"))

from data_processing import load_sales_data
from feature_engineering import FEATURE_COLUMNS, prepare_training_data
from recommendations import purchase_recommendation


def test_feature_engineering_creates_required_columns():
    data = load_sales_data()
    prepared, _ = prepare_training_data(data)
    for column in FEATURE_COLUMNS:
        assert column in prepared.columns
    assert len(prepared) > 0


def test_purchase_recommendation_shape():
    result = purchase_recommendation(1, days=7)
    assert "recommended_order_quantity" in result
    assert "explanation" in result
    assert result["forecast_days"] == 7
