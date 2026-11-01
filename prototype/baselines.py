"""Separate, explicit inference contracts for public-data baseline models."""
import json
from pathlib import Path

import joblib
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

ROOT = Path(__file__).parent / "models"


class BaselineInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    features: dict[str, str | float | None]


def router(authorize):
    from fastapi import Depends
    routes = APIRouter(prefix="/v2/baselines", dependencies=[Depends(authorize)])

    def metadata(name):
        if name not in {"campus", "survey"}:
            raise HTTPException(404, "Unknown baseline")
        path = ROOT / f"{name}-final"
        if not (path / "baseline-report.json").exists():
            raise HTTPException(503, "Baseline not installed")
        return path, json.loads((path / "baseline-report.json").read_text(encoding="utf-8"))

    @routes.get("/{name}")
    def describe(name: str):
        return metadata(name)[1]

    @routes.post("/{name}/predict")
    def predict(name: str, body: BaselineInput):
        path, info = metadata(name)
        features = info["numeric_features"] + info["categorical_features"]
        if set(body.features) != set(features):
            raise HTTPException(422, {"message": "Supply the exact original feature schema; no evidence-score substitutions.", "required_features": features})
        try:
            frame = pd.DataFrame([body.features], columns=features)
            for column in info["numeric_features"]:
                frame[column] = pd.to_numeric(frame[column], errors="raise")
            model = joblib.load(path / "baseline.joblib")
            probability = model.predict_proba(frame)[0]
            return {"model": info["selected_model"], "target": info["purpose"],
                "label": str(model.classes_[probability.argmax()]),
                "probabilities": {str(k): float(v) for k, v in zip(model.classes_, probability)},
                "test_accuracy": info["holdout"]["accuracy"], "limitations": info["limitations"]}
        except (ValueError, TypeError) as error:
            raise HTTPException(422, "Features have incompatible types or values.") from error
    return routes
