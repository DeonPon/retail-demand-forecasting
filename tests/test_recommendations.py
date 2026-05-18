import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR / "src"))

from recommendations import list_recommendations, purchase_recommendation


def test_single_recommendation_contains_priority():
    result = purchase_recommendation(1, days=14)
    assert result["priority"] in {"високий", "середній", "низький"}
    assert "recommended_order_quantity" in result


def test_recommendations_list_non_empty():
    recommendations = list_recommendations(days=14)
    assert len(recommendations) > 20
