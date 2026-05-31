from __future__ import annotations

import io
import logging
import os
import secrets
import sys
from functools import lru_cache
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, make_response, redirect, render_template, request, session, url_for


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.append(str(SRC_DIR))
sys.path.append(str(ROOT_DIR / "app" / "auth"))

from auth import authenticate, login_required
from catalog import get_category_names
from data_processing import DEFAULT_DATA_PATH, REQUIRED_COLUMNS, clear_data_cache, load_sales_data, save_uploaded_dataset
from database import DATABASE_PATH, get_import_history, get_product_detail, get_system_overview, import_sales_dataframe, initialize_database, log_import
from generate_dataset import main as generate_dataset
from predict import METRICS_PATH, MODEL_PATH, ModelNotTrainedError, NotEnoughDataError, ProductNotFoundError, clear_model_cache, forecast_product, get_metrics, get_products
from recommendations import clear_recommendations_cache, exportable_recommendations, list_recommendations, purchase_recommendation
from train_model import train_model


FEATURE_LABELS = {
    "lag_1": "продажі за попередній день",
    "lag_7": "продажі за попередній тиждень",
    "lag_14": "продажі за попередні 14 днів",
    "rolling_mean_7": "середні продажі за 7 днів",
    "rolling_mean_14": "середні продажі за 14 днів",
    "promo": "акційний період",
    "price": "ціна товару",
    "stock_quantity": "залишок товару",
    "base_demand": "базовий попит категорії",
    "is_weekend": "вихідний день",
    "day_of_week": "день тижня",
    "supplier_delay_days": "затримка постачальника",
}


def humanize_feature_importance(items: list[dict]) -> list[dict]:
    return [{**item, "label": FEATURE_LABELS.get(item.get("feature", ""), item.get("feature", ""))} for item in items]


def forecast_day_meta(date_value: str) -> dict:
    date = pd.to_datetime(date_value)
    if date.dayofweek >= 5:
        return {"day_type": "вихідний", "comment": "можливе відхилення через поведінку покупців у вихідні"}
    if date.month in {6, 7, 8, 12}:
        return {"day_type": "робочий", "comment": "можливий сезонний вплив"}
    return {"day_type": "робочий", "comment": "звичайний день без додаткового сезонного маркера"}


