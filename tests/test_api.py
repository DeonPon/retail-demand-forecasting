import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "app"))

from app import app


def test_core_api_endpoints():
    client = app.test_client()
    assert client.get("/health").status_code == 200
    assert client.get("/api/products").status_code == 200
    assert client.get("/api/metrics").status_code == 200
    assert client.get("/api/feature-importance").status_code == 200
    assert client.get("/api/recommendations?days=14").status_code == 200


def test_forecast_endpoint_shape():
    client = app.test_client()
    response = client.get("/api/forecast/1?days=7")
    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["forecast_days"] == 7
    assert "factors" in payload


def test_login_and_pages():
    client = app.test_client()
    login = client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
    assert login.status_code == 200
    for route in ["/", "/products", "/forecast", "/recommendations", "/metrics", "/about"]:
        assert client.get(route).status_code == 200
