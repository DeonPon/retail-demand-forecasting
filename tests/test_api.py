import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "app"))

from app import app


def test_api_products():
    client = app.test_client()
    response = client.get("/api/products")
    assert response.status_code == 200
    assert response.json["status"] == "success"


def test_api_forecast():
    client = app.test_client()
    response = client.get("/api/forecast/1?days=3")
    assert response.status_code == 200
    assert response.json["data"]["forecast_days"] == 3


def test_login_page_opens():
    client = app.test_client()
    response = client.get("/login")
    assert response.status_code == 200
