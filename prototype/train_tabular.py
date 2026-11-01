"""Train a separate public-data baseline, never the evidence readiness model.

python -m prototype.train_tabular --dataset campus --output prototype/evaluation/campus-baseline
"""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, f1_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .prepare_datasets import ROOT, read_jsonl


def train(dataset, output, root=ROOT):
    folder = root / "prepared" / ("campus_baseline" if dataset == "campus" else "survey")
    rows = {split: read_jsonl(folder / f"{split}.jsonl") for split in ["train", "validation", "test"]}
    if not all(rows.values()):
        raise ValueError("All three prepared splits must contain records.")
    groups = {split: {r["group_id"] for r in records} for split, records in rows.items()}
    if groups["train"] & groups["validation"] or groups["train"] & groups["test"] or groups["validation"] & groups["test"]:
        raise ValueError("Prepared splits share leakage groups.")
    frames = {split: pd.DataFrame([r["features"] for r in records]).replace({None: np.nan}) for split, records in rows.items()}
    labels = {split: np.array([r["label"] for r in records]) for split, records in rows.items()}
    numeric = list(frames["train"].select_dtypes(include=["number"]).columns)
    categorical = [name for name in frames["train"].columns if name not in numeric]
    preprocessing = ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median", keep_empty_features=True)), ("scale", StandardScaler())]), numeric),
        ("category", Pipeline([("impute", SimpleImputer(strategy="constant", fill_value="unknown", keep_empty_features=True)),
            ("encode", OneHotEncoder(handle_unknown="ignore"))]), categorical),
    ])
    candidates = [
        ("Logistic regression", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=42)),
        ("Random forest", RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=3, class_weight="balanced", random_state=42)),
    ]
    results, winner, best = [], None, -1
    for name, model in candidates:
        pipeline = Pipeline([("preprocessor", preprocessing), ("classifier", model)])
        pipeline.fit(frames["train"], labels["train"])
        score = float(f1_score(labels["validation"], pipeline.predict(frames["validation"]), average="macro"))
        results.append({"model": name, "validation_macro_f1": score})
        if score > best:
            winner, best, selected = pipeline, score, name
    # The chosen fitted model sees the test set only after validation selection.
    predictions = winner.predict(frames["test"])
    probabilities = winner.predict_proba(frames["test"])
    report = {"dataset": dataset, "purpose": "published_binary_placement_baseline" if dataset == "campus" else "self_reported_readiness_baseline",
        "selected_model": selected, "candidates": results, "rows": {s: len(r) for s, r in rows.items()},
        "numeric_features": numeric, "categorical_features": categorical,
        "holdout": {"accuracy": float(accuracy_score(labels["test"], predictions)),
            "balanced_accuracy": float(balanced_accuracy_score(labels["test"], predictions)),
            "macro_f1": float(f1_score(labels["test"], predictions, average="macro")),
            "log_loss": float(log_loss(labels["test"], probabilities, labels=winner.classes_)),
            "classification_report": classification_report(labels["test"], predictions, output_dict=True, zero_division=0)},
        "limitations": ["Predicts publisher/self-reported labels only; their real-world validity is not independently verified.",
            "Not the evidence readiness classifier. Cannot be installed using SKILLSBRIDGE_MODEL_DIR.",
            "Probabilities are uncalibrated. Do not repeatedly tune against this test split."]}
    output.mkdir(parents=True, exist_ok=True)
    if (output / "baseline.joblib").exists():
        raise ValueError("Choose a new output directory rather than replacing a baseline.")
    joblib.dump(winner, output / "baseline.joblib")
    (output / "baseline-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["campus", "survey"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(train(args.dataset, args.output), indent=2))
