import pytest

from prototype.standardize import FIELDS, validate_extraction


def empty():
    return {field: {"value": None, "quote": ""} for field in FIELDS}


def test_unknown_values_are_not_estimated():
    result = validate_extraction(empty(), ["I built an API and wrote tests."], 8.2)
    assert result["fields"]["cgpa"]["value"] == 8.2
    assert result["fields"]["aptitude_test_score"]["value"] is None
    assert result["review_required"]


def test_exact_original_measurement_is_preserved():
    data = empty()
    quote = "My aptitude test score was 82 out of 100."
    data["aptitude_test_score"] = {"value": 82, "quote": quote}
    assert validate_extraction(data, [quote])["fields"]["aptitude_test_score"]["value"] == 82


def test_communication_score_cannot_become_soft_skills_rating():
    data = empty()
    quote = "Communication score: 85 out of 100."
    data["soft_skills_rating_original"] = {"value": 4.25, "quote": quote}
    with pytest.raises(ValueError):
        validate_extraction(data, [quote])


def test_invented_quote_rejected():
    data = empty()
    data["cgpa"] = {"value": 8.2, "quote": "CGPA 8.2 out of 10"}
    with pytest.raises(ValueError):
        validate_extraction(data, ["CGPA is not provided."])


def test_conflicting_entered_measurement_requires_review():
    data = empty()
    quote = "CGPA 8.2 out of 10"
    data["cgpa"] = {"value": 8.2, "quote": quote}
    result = validate_extraction(data, [quote], 7.5)
    assert result["conflicts"]
    assert result["fields"]["cgpa"]["value"] == 7.5


def test_coding_cannot_be_substituted_for_aptitude():
    data = empty()
    quote = "Coding score 82 out of 100"
    data["aptitude_test_score"] = {"value": 82, "quote": quote}
    with pytest.raises(ValueError):
        validate_extraction(data, [quote])


def test_saved_standardization_is_persisted_and_returned(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from prototype.app import create_app
    import prototype.standardize as standardizer
    monkeypatch.delenv("SKILLSBRIDGE_API_KEY", raising=False)
    async def extract(profile):
        return validate_extraction(empty(), [], profile.cgpa)
    monkeypatch.setattr(standardizer, "standardize", extract)
    with TestClient(create_app(tmp_path)) as client:
        profile = {"student_name": "Synthetic profile", "cgpa": 8.2, "evaluator": "offline", "evidence": []}
        key = client.post("/v2/assessments", json=profile).json()["id"]
        result = client.post(f"/v2/assessments/{key}/standardize")
        assert result.status_code == 200
        report = client.get(f"/v2/assessments/{key}/report").json()
        assert report["standardized_inputs"]["fields"]["cgpa"]["value"] == 8.2
        assert client.post("/v2/assessments/missing/standardize").status_code == 404
