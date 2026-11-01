"""Grouped model comparison on expert-labelled JSONL; no synthetic accuracy claims.

python -m prototype.train --data labels.jsonl --output prototype/models
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, classification_report, f1_score, log_loss
from sklearn.model_selection import GridSearchCV, GroupShuffleSplit, StratifiedGroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .schemas import CATEGORICAL_FEATURES, FEATURES, LABELS, LEVELS, NUMERIC_FEATURES, SCHEMA_VERSION


def validate_records(records, *, allow_synthetic=False):
    if len(records) < 60:
        raise ValueError("At least 60 independent student-role records are required for this initial comparison; more may be needed for reliable estimates.")
    seen_students, hashes, signatures = {}, {}, set()
    for row in records:
        required = {"student_id", "group_id", "label", "label_source", "evaluator_signature", "features"}
        if not required.issubset(row):
            raise ValueError(f"Each row requires {sorted(required)}.")
        if row["label_source"] != "human_expert" and not (allow_synthetic and row["label_source"] == "synthetic_smoke"):
            raise ValueError("Readiness labels must come from human experts. Synthetic data is only allowed for explicit smoke tests.")
        if row["label"] not in LABELS:
            raise ValueError("Unknown readiness class.")
        if not row["student_id"] or not row["group_id"]:
            raise ValueError("Student and leakage-group IDs must be nonempty.")
        previous = seen_students.setdefault(row["student_id"], row["group_id"])
        if previous != row["group_id"]:
            raise ValueError("All records for one student must share the same group_id.")
        if set(row["features"]) != set(FEATURES):
            raise ValueError("Feature schema must match the assessment export exactly.")
        for name in NUMERIC_FEATURES:
            value = row["features"][name]
            if value is not None and (not isinstance(value, (int, float)) or not np.isfinite(value)):
                raise ValueError(f"Invalid numeric feature: {name}.")
            limit = 10 if name == "cgpa" else 12 if name == "evidence_count" else 100
            if value is not None and not 0 <= value <= limit:
                raise ValueError(f"Out-of-range feature: {name}.")
        for name in CATEGORICAL_FEATURES:
            allowed = {"junior_backend", "junior_frontend", "junior_data"} if name == "target_role" else set(LEVELS) if name.endswith("_level") else {"supported", "partial", "not_demonstrated", "unknown", "mixed"}
            if row["features"][name] not in allowed:
                raise ValueError(f"Invalid category: {name}.")
        signatures.add(row["evaluator_signature"])
        for digest in row.get("artifact_hashes", []):
            previous = hashes.setdefault(digest, row["group_id"])
            if previous != row["group_id"]:
                raise ValueError("Duplicate artifacts must share a leakage group across students.")
    if len(signatures) != 1:
        raise ValueError("Use a single frozen evaluator/rubric signature per dataset.")
    if len(seen_students) < 60:
        raise ValueError("At least 60 independent students are required, not repeated snapshots.")
    groups_per_class = {label: {r["group_id"] for r in records if r["label"] == label} for label in LABELS}
    if any(len(groups) < 8 for groups in groups_per_class.values()):
        raise ValueError("Each readiness class requires at least 8 distinct leakage groups.")
    return next(iter(signatures))


def preprocessing():
    return ColumnTransformer([
        ("numeric", Pipeline([("impute", SimpleImputer(strategy="median", keep_empty_features=True)),
                             ("scale", StandardScaler())]), NUMERIC_FEATURES),
        ("category", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
    ])


def candidate_models():
    return [
        ("Logistic regression", LogisticRegression(max_iter=1500, class_weight="balanced", random_state=42),
         {"classifier__C": [0.1, 1.0, 10.0]}),
        ("Random forest", RandomForestClassifier(n_estimators=160, class_weight="balanced", random_state=42, n_jobs=1),
         {"classifier__max_depth": [4, 8, None], "classifier__min_samples_leaf": [2, 5]}),
        ("Extra trees", ExtraTreesClassifier(n_estimators=160, class_weight="balanced", random_state=42, n_jobs=1),
         {"classifier__max_depth": [4, 8, None], "classifier__min_samples_leaf": [2, 5]}),
    ]


def train(records, output: Path, *, allow_synthetic=False):
    signature = validate_records(records, allow_synthetic=allow_synthetic)
    synthetic = any(r["label_source"] == "synthetic_smoke" for r in records)
    frame = pd.DataFrame([r["features"] for r in records], columns=FEATURES)
    for name in NUMERIC_FEATURES:
        frame[name] = pd.to_numeric(frame[name], errors="raise")
    labels = np.array([r["label"] for r in records])
    groups = np.array([r["group_id"] for r in records])
    # Fixed holdout allocation. Stop on inadequate class coverage; do not optimize the test split.
    train_idx, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42).split(frame, labels, groups))
    if set(labels[test_idx]) != set(LABELS) or set(labels[train_idx]) != set(LABELS):
        raise ValueError("The fixed group holdout lacks a class. Collect more representative data.")
    cv = list(StratifiedGroupKFold(n_splits=4, shuffle=True, random_state=42).split(frame.iloc[train_idx], labels[train_idx], groups[train_idx]))
    for fitting, validating in cv:
        if set(labels[train_idx][fitting]) != set(LABELS) or set(labels[train_idx][validating]) != set(LABELS):
            raise ValueError("A grouped CV fold lacks a class. Collect more representative groups.")
    candidates, winner, best_score = [], None, -1
    for name, estimator, parameters in candidate_models():
        search = GridSearchCV(Pipeline([("preprocessor", preprocessing()), ("classifier", estimator)]),
            parameters, scoring="f1_macro", cv=cv, n_jobs=1, error_score="raise", refit=True)
        search.fit(frame.iloc[train_idx], labels[train_idx])
        candidates.append({"model": name, "cv_macro_f1": float(search.best_score_),
            "cv_std": float(search.cv_results_["std_test_score"][search.best_index_]), "parameters": search.best_params_})
        if search.best_score_ > best_score:
            winner, best_score = search.best_estimator_, search.best_score_
            selected = name
    prediction = winner.predict(frame.iloc[test_idx])
    probabilities = winner.predict_proba(frame.iloc[test_idx])
    fingerprint = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
    report = {"schema_version": SCHEMA_VERSION, "features": FEATURES, "evaluator_signature": signature,
        "trained_at": datetime.now(timezone.utc).isoformat(), "dataset_sha256": fingerprint,
        "label_source": "synthetic_smoke" if synthetic else "human_expert",
        "selected_model": selected, "candidates": candidates, "rows": len(records),
        "train_rows": len(train_idx), "test_rows": len(test_idx),
        "groups_disjoint": not bool(set(groups[train_idx]) & set(groups[test_idx])),
        "holdout": {"accuracy": float(accuracy_score(labels[test_idx], prediction)),
            "balanced_accuracy": float(balanced_accuracy_score(labels[test_idx], prediction)),
            "macro_f1": float(f1_score(labels[test_idx], prediction, average="macro")),
            "log_loss": float(log_loss(labels[test_idx], probabilities, labels=winner.classes_)),
            "classification_report": classification_report(labels[test_idx], prediction, zero_division=0, output_dict=True)},
        "limitations": ["Synthetic smoke-test metrics are not evidence of real model performance." if synthetic else
            "Labels and provenance are supplied by the dataset author, not independently verified by this script.",
            "Probabilities are uncalibrated expert-category estimates, not placement probabilities.",
            "External-cohort validation and subgroup evaluation are still required.",
            "Do not repeatedly tune against this holdout; use a new cohort after feedback-driven revisions."]}
    output.mkdir(parents=True, exist_ok=True)
    if synthetic:
        (output / "smoke-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    else:
        # Export a complete bundle to a NEW directory; app installation is a separate deliberate action.
        if (output / "model.joblib").exists():
            raise ValueError("Output already contains a model. Use a new version directory.")
        joblib.dump(winner, output / "model.joblib")
        (output / "metadata.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-synthetic-smoke", action="store_true", help="Test pipeline mechanics; never exports an installable model.")
    args = parser.parse_args()
    records = [json.loads(line) for line in args.data.read_text(encoding="utf-8").splitlines() if line.strip()]
    report = train(records, args.output, allow_synthetic=args.allow_synthetic_smoke)
    print(json.dumps({"selected_model": report["selected_model"], "label_source": report["label_source"],
        "holdout": report["holdout"], "limitations": report["limitations"]}, indent=2))


if __name__ == "__main__":
    main()
