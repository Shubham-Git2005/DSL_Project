"""Measure artifact assessment against independent expert labels, not self-evaluation."""
import argparse
import asyncio
import json
from pathlib import Path

from sklearn.metrics import classification_report, f1_score

from .evaluator import DIMENSIONS, llm_assess, offline_assess
from .schemas import Evidence, LEVELS, RUBRIC_VERSION


async def benchmark(records, mode="offline"):
    if not records:
        raise ValueError("No labelled artifacts were supplied.")
    actual, predicted, levels_actual, levels_predicted, failures, details = [], [], [], [], [], []
    for index, record in enumerate(records):
        if record.get("label_source") != "human_expert":
            raise ValueError("Benchmark labels must be independent human expert judgements.")
        item = Evidence.model_validate(record["evidence"])
        expected = record["expected_categories"]
        if set(expected) != set(DIMENSIONS[item.kind]):
            raise ValueError("Expected categories must cover every rubric dimension exactly once.")
        if any(v not in {"supported", "partial", "not_demonstrated", "unknown"} for v in expected.values()):
            raise ValueError("Invalid expert category.")
        if record["expected_level"] not in LEVELS:
            raise ValueError("Invalid expert level.")
        try:
            result = await llm_assess(item, record.get("target_role", "junior_backend")) if mode == "llm" else offline_assess(item)
        except Exception as error:
            failures.append({"index": index, "error_type": type(error).__name__})
            continue
        mismatches=[]
        for finding in result.findings:
            actual.append(expected[finding.dimension])
            predicted.append(finding.category)
            if expected[finding.dimension] != finding.category:
                mismatches.append({"dimension": finding.dimension,"expected":expected[finding.dimension],"predicted":finding.category})
        levels_actual.append(record["expected_level"])
        levels_predicted.append(result.level)
        details.append({"index":index,"title":item.title,"mismatches":mismatches,
            "expected_level":record["expected_level"],"predicted_level":result.level})
    categories=["supported","partial","not_demonstrated","unknown"]
    return {"purpose":"Agreement with supplied independent expert labels, not placement accuracy.",
        "mode":mode,"rubric_version":RUBRIC_VERSION,"artifact_count":len(records),
        "completed":len(details),"failed":len(failures),"failures":failures,
        "coverage":len(details)/len(records),
        "category_macro_f1":float(f1_score(actual,predicted,labels=categories,average="macro",zero_division=0)) if actual else None,
        "category_report":classification_report(actual,predicted,labels=categories,zero_division=0,output_dict=True) if actual else None,
        "level_macro_f1":float(f1_score(levels_actual,levels_predicted,labels=LEVELS,average="macro",zero_division=0)) if levels_actual else None,
        "error_analysis":details,
        "limitations":["Agreement metrics exclude failed items; always inspect coverage and failure counts.",
            "Small samples and missing classes make macro metrics unstable.",
            "Expert label provenance is declared by the dataset author, not verified by this tool.",
            "Offline mode is a text scan, not a semantic assessor."]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--mode",choices=["offline","llm"],default="offline")
    args=parser.parse_args()
    rows=[json.loads(line) for line in args.data.read_text(encoding="utf-8").splitlines() if line.strip()]
    report=asyncio.run(benchmark(rows,args.mode))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in {"category_report","error_analysis"}},indent=2))


if __name__=="__main__":
    main()