@lru_cache(maxsize=1)
def get_demo_product_id() -> int:
    data = load_sales_data(DEFAULT_DATA_PATH)
    candidates = []
    for product_id, group in data.sort_values("date").groupby("product_id"):
        if len(group) < 60:
            continue
        sales = group["sales_quantity"].astype(float)
        mean_sales = float(sales.mean())
        if mean_sales <= 0:
            continue
        recent = group.tail(60)
        first_period = float(recent.head(30)["sales_quantity"].mean())
        last_period = float(recent.tail(30)["sales_quantity"].mean())
        variation = float(recent["sales_quantity"].std() or 0.0) / max(float(recent["sales_quantity"].mean()), 1.0)
        trend_strength = abs(last_period - first_period) / max(mean_sales, 1.0)
        promo_signal = float(recent["promo"].astype(int).sum()) / max(len(recent), 1)
        score = trend_strength + min(variation, 0.8) * 0.7 + promo_signal * 0.4
        if 0.08 <= variation <= 0.75:
            candidates.append((score, int(product_id)))
    if not candidates:
        return 9
    return max(candidates)[1]


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    initialize_database(seed=DEFAULT_DATA_PATH.exists())
    app.logger.setLevel(logging.INFO)

    def reset_runtime_caches() -> None:
        clear_data_cache()
        clear_model_cache()
        clear_recommendations_cache()
        get_demo_product_id.cache_clear()

    def set_notice(message: str, level: str = "info") -> None:
        session["notice"] = {"message": message, "level": level}

    def pop_notice() -> dict | None:
        return session.pop("notice", None)

    def build_json_error(message: str, status_code: int):
        return jsonify({"status": "error", "message": message}), status_code

    def empty_forecast(product_id: int, product_name: str = "Товар") -> dict:
        return {
            "product_id": product_id,
            "product_name": product_name,
            "category": "",
            "forecast_days": 14,
            "history_last_date": "",
            "forecast_start_date": "",
            "forecast_end_date": "",
            "forecast": [],
            "forecast_total": 0,
            "forecast_min": 0,
            "forecast_max": 0,
            "forecast_avg": 0,
            "trend": "недоступний",
            "factors": [],
            "plain_explanation": "Прогноз тимчасово недоступний, перевірте модель або дані.",
            "feature_importance": [],
        }

    def build_dashboard_context(selected_product: int, days: int = 14) -> dict:
        products = get_products()
        product_ids = {product["product_id"] for product in products}
        if selected_product not in product_ids and products:
            selected_product = get_demo_product_id()

        metrics = get_metrics()
        overview = get_system_overview()
        imports = get_import_history(limit=5)
        forecast_error = None

        try:
            forecast = forecast_product(selected_product, days=days, persist=False)
        except Exception:
            app.logger.exception("Помилка побудови прогнозу для dashboard")
            selected_name = next((product["product_name"] for product in products if product["product_id"] == selected_product), "Товар")
            forecast = empty_forecast(selected_product, selected_name)
            forecast_error = "Прогноз тимчасово недоступний, перевірте модель або дані."

        return {
            "products": products,
            "selected_product": selected_product,
            "forecast": forecast,
            "forecast_error": forecast_error,
            "metrics": metrics,
            "overview": overview,
            "imports": imports,
            "feature_importance": metrics.get("feature_importance", []),
            "human_feature_importance": humanize_feature_importance(metrics.get("feature_importance", [])),
            "notice": pop_notice(),
        }

    @app.errorhandler(ModelNotTrainedError)
    def handle_model_error(error):
        return build_json_error(str(error), 503)

    @app.errorhandler(ProductNotFoundError)
    def handle_product_error(error):
        return build_json_error(str(error), 404)

    @app.errorhandler(NotEnoughDataError)
    def handle_data_error(error):
        return build_json_error(str(error), 400)

    @app.errorhandler(ValueError)
    def handle_value_error(error):
        return build_json_error(str(error), 400)

    @app.errorhandler(500)
    def handle_internal_error(error):
        app.logger.exception("Внутрішня помилка сервера: %s", error)
        if request.path.startswith("/api/") or request.path == "/health":
            return build_json_error("Внутрішня помилка сервера. Спробуйте ще раз пізніше.", 500)
        return render_template("error.html", title="Помилка сервера", message="Сталася внутрішня помилка. Спробуйте оновити сторінку або перевірити модель і дані."), 500

    @app.route("/favicon.svg")
    def favicon():
        return app.send_static_file("img/favicon.svg")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            user = authenticate(request.form.get("username", ""), request.form.get("password", ""))
            if user:
                session["user"] = {"username": user["username"], "role": user["role"]}
                return redirect(url_for("dashboard"))
            error = "Невірний логін або пароль."
        return render_template("login.html", error=error)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/")
    def dashboard():
        selected_product = int(request.args.get("product_id", get_demo_product_id()))
        return render_template("dashboard.html", **build_dashboard_context(selected_product))

    @app.route("/dataset")
    @app.route("/products")
    def products_page():
        query = request.args.get("q", "").strip().lower()
        category = request.args.get("category", "")
        sort = request.args.get("sort", "demand_desc")
        history = load_sales_data(DEFAULT_DATA_PATH)
        dataset_summary = {
            "date_from": history["date"].min().date().isoformat(),
            "date_to": history["date"].max().date().isoformat(),
            "products_count": int(history["product_id"].nunique()),
            "categories_count": int(history["category"].nunique()),
            "sales_rows_count": int(len(history)),
            "average_daily_demand": round(float(history["sales_quantity"].mean()), 2),
        }
        grouped = (
            history.groupby(["product_id", "product_name", "category"], as_index=False)
            .agg(
                average_price=("price", "mean"),
                records_count=("sales_quantity", "count"),
                average_daily_demand=("sales_quantity", "mean"),
                min_sales=("sales_quantity", "min"),
                max_sales=("sales_quantity", "max"),
                date_from=("date", "min"),
                date_to=("date", "max"),
            )
        )
        products = []
        for row in grouped.to_dict("records"):
            products.append(
                {
                    **row,
                    "average_price": round(float(row["average_price"]), 2),
                    "average_daily_demand": round(float(row["average_daily_demand"]), 2),
                    "min_sales": round(float(row["min_sales"]), 2),
                    "max_sales": round(float(row["max_sales"]), 2),
                    "date_from": pd.Timestamp(row["date_from"]).date().isoformat(),
                    "date_to": pd.Timestamp(row["date_to"]).date().isoformat(),
                }
            )

        if query:
            products = [item for item in products if query in item["product_name"].lower()]
        if category:
            products = [item for item in products if item["category"] == category]

        sort_options = {
            "name": lambda item: item["product_name"],
            "demand_desc": lambda item: -item["average_daily_demand"],
            "demand_asc": lambda item: item["average_daily_demand"],
            "records_desc": lambda item: -item["records_count"],
            "price_desc": lambda item: -item["average_price"],
        }
        products = sorted(products, key=sort_options.get(sort, sort_options["demand_desc"]))
        return render_template("products.html", products=products, dataset_summary=dataset_summary, categories=get_category_names(), selected_category=category, query=request.args.get("q", ""), selected_sort=sort, notice=pop_notice())

    @app.route("/forecast")
    def forecast_page():
        products = get_products()
        days = int(request.args.get("days", 14))
        selected_product = int(request.args.get("product_id", products[8]["product_id"] if len(products) > 8 else products[0]["product_id"] if products else 1))
        forecast = forecast_product(selected_product, days=days, persist=False)
        forecast["forecast"] = [{**row, **forecast_day_meta(row["date"])} for row in forecast["forecast"]]
        forecast["feature_importance_human"] = humanize_feature_importance(forecast.get("feature_importance", []))
        return render_template("forecast.html", products=products, selected_product=selected_product, days=days, forecast=forecast, metrics=get_metrics())

    @app.route("/recommendations")
    def recommendations_page():
        days = int(request.args.get("days", 14))
        recommendations = list_recommendations(days=days)
        return render_template("recommendations.html", recommendations=recommendations, days=days)

    @app.route("/recommendations/export.csv")
    def recommendations_export():
        days = int(request.args.get("days", 14))
        frame = pd.DataFrame(exportable_recommendations(days=days))
        csv_buffer = io.StringIO()
        frame.to_csv(csv_buffer, index=False)
        response = make_response("\ufeff" + csv_buffer.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
        response.headers["Content-Disposition"] = "attachment; filename=recommendations.csv"
        return response

    @app.route("/metrics")
    def metrics_page():
        metrics = get_metrics()
        return render_template("metrics.html", metrics=metrics, human_feature_importance=humanize_feature_importance(metrics.get("feature_importance", [])[:7]), overview=get_system_overview(), imports=get_import_history(limit=5))

    @app.route("/about")
    def about_page():
        return render_template("about.html", metrics=get_metrics(), overview=get_system_overview())

    @app.route("/download/sample-csv")
    def download_sample_csv():
        csv_text = DEFAULT_DATA_PATH.read_text(encoding="utf-8")
        response = make_response("\ufeff" + csv_text)
        response.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
        response.headers["Content-Disposition"] = "attachment; filename=sales_sample_excel.csv"
        return response

    @app.route("/upload", methods=["POST"])
    def upload_from_form():
        payload, status = upload_dataset(run_training=True)
        set_notice(payload.get_json().get("message", "Операцію виконано."), "success" if status < 400 else "error")
        return redirect(url_for("dashboard"))

    @app.route("/api/products")
    def api_products():
        return jsonify({"status": "success", "data": get_products()})

    @app.route("/api/products/<int:product_id>")
    def api_product_detail(product_id: int):
        detail = get_product_detail(product_id)
        if detail is None:
            return build_json_error("Товар не знайдено.", 404)
        return jsonify({"status": "success", "data": detail})

    @app.route("/api/categories")
    def api_categories():
        return jsonify({"status": "success", "data": get_category_names()})

    @app.route("/api/forecast/<int:product_id>")
    def api_forecast(product_id: int):
        days = int(request.args.get("days", 14))
        return jsonify({"status": "success", "data": forecast_product(product_id, days=days, persist=False)})

    @app.route("/api/recommendation/<int:product_id>")
    def api_recommendation(product_id: int):
        days = int(request.args.get("days", 14))
        return jsonify({"status": "success", "data": purchase_recommendation(product_id, days=days, persist_forecast=False)})

    @app.route("/api/recommendations")
    def api_recommendations():
        days = int(request.args.get("days", 14))
        return jsonify({"status": "success", "data": list_recommendations(days=days)})

    @app.route("/api/metrics")
    def api_metrics():
        return jsonify({"status": "success", "data": get_metrics()})

    @app.route("/api/feature-importance")
    def api_feature_importance():
        return jsonify({"status": "success", "data": get_metrics().get("feature_importance", [])})

    @app.route("/api/imports")
    def api_imports():
        return jsonify({"status": "success", "data": get_import_history(limit=20)})

    @app.route("/api/upload", methods=["POST"])
    def api_upload():
        return upload_dataset(run_training=True)

    @app.route("/api/retrain", methods=["POST"])
    def api_retrain():
        reset_runtime_caches()
        metrics = train_model()
        reset_runtime_caches()
        return jsonify({"status": "success", "message": "Модель успішно перенавчено.", "metrics": metrics})

    @app.route("/health")
    def health():
        return jsonify(
            {
                "status": "ok",
                "app": "running",
                "model_exists": MODEL_PATH.exists(),
                "metrics_exists": METRICS_PATH.exists(),
                "data_exists": DEFAULT_DATA_PATH.exists(),
                "database_exists": DATABASE_PATH.exists(),
            }
        )

    @app.route("/api/system-info")
    def api_system_info():
        overview = get_system_overview()
        return jsonify({"status": "success", "data": {"project": "Інтелектуальна система прогнозування попиту на товари", "author": "Чесніший Денис Юрійович", **overview}})

    @app.route("/api/chart-data/<int:product_id>")
    def api_chart_data(product_id: int):
        days = int(request.args.get("days", 14))
        sales = load_sales_data(DEFAULT_DATA_PATH)
        product_sales = sales[sales["product_id"] == product_id].sort_values("date").tail(60)
        forecast = forecast_product(product_id, days=days, persist=False)
        return jsonify(
            {
                "status": "success",
                "data": {
                    "history": [
                        {"date": row["date"].date().isoformat(), "sales": float(row["sales_quantity"]), "promo": bool(int(row["promo"]))}
                        for row in product_sales.to_dict("records")
                    ],
                    "forecast": [{"date": row["date"], "predicted": float(row["predicted_quantity"])} for row in forecast["forecast"]],
                    "forecast_start_date": forecast["forecast_start_date"],
                    "history_last_date": forecast["history_last_date"],
                },
            }
        )

    def upload_dataset(run_training: bool):
        uploaded_file = request.files.get("file")
        if uploaded_file is None or uploaded_file.filename == "":
            return build_json_error("CSV-файл не передано. Обов'язкові колонки: " + ", ".join(REQUIRED_COLUMNS), 400)
        try:
            frame = pd.read_csv(uploaded_file)
            save_uploaded_dataset(frame)
            imported = import_sales_dataframe(load_sales_data(DEFAULT_DATA_PATH), uploaded_file.filename or "uploaded.csv")
            reset_runtime_caches()
            metrics = None
            if run_training:
                metrics = train_model()
                reset_runtime_caches()
            message = imported["message"] if not metrics else imported["message"] + " Прогноз сформовано на основі оновленої моделі."
            return jsonify({"status": "success", "message": message, "import": imported, "metrics": metrics}), 200
        except Exception as exc:
            app.logger.exception("Помилка імпорту CSV")
            log_import(uploaded_file.filename or "uploaded.csv", 0, 0, "error", str(exc))
            return build_json_error(str(exc), 400)

    return app


app = create_app()


if __name__ == "__main__":
    if not DEFAULT_DATA_PATH.exists():
        generate_dataset()
    if not MODEL_PATH.exists():
        train_model()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
