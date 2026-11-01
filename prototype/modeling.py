"""Only load locally trained, version-compatible models. Never deserialize uploads."""
import json
from pathlib import Path

from .schemas import FEATURES, SCHEMA_VERSION


def model_status(directory: Path):
    metadata_path = directory / "metadata.json"
    if not metadata_path.exists() or not (directory / "model.joblib").exists():
        return {"available": False, "status": "awaiting_labels", "reason": "No expert-labelled dataset or trained evidence model is installed."}
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("schema_version") != SCHEMA_VERSION or metadata.get("features") != FEATURES:
            raise ValueError("Model feature schema does not match this application.")
        if metadata.get("label_source") != "human_expert":
            raise ValueError("Only models trained with declared human expert labels can be installed.")
        return {"available": True, "status": "experimental", **metadata}
    except (ValueError, OSError) as error:
        return {"available": False, "status": "incompatible", "reason": str(error)}


def predict_report(report, directory: Path):
    status = model_status(directory)
    if not status["available"]:
        return report
    expected = status.get("evaluator_signature")
    actual = f"{report['evaluator']}:{report['evaluator_model']}:{report['rubric_version']}"
    if expected != actual:
        report["readiness"]["reason"] = "Installed model was trained with a different evaluator or rubric. Prediction withheld."
        return report
    if not report["artifacts"]:
        report["readiness"]["reason"] = "Evidence is required before a model prediction can be made."
        return report
    import joblib
    import pandas as pd
    pipeline = joblib.load(directory / "model.joblib")
    frame = pd.DataFrame([{name: report["features"].get(name) for name in FEATURES}])
    probabilities = pipeline.predict_proba(frame)[0]
    classes = list(pipeline.classes_)
    report["readiness"] = {"status": "experimental", "label": str(classes[int(probabilities.argmax())]),
        "probabilities": {str(label): round(float(value), 4) for label, value in zip(classes, probabilities)},
        "reason": "Experimental probability of an expert readiness category; not a placement probability.",
        "model_name": status["selected_model"]}
    return report
