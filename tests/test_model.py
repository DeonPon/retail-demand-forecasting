import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "src"))

from data_processing import load_sales_data
from feature_engineering import FEATURE_COLUMNS, prepare_training_data
from train_model import train_model


def test_feature_engineering_columns():
    data = load_sales_data()
    prepared, _ = prepare_training_data(data)
    for column in FEATURE_COLUMNS:
        assert column in prepared.columns
    assert len(prepared) > 1000


def test_training_returns_model_comparison():
    metrics = train_model()
    assert metrics["best_model_name"] in {"RandomForestRegressor", "GradientBoostingRegressor", "ExtraTreesRegressor"}
    assert len(metrics["model_comparison"]) == 3
    assert len(metrics["feature_importance"]) > 0
