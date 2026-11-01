"""Submit synthetic test profiles to the running API and check structural invariants."""
import argparse
import json
import os
import time
from pathlib import Path

import httpx


def run(path, base, evaluator, output):
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["evaluator"] = evaluator
    headers = {"X-API-Key": os.environ["SKILLSBRIDGE_API_KEY"]} if os.getenv("SKILLSBRIDGE_API_KEY") else {}
    with httpx.Client(base_url=base, timeout=15, headers=headers, trust_env=False) as client:
        created = client.post("/v2/assessments", json=payload)
        created.raise_for_status()
        key = created.json()["id"]
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            response = client.get(f"/v2/assessments/{key}")
            response.raise_for_status()
            job = response.json()
            if job["status"] == "failed":
                raise RuntimeError(job["error"])
            if job["status"] == "completed":
                break
            time.sleep(1)
        else:
            raise TimeoutError("Assessment is still running; retrieve it from history.")
        response = client.get(f"/v2/assessments/{key}/report")
        response.raise_for_status()
        report = response.json()
    assert report["dataset_origin"] == "synthetic_example"
    assert len(report["artifacts"]) == len(payload["evidence"])
    for result, source in zip(report["artifacts"], payload["evidence"]):
        assert not result["independently_verified"]
        assert result["level_quote"] in source["content"]
        assert all(finding["quote"] in source["content"] for finding in result["findings"])
    output.mkdir(parents=True, exist_ok=True)
    (output / path.name).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"sample": path.name, "id": key, "evaluator": report["evaluator"],
        "levels": [a["level"] for a in report["artifacts"]], "structural_checks": "passed"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", default="01_guided_project")
    parser.add_argument("--evaluator", choices=["auto", "offline", "llm"], default="auto")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    args = parser.parse_args()
    folder = Path(__file__).parent / "samples"
    paths = sorted(folder.glob("*.json")) if args.sample == "all" else [folder / f"{args.sample.removesuffix('.json')}.json"]
    failed = 0
    for path in paths:
        try:
            result = run(path, args.base_url, args.evaluator, Path(__file__).parent / "data" / "sample_results")
            result["status"] = "completed"
        except Exception as error:
            failed += 1
            result = {"sample": path.name, "status": "failed", "error_type": type(error).__name__, "reason": str(error)}
        print(json.dumps(result), flush=True)
    if failed:
        raise SystemExit(1)
