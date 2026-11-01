import copy

import numpy as np
import pandas as pd
import pytest

from prototype.schemas import CATEGORICAL_FEATURES, FEATURES, LABELS
from prototype.train import train, validate_records


def synthetic_records():
    """Intentionally synthetic, noisy fixtures for pipeline mechanics only."""
    rng=np.random.default_rng(19)
    records=[]
    for i in range(90):
        category=["unknown","partial","supported"][i%3]
        features={"cgpa":float(rng.uniform(5,10)),"coding_score":float(rng.uniform(20,95)),
            "communication_score":float(rng.uniform(30,90)),"evidence_count":int(rng.integers(1,7)),
            **{name:(["unknown","applied","independent"][i%3] if name.endswith("_level") else category)
               for name in CATEGORICAL_FEATURES if name!="target_role"},"target_role":"junior_backend"}
        if i%7==0:features["testing"]="unknown"
        records.append({"student_id":f"student-{i}","group_id":f"group-{i}","label":LABELS[i%3],
            "label_source":"synthetic_smoke","evaluator_signature":"offline:offline-text-scan-v1:role-rubric-1.1",
            "features":features,"artifact_hashes":[f"fixture-{i}"]})
    return records


def test_synthetic_data_cannot_be_promoted(tmp_path):
    rows=synthetic_records()
    with pytest.raises(ValueError,match="human experts"):
        train(rows,tmp_path)
    assert not (tmp_path/"model.joblib").exists()


def test_grouped_model_comparison_smoke(tmp_path):
    report=train(synthetic_records(),tmp_path,allow_synthetic=True)
    assert len(report["candidates"])==3
    assert report["groups_disjoint"]
    assert report["label_source"]=="synthetic_smoke"
    assert 0 <= report["holdout"]["macro_f1"] <= 1
    assert (tmp_path/"smoke-report.json").exists()
    assert not (tmp_path/"model.joblib").exists()
    assert not (tmp_path/"metadata.json").exists()


def test_evaluator_signature_must_be_frozen():
    rows=synthetic_records()
    rows[0]["evaluator_signature"]="different"
    with pytest.raises(ValueError,match="single frozen"):
        validate_records(rows,allow_synthetic=True)


def test_student_leakage_is_rejected():
    rows=synthetic_records()
    rows[1]["student_id"]=rows[0]["student_id"]
    with pytest.raises(ValueError,match="same group_id"):
        validate_records(rows,allow_synthetic=True)


def test_duplicate_artifacts_cannot_cross_groups():
    rows=synthetic_records()
    rows[1]["artifact_hashes"]=rows[0]["artifact_hashes"]
    with pytest.raises(ValueError,match="Duplicate artifacts"):
        validate_records(rows,allow_synthetic=True)


def test_invalid_training_features_rejected():
    rows=synthetic_records()
    rows[0]["features"]["cgpa"]=float("nan")
    with pytest.raises(ValueError,match="Invalid numeric"):
        validate_records(rows,allow_synthetic=True)


def test_models_handle_missing_scores_and_unseen_categories():
    from prototype.train import candidate_models,preprocessing
    from sklearn.pipeline import Pipeline
    rows=synthetic_records()
    frame=pd.DataFrame([r["features"] for r in rows],columns=FEATURES)
    frame.loc[0,"cgpa"]=np.nan
    for name,estimator,_ in candidate_models():
        pipe=Pipeline([("preprocessor",preprocessing()),("classifier",estimator)])
        pipe.fit(frame,[r["label"] for r in rows])
        sample=frame.iloc[:1].copy()
        sample["target_role"]="junior_frontend"
        probability=pipe.predict_proba(sample)
        assert probability.shape==(1,3),name
        assert np.allclose(probability.sum(axis=1),1),name


def test_incompatible_model_is_not_loaded(tmp_path):
    import json
    from prototype.modeling import model_status
    (tmp_path/"metadata.json").write_text(json.dumps({"schema_version":"legacy-six-feature"}))
    (tmp_path/"model.joblib").write_bytes(b"never deserialize")
    assert model_status(tmp_path)["available"] is False
