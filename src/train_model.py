import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from data_processing import DEFAULT_DATA_PATH, get_product_catalog, load_sales_data
from database import initialize_database, save_model_metrics
from feature_engineering import FEATURE_COLUMNS, prepare_training_data
from generate_dataset import generate_sales_dataset


ROOT_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT_DIR / "models" / "demand_model.joblib"
METRICS_PATH = ROOT_DIR / "models" / "metrics.json"


def mean_absolute_percentage_error(y_true, y_pred) -> float:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    mask = y_true != 0
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def train_model() -> dict:
    """Навчає RandomForestRegressor і зберігає модель, метрики та довідники."""
    if not DEFAULT_DATA_PATH.exists():
        DEFAULT_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        generate_sales_dataset().to_csv(DEFAULT_DATA_PATH, index=False, encoding="utf-8")

    raw_data = load_sales_data(DEFAULT_DATA_PATH)
    prepared, category_mapping = prepare_training_data(raw_data)

    if len(prepared) < 100:
        raise ValueError("Недостатньо історичних даних для навчання моделі.")

    split_date = prepared["date"].quantile(0.8)
    train = prepared[prepared["date"] <= split_date]
    test = prepared[prepared["date"] > split_date]

    model = RandomForestRegressor(
        n_estimators=220,
        max_depth=14,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=1,
    )
    model.fit(train[FEATURE_COLUMNS], train["sales_quantity"])
    predictions = model.predict(test[FEATURE_COLUMNS])

    metrics = {
        "MAE": round(float(mean_absolute_error(test["sales_quantity"], predictions)), 3),
        "RMSE": round(float(mean_squared_error(test["sales_quantity"], predictions) ** 0.5), 3),
        "MAPE": round(mean_absolute_percentage_error(test["sales_quantity"], predictions), 3),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "model": "RandomForestRegressor",
    }

    artifact = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "category_mapping": category_mapping,
        "products": get_product_catalog(DEFAULT_DATA_PATH).to_dict("records"),
        "last_date": str(raw_data["date"].max().date()),
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    initialize_database(seed=True)
    save_model_metrics(metrics)
    return metrics


def main() -> None:
    metrics = train_model()
    print("Модель навчено.")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
