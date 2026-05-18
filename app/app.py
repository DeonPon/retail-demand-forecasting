from __future__ import annotations

import io
import os
import secrets
import sys
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, make_response, redirect, render_template, request, send_file, session, url_for


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.append(str(SRC_DIR))
sys.path.append(str(ROOT_DIR / "app" / "auth"))

from auth import authenticate, login_required
from catalog import get_category_names
from data_processing import (
    DEFAULT_DATA_PATH,
    REQUIRED_COLUMNS,
    clear_data_cache,
    get_product_catalog,
    load_sales_data,
    save_uploaded_dataset,
)
from database import (
    DATABASE_PATH,
    get_import_history,
    get_product_detail,
    get_system_overview,
    import_sales_dataframe,
    initialize_database,
    log_import,
)
from generate_dataset import main as generate_dataset
from predict import (
    METRICS_PATH,
    MODEL_PATH,
    ModelNotTrainedError,
    NotEnoughDataError,
    ProductNotFoundError,
    clear_model_cache,
    forecast_product,
    get_metrics,
    get_products,
)
from recommendations import clear_recommendations_cache, exportable_recommendations, list_recommendations, purchase_recommendation
from train_model import train_model


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    initialize_database(seed=DEFAULT_DATA_PATH.exists())

    def reset_runtime_caches() -> None:
        clear_data_cache()
        clear_model_cache()
        clear_recommendations_cache()

    def set_notice(message: str, level: str = "info") -> None:
        session["notice"] = {"message": message, "level": level}

    def pop_notice() -> dict | None:
        return session.pop("notice", None)

    def build_dashboard_context(selected_product: int, days: int = 14) -> dict:
        products = get_products()
        recommendations = list_recommendations(days=days)
        product_ids = {product["product_id"] for product in products}
        if selected_product not in product_ids and products:
            selected_product = int(products[0]["product_id"])
        forecast = forecast_product(selected_product, days=days, persist=False)
        recommendation = purchase_recommendation(selected_product, days=days, persist_forecast=False)
        metrics = get_metrics()
        overview = get_system_overview()
        imports = get_import_history(limit=5)
        top_to_buy = [item for item in recommendations if item["recommended_order_quantity"] > 0][:8]
        risk_items = [item for item in recommendations if item["stock_cover_days"] < 6][:8]
        feature_importance = metrics.get("feature_importance", [])
        status_cards = [
            {"label": "Модель", "ok": MODEL_PATH.exists()},
            {"label": "Метрики", "ok": METRICS_PATH.exists()},
            {"label": "Дані", "ok": DEFAULT_DATA_PATH.exists()},
            {"label": "База даних", "ok": DATABASE_PATH.exists()},
        ]
        average_forecast = round(sum(item["forecast_total"] for item in recommendations) / max(len(recommendations), 1), 2)
        return {
            "products": products,
            "selected_product": selected_product,
            "forecast": forecast,
            "recommendation": recommendation,
            "recommendations": recommendations,
            "metrics": metrics,
            "overview": overview,
            "imports": imports,
            "top_to_buy": top_to_buy,
            "risk_items": risk_items,
            "feature_importance": feature_importance,
            "average_forecast": average_forecast,
            "products_to_order": sum(1 for item in recommendations if item["recommended_order_quantity"] > 0),
            "status_cards": status_cards,
            "notice": pop_notice(),
        }

    def build_json_error(message: str, status_code: int):
        return jsonify({"status": "error", "message": message}), status_code

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
    @login_required
    def dashboard():
        selected_product = int(request.args.get("product_id", 1))
        return render_template("dashboard.html", **build_dashboard_context(selected_product))

    @app.route("/products")
    @login_required
    def products_page():
        query = request.args.get("q", "").strip().lower()
        category = request.args.get("category", "")
        sort = request.args.get("sort", "stock_asc")
        days = int(request.args.get("days", 14))
        catalog = get_product_catalog()
        recommendations_map = {item["product_id"]: item for item in list_recommendations(days=days)}
        history = load_sales_data(DEFAULT_DATA_PATH)
        recent_avg = history.groupby("product_id").tail(7).groupby("product_id")["sales_quantity"].mean().to_dict()

        products = []
        for row in catalog.to_dict("records"):
            recommendation = recommendations_map.get(row["product_id"], {})
            avg_7 = round(float(recent_avg.get(row["product_id"], 0)), 2)
            status_tags = []
            if row["stock_quantity"] < max(avg_7 * 4, row["base_demand"] * 2):
                status_tags.append("низький залишок")
            if recommendation.get("recommended_order_quantity", 0) > 0:
                status_tags.append("потребує закупівлі")
            if avg_7 >= row["base_demand"] * 0.95:
                status_tags.append("стабільний попит")
            products.append(
                {
                    **row,
                    "avg_sales_7": avg_7,
                    "forecast_14": recommendation.get("forecast_total", 0),
                    "recommended_order_quantity": recommendation.get("recommended_order_quantity", 0),
                    "status_tags": status_tags,
                }
            )

        if query:
            products = [item for item in products if query in item["product_name"].lower()]
        if category:
            products = [item for item in products if item["category"] == category]

        sort_options = {
            "name": lambda item: item["product_name"],
            "stock_asc": lambda item: item["stock_quantity"],
            "stock_desc": lambda item: -item["stock_quantity"],
            "forecast_desc": lambda item: -item["forecast_14"],
        }
        products = sorted(products, key=sort_options.get(sort, sort_options["stock_asc"]))
        return render_template(
            "products.html",
            products=products,
            categories=get_category_names(),
            selected_category=category,
            query=request.args.get("q", ""),
            selected_sort=sort,
        )

    @app.route("/forecast")
    @login_required
    def forecast_page():
        products = get_products()
        days = int(request.args.get("days", 14))
        selected_product = int(request.args.get("product_id", products[0]["product_id"] if products else 1))
        forecast = forecast_product(selected_product, days=days, persist=False)
        return render_template(
            "forecast.html",
            products=products,
            selected_product=selected_product,
            days=days,
            forecast=forecast,
            metrics=get_metrics(),
        )

    @app.route("/recommendations")
    @login_required
    def recommendations_page():
        days = int(request.args.get("days", 14))
        recommendations = list_recommendations(days=days)
        return render_template("recommendations.html", recommendations=recommendations, days=days)

    @app.route("/recommendations/export.csv")
    @login_required
    def recommendations_export():
        days = int(request.args.get("days", 14))
        frame = pd.DataFrame(exportable_recommendations(days=days))
        csv_buffer = io.StringIO()
        frame.to_csv(csv_buffer, index=False)
        response = make_response(csv_buffer.getvalue())
        response.headers["Content-Type"] = "text/csv; charset=utf-8"
        response.headers["Content-Disposition"] = "attachment; filename=recommendations.csv"
        return response

    @app.route("/metrics")
    @login_required
    def metrics_page():
        return render_template("metrics.html", metrics=get_metrics(), overview=get_system_overview(), imports=get_import_history(limit=5))

    @app.route("/about")
    @login_required
    def about_page():
        return render_template("about.html", metrics=get_metrics(), overview=get_system_overview())

    @app.route("/download/sample-csv")
    @login_required
    def download_sample_csv():
        return send_file(DEFAULT_DATA_PATH, as_attachment=True, download_name="sales_sample.csv")

    @app.route("/upload", methods=["POST"])
    @login_required
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
        return jsonify({"status": "success", "data": forecast_product(product_id, days=days, persist=True)})

    @app.route("/api/recommendation/<int:product_id>")
    def api_recommendation(product_id: int):
        days = int(request.args.get("days", 14))
        return jsonify({"status": "success", "data": purchase_recommendation(product_id, days=days, persist_forecast=True)})

    @app.route("/api/recommendations")
    def api_recommendations():
        days = int(request.args.get("days", 14))
        return jsonify({"status": "success", "data": list_recommendations(days=days)})

    @app.route("/api/metrics")
    def api_metrics():
        return jsonify({"status": "success", "data": get_metrics()})

    @app.route("/api/feature-importance")
    def api_feature_importance():
        metrics = get_metrics()
        return jsonify({"status": "success", "data": metrics.get("feature_importance", [])})

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
        return jsonify(
            {
                "status": "success",
                "data": {
                    "project": "Інтелектуальна система прогнозування попиту на товари",
                    "author": "Чесніший Денис Юрійович",
                    **overview,
                },
            }
        )

    @app.route("/api/chart-data/<int:product_id>")
    def api_chart_data(product_id: int):
        days = int(request.args.get("days", 14))
        sales = load_sales_data(DEFAULT_DATA_PATH)
        product_sales = sales[sales["product_id"] == product_id].sort_values("date").tail(60)
        forecast = forecast_product(product_id, days=days, persist=False)
        promo_periods = [
            {"date": row["date"].date().isoformat(), "promo": int(row["promo"])}
            for row in product_sales.tail(30).to_dict("records")
        ]
        return jsonify(
            {
                "status": "success",
                "data": {
                    "actual": [{"date": row["date"].date().isoformat(), "quantity": float(row["sales_quantity"])} for row in product_sales.to_dict("records")],
                    "forecast": forecast["forecast"],
                    "promo_periods": promo_periods,
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
            message = imported["message"] if not metrics else imported["message"].replace("готова до перенавчання", "перенавчена і готова до роботи")
            return jsonify({"status": "success", "message": message, "import": imported, "metrics": metrics}), 200
        except Exception as exc:
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
