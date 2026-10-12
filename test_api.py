"""
API-level tests. Run with: pytest test_api.py -v
Requires skillsbridge_readiness_model.pkl and model_feature_order.pkl
to be present (produced by the Colab notebook).
"""

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_prediction_returns_200():
    payload = {
        "cgpa": 8.2,
        "internships": 1,
        "projects": 4,
        "certifications": 2,
        "coding_score": 75,
        "communication_score": 60,
    }
    response = client.post("/v1/predict-readiness", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert 0 <= body["readiness_percent"] <= 100
    assert body["label"] in ["Ready", "Needs Improvement"]


def test_invalid_cgpa_rejected():
    payload = {
        "cgpa": 15,  # out of valid 0-10 range
        "internships": 1,
        "projects": 4,
        "certifications": 2,
        "coding_score": 75,
        "communication_score": 60,
    }
    response = client.post("/v1/predict-readiness", json=payload)
    assert response.status_code == 422  # Pydantic validation should reject this


def test_missing_field_rejected():
    payload = {"cgpa": 8.2}  # missing required fields
    response = client.post("/v1/predict-readiness", json=payload)
    assert response.status_code == 422


def test_explanation_fields_present():
    payload = {
        "cgpa": 6.5,
        "internships": 0,
        "projects": 1,
        "certifications": 0,
        "coding_score": 40,
        "communication_score": 50,
    }
    response = client.post("/v1/predict-readiness", json=payload)
    body = response.json()
    assert "weakest_factors" in body
    assert "strongest_factors" in body
