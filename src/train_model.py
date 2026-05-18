from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor, GradientBoostingRegressor, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from data_processing import DEFAULT_DATA_PATH, load_sales_data
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


def evaluate_model(model, train_x, train_y, test_x, test_y) -> tuple[object, dict]:
    model.fit(train_x, train_y)
    predictions = model.predict(test_x)
    metrics = {
        "MAE": round(float(mean_absolute_error(test_y, predictions)), 3),
        "RMSE": round(float(mean_squared_error(test_y, predictions) ** 0.5), 3),
        "MAPE": round(mean_absolute_percentage_error(test_y, predictions), 3),
    }
    return model, metrics


def train_model() -> dict:
    initialize_database(seed=DEFAULT_DATA_PATH.exists())

    if not DEFAULT_DATA_PATH.exists():
        DEFAULT_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        generate_sales_dataset().to_csv(DEFAULT_DATA_PATH, index=False, encoding="utf-8")

    raw_data = load_sales_data(DEFAULT_DATA_PATH)
    prepared, category_mapping = prepare_training_data(raw_data)
    if len(prepared) < 500:
        raise ValueError("Недостатньо історичних даних для навчання моделі.")

    split_date = prepared["date"].quantile(0.8)
    train = prepared[prepared["date"] <= split_date]
    test = prepared[prepared["date"] > split_date]
    train_x = train[FEATURE_COLUMNS]
    train_y = train["sales_quantity"]
    test_x = test[FEATURE_COLUMNS]
    test_y = test["sales_quantity"]

    candidate_models = {
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=40, max_depth=10, min_samples_leaf=2, random_state=42, n_jobs=1
        ),
        "GradientBoostingRegressor": GradientBoostingRegressor(
            random_state=42, n_estimators=80, learning_rate=0.06, max_depth=3
        ),
        "ExtraTreesRegressor": ExtraTreesRegressor(
            n_estimators=50, max_depth=12, min_samples_leaf=2, random_state=42, n_jobs=1
        ),
    }

    model_scores: list[dict] = []
    best_model_name = ""
    best_model = None
    best_metrics = None

    for model_name, model in candidate_models.items():
        trained_model, metrics = evaluate_model(model, train_x, train_y, test_x, test_y)
        model_scores.append({"model": model_name, **metrics})
        if best_metrics is None or metrics["MAPE"] < best_metrics["MAPE"]:
            best_model_name = model_name
            best_model = trained_model
            best_metrics = metrics

    feature_importance_pairs: list[dict] = []
    if hasattr(best_model, "feature_importances_"):
        feature_importance_pairs = [
            {"feature": feature, "importance": round(float(importance), 5)}
            for feature, importance in sorted(
                zip(FEATURE_COLUMNS, best_model.feature_importances_),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

    metrics_payload = {
        **best_metrics,
        "best_model_name": best_model_name,
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "last_training_at": datetime.now(UTC).isoformat(),
        "feature_importance": feature_importance_pairs[:10],
        "model_comparison": model_scores,
    }

    artifact = {
        "model": best_model,
        "feature_columns": FEATURE_COLUMNS,
        "category_mapping": category_mapping,
        "last_date": str(raw_data["date"].max().date()),
        "metrics": metrics_payload,
    }

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, MODEL_PATH, compress=("xz", 3))
    METRICS_PATH.write_text(json.dumps(metrics_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    save_model_metrics(metrics_payload)
    return metrics_payload


def main() -> None:
    metrics = train_model()
    print("Модель навчено.")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
