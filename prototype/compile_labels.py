"""Compile independently reviewed profiles into the exact readiness training schema.

Only explicitly human-labelled development records are evaluated. Test records remain held out.
"""
import argparse
import asyncio
import json
import os
from pathlib import Path

from .evaluator import evaluate
from .prepare_datasets import read_jsonl, write_jsonl
from .schemas import AssessmentRequest, LABELS


def eligible_records(rows):
    eligible, counts = [], {"unlabelled": 0, "reserved_test": 0}
    for row in rows:
        if row.get("split") == "test":
            counts["reserved_test"] += 1
            continue
        if row.get("readiness_label") is None:
            counts["unlabelled"] += 1
            continue
        if row["readiness_label"] not in LABELS or row.get("label_source") != "human_expert":
            raise ValueError("Readiness labels must be valid, explicitly independent human expert labels.")
        if not row.get("reviewer_id") or not row.get("review_notes"):
            raise ValueError("Labelled records need reviewer_id and review_notes.")
        if row.get("target_role") not in {"junior_backend", "junior_frontend", "junior_data"}:
            raise ValueError("A reviewer must explicitly select the target role.")
        eligible.append(row)
    return eligible, counts


async def compile_records(rows, output):
    selected, counts = eligible_records(rows)
    if not selected:
        raise ValueError("No eligible independent expert labels. Fill the annotation queue before compiling readiness training data.")
    compiled = []
    for row in selected:
        profile = AssessmentRequest.model_validate(row["profile"])
        profile.target_role = row["target_role"]
        profile.evaluator = "offline" if os.environ.get("ASSESSOR_PROVIDER") == "offline" else "llm"
        report = await evaluate(profile)
        signature = f"{report['evaluator']}:{report['evaluator_model']}:{report['rubric_version']}"
        compiled.append({"student_id": row["student_id"], "group_id": row["group_id"],
            "label": row["readiness_label"], "label_source": "human_expert", "reviewer_id": row["reviewer_id"],
            "review_notes": row["review_notes"], "source_population": row.get("source_population"),
            "artifact_hashes": row["artifact_hashes"], "evaluator_signature": signature, "features": report["features"]})
    write_jsonl(output, compiled)
    return {"compiled": len(compiled), "excluded": counts, "output": str(output),
        "warning": "Source population and independent label quality still require review; this does not establish real-world accuracy."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", choices=["lmstudio", "offline"], default="lmstudio")
    args = parser.parse_args()
    os.environ["ASSESSOR_PROVIDER"] = args.provider
    if args.provider == "lmstudio":
        os.environ.setdefault("ASSESSOR_MODEL", "qwen2.5-7b-instruct")
    print(json.dumps(asyncio.run(compile_records(read_jsonl(args.annotations), args.output)), indent=2))
