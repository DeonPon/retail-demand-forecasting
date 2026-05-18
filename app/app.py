import os
import sys
import secrets
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, redirect, render_template, request, session, url_for


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.append(str(SRC_DIR))
sys.path.append(str(ROOT_DIR / "app" / "auth"))

from auth import authenticate, login_required
from data_processing import DEFAULT_DATA_PATH, load_sales_data, save_uploaded_dataset
from database import initialize_database, seed_from_csv
from generate_dataset import main as generate_dataset
from predict import (
    ModelNotTrainedError,
    NotEnoughDataError,
    ProductNotFoundError,
    forecast_product,
    get_metrics,
    get_products,
    total_forecast_for_product,
)
from recommendations import purchase_recommendation
from train_model import train_model


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    initialize_database(seed=DEFAULT_DATA_PATH.exists())

    @app.errorhandler(ModelNotTrainedError)
    def handle_model_error(error):
        return jsonify({"status": "error", "message": str(error)}), 503

    @app.errorhandler(ProductNotFoundError)
    def handle_product_error(error):
        return jsonify({"status": "error", "message": str(error)}), 404

    @app.errorhandler(NotEnoughDataError)
    def handle_data_error(error):
        return jsonify({"status": "error", "message": str(error)}), 400

    @app.errorhandler(ValueError)
    def handle_value_error(error):
        return jsonify({"status": "error", "message": str(error)}), 400

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
        products = get_products()
        selected_product = int(request.args.get("product_id", products[0]["product_id"] if products else 1))
        metrics = get_metrics()
        forecast = forecast_product(selected_product, days=14)
        recommendation = purchase_recommendation(selected_product, days=14)
        recommendations = [purchase_recommendation(int(p["product_id"]), days=14) for p in products]
        products_to_order = sum(1 for item in recommendations if item["recommended_order_quantity"] > 0)
        average_forecast = round(
            sum(item["forecast_total"] for item in recommendations) / len(recommendations), 2
        ) if recommendations else 0

        return render_template(
            "dashboard.html",
            products=products,
            selected_product=selected_product,
            metrics=metrics,
            forecast=forecast,
            recommendation=recommendation,
            recommendations=recommendations,
            products_to_order=products_to_order,
            average_forecast=average_forecast,
        )

    @app.route("/products")
    @login_required
    def products_page():
        return render_template("products.html", products=get_products())

    @app.route("/forecast")
    @login_required
    def forecast_page():
        products = get_products()
        selected_product = int(request.args.get("product_id", products[0]["product_id"] if products else 1))
        forecast = forecast_product(selected_product, days=int(request.args.get("days", 14)))
        return render_template("forecast.html", products=products, selected_product=selected_product, forecast=forecast)

    @app.route("/recommendations")
    @login_required
    def recommendations_page():
        products = get_products()
        recommendations = [purchase_recommendation(int(p["product_id"]), days=14) for p in products]
        return render_template("recommendations.html", recommendations=recommendations)

    @app.route("/metrics")
    @login_required
    def metrics_page():
        return render_template("metrics.html", metrics=get_metrics())

    @app.route("/about")
    @login_required
    def about_page():
        return render_template("about.html")

    @app.route("/upload", methods=["POST"])
    @login_required
    def upload_from_form():
        response, status = upload_dataset()
        if status >= 400:
            return response
        return redirect(url_for("dashboard"))

    @app.route("/api/products")
    def api_products():
        return jsonify({"status": "success", "data": get_products()})

    @app.route("/api/forecast/<int:product_id>")
    def api_forecast(product_id: int):
        days = int(request.args.get("days", 14))
        return jsonify({"status": "success", "data": forecast_product(product_id, days=days)})

    @app.route("/api/recommendation/<int:product_id>")
    def api_recommendation(product_id: int):
        days = int(request.args.get("days", 14))
        return jsonify({"status": "success", "data": purchase_recommendation(product_id, days=days)})

    @app.route("/api/metrics")
    def api_metrics():
        return jsonify({"status": "success", "data": get_metrics()})

    @app.route("/api/upload", methods=["POST"])
    def api_upload():
        response, status = upload_dataset()
        return response, status

    @app.route("/api/retrain", methods=["POST"])
    def api_retrain():
        metrics = train_model()
        seed_from_csv()
        return jsonify({"status": "success", "message": "Модель перенавчено.", "metrics": metrics})

    @app.route("/api/system-info")
    def api_system_info():
        return jsonify(
            {
                "status": "success",
                "data": {
                    "project": "Інтелектуальна система прогнозування попиту",
                    "author": "Чесніший Денис Юрійович",
                    "technology": ["Python", "Flask", "Pandas", "Scikit-learn", "SQLite", "Bootstrap", "Chart.js"],
                    "model_status": "trained" if (ROOT_DIR / "models" / "demand_model.joblib").exists() else "not_trained",
                    "products_count": len(get_products()) if DEFAULT_DATA_PATH.exists() else 0,
                },
            }
        )

    @app.route("/api/chart-data/<int:product_id>")
    def api_chart_data(product_id: int):
        sales = load_sales_data(DEFAULT_DATA_PATH)
        product_sales = sales[sales["product_id"] == product_id].sort_values("date").tail(45)
        forecast = forecast_product(product_id, days=14)
        return jsonify(
            {
                "status": "success",
                "data": {
                    "actual": [
                        {"date": row["date"].date().isoformat(), "quantity": float(row["sales_quantity"])}
                        for row in product_sales.to_dict("records")
                    ],
                    "forecast": forecast["forecast"],
                },
            }
        )

    def upload_dataset():
        uploaded_file = request.files.get("file")
        if uploaded_file is None or uploaded_file.filename == "":
            return jsonify({"status": "error", "message": "CSV-файл не передано."}), 400

        try:
            data = pd.read_csv(uploaded_file)
            save_uploaded_dataset(data)
            seed_from_csv()
            metrics = train_model()
        except Exception as exc:
            return jsonify({"status": "error", "message": f"Не вдалося обробити CSV: {exc}"}), 400

        return jsonify({"status": "success", "message": "Дані оновлено, модель перенавчено.", "metrics": metrics}), 200

    return app


app = create_app()


if __name__ == "__main__":
    if not DEFAULT_DATA_PATH.exists():
        generate_dataset()
    if not (ROOT_DIR / "models" / "demand_model.joblib").exists():
        train_model()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
