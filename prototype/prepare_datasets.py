"""Prepare downloaded public sources without inventing readiness labels.

python -m prototype.prepare_datasets
Raw files live in prototype/data/datasets/raw. This command is offline.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "data" / "datasets"
EMPTY = {"", "unknown", "none", "null", "n/a", "na", "not specified", "not available"}
SOURCES = {
    "ResumeExtractBench": {"url": "https://huggingface.co/datasets/Careerflow/ResumeExtractBench", "license": "CC-BY-4.0", "purpose": "extraction_evaluation"},
    "resumes": {"url": "https://huggingface.co/datasets/uhfew/resumes", "license": "MIT (publisher declaration)", "purpose": "unlabelled_evidence_annotation", "population": "mixed real/synthetic; per-record origin not established"},
    "Campus_Recruitment_CSV": {"url": "https://huggingface.co/datasets/surya5678/Campus_Recruitment_CSV", "license": "CC0-1.0 (publisher declaration)", "purpose": "separate_binary_placement_baseline"},
    "placement_survey": {"url": "https://data.mendeley.com/datasets/f52mmcsbsn/1", "license": "CC-BY-4.0", "purpose": "separate_self_reported_survey", "version": "1", "download_url": "https://data.mendeley.com/public-api/zip/f52mmcsbsn/download/1"},
}


def digest(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def read_jsonl(path):
    with path.open(encoding="utf-8-sig") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def scrub(text, names=()):
    text = str(text)
    for name in names:
        if isinstance(name, str) and len(name.strip()) >= 4 and name.strip().lower() not in EMPTY:
            text = re.sub(re.escape(name.strip()), "[NAME]", text, flags=re.I)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", text)
    text = re.sub(r"https?://(?:www\.)?(?:linkedin\.com|github\.com)/[^\s\"<>]+", "[PROFILE_URL]", text, flags=re.I)
    # Mask conventional phone formats without interpreting normal dates as phone numbers.
    text = re.sub(r"(?<!\w)(?:\+\d{1,3}[ .-]?)?(?:\(?\d{3}\)?[ .-])\d{3}[ .-]\d{4}(?!\w)", "[PHONE]", text)
    text = re.sub(r"(?<!\d)\+?\d{10,13}(?!\d)", "[PHONE]", text)
    return text


def clean_tree(value, names=()):
    if isinstance(value, dict):
        excluded = {"personal_info", "basics", "email", "phone", "linkedin", "github", "location", "address"}
        result = {k: clean_tree(v, names) for k, v in value.items() if k.lower() not in excluded}
        return {k: v for k, v in result.items() if v not in (None, "", [], {})}
    if isinstance(value, list):
        return [v for item in value if (v := clean_tree(item, names)) not in (None, "", [], {})]
    if isinstance(value, str):
        return None if value.strip().lower() in EMPTY else scrub(value.strip(), names)
    return value


def entries(value):
    if isinstance(value, dict) and "items" in value:
        value = value["items"]
    if value in (None, "", []):
        return []
    return value if isinstance(value, list) else [value]


def assigned_split(group_id):
    bucket = int(hashlib.sha256(("skillsbridge-data-v1:" + group_id).encode()).hexdigest()[:8], 16) % 100
    return "train" if bucket < 70 else "validation" if bucket < 85 else "test"


def intern_experience(item):
    if not isinstance(item, dict):
        return False
    role = " ".join(str(item.get(k, "")) for k in ["title", "position", "role", "employment_type"])
    return bool(re.search(r"\bintern(?:ship)?\b", role, re.I))


def make_artifact(kind, title, item, names):
    cleaned = clean_tree(item, names)
    if not cleaned:
        return None
    content = json.dumps(cleaned, ensure_ascii=False, indent=2) if not isinstance(cleaned, str) else cleaned
    # Reject empty/template artifacts instead of padding them to satisfy API lengths.
    leaves = re.sub(r"[^a-zA-Z]", "", " ".join(str(v) for v in cleaned.values()) if isinstance(cleaned, dict) else content)
    if len(leaves) < 20 or len(content) > 12000:
        return None
    return {"kind": kind, "title": scrub(str(title or kind), names)[:160], "content": content, "source_url": None}


def prepare_resumes(raw, output):
    rows = read_jsonl(raw / "resumes" / "master_resumes.jsonl")
    pending, excluded = [], Counter()
    seen = set()
    for index, row in enumerate(rows):
        pii = row.get("personal_info") or {}
        names = [pii.get("name", "")]
        artifacts = []
        for project in entries(row.get("projects")):
            title = project.get("name", "Project evidence") if isinstance(project, dict) else "Project evidence"
            artifact = make_artifact("project", title, project, names)
            if artifact:
                artifacts.append(artifact)
        for experience in entries(row.get("internships")) + [v for v in entries(row.get("experience")) if intern_experience(v)]:
            title = experience.get("title", experience.get("position", "Internship evidence")) if isinstance(experience, dict) else "Internship evidence"
            artifact = make_artifact("internship", title, experience, names)
            if artifact:
                artifacts.append(artifact)
        for credential in entries(row.get("certifications")):
            title = credential.get("name", "Certification evidence") if isinstance(credential, dict) else "Certification evidence"
            artifact = make_artifact("certification", title, credential, names)
            if artifact:
                artifacts.append(artifact)
        artifacts = list({digest(item): item for item in artifacts}.values())[:12]
        # Bound the complete API payload; do not silently clip an individual claim.
        while sum(len(a["content"]) for a in artifacts) > 72000:
            artifacts.pop()
        if not artifacts:
            excluded["no_usable_supported_artifact_type"] += 1
            continue
        fingerprint = digest(artifacts)
        if fingerprint in seen:
            excluded["duplicate_normalized_profile"] += 1
            continue
        seen.add(fingerprint)
        record_id = f"resumes-{index:05d}"
        pending.append({"record_id": record_id, "student_id": record_id,
            "source_dataset": "uhfew/resumes", "source_row": index + 1,
            "source_population": "mixed_real_synthetic_unspecified", "readiness_label": None,
            "label_source": "unlabelled", "reviewer_id": None, "review_notes": None,
            "target_role": None, "artifact_hashes": [digest(a["content"].encode()) for a in artifacts],
            "profile": {"student_name": f"Dataset profile {index:05d}", "target_role": "junior_backend",
                "cgpa": None, "communication_score": None, "coding_score": None,
                "evaluator": "auto", "evidence": artifacts},
            "role_note": "Backend is a transport default; reviewer must choose a supported role before labelling."})
    # Connected components prevent identical artifacts crossing groups, including repeated certifications.
    parents = list(range(len(pending)))
    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index
    owners = {}
    for index, row in enumerate(pending):
        for artifact_hash in row["artifact_hashes"]:
            if artifact_hash in owners:
                parents[find(index)] = find(owners[artifact_hash])
            else:
                owners[artifact_hash] = index
    members = defaultdict(list)
    for index, row in enumerate(pending):
        members[find(index)].append(row["record_id"])
    for index, row in enumerate(pending):
        row["group_id"] = "resume-component-" + digest(sorted(members[find(index)]))[:16]
        row["split"] = assigned_split(row["group_id"])
    write_jsonl(output / "resumes" / "annotation_queue.jsonl", pending)
    for split in ["train", "validation", "test"]:
        write_jsonl(output / "resumes" / f"{split}.jsonl", [r for r in pending if r["split"] == split])
    # Compact local request examples, not automatically sent to any evaluator.
    for index, row in enumerate(pending[:5]):
        path = output / "resumes" / "api_samples" / f"profile_{index+1}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(row["profile"], indent=2, ensure_ascii=False), encoding="utf-8")
    return {"source_rows": len(rows), "prepared_unlabelled_profiles": len(pending), "excluded": dict(excluded),
        "splits": dict(Counter(r["split"] for r in pending)), "connected_groups": len(members),
        "largest_group": max(map(len, members.values()), default=0),
        "artifact_types": dict(Counter(a["kind"] for r in pending for a in r["profile"]["evidence"])),
        "warning": "No expert readiness labels or confirmed per-record real/synthetic origins. Redaction is best-effort, not certified anonymization."}


def prepare_benchmark(raw, output):
    from pypdf import PdfReader
    rows = read_jsonl(raw / "ResumeExtractBench" / "test.jsonl")
    prepared = []
    for index, row in enumerate(rows):
        source = raw / "ResumeExtractBench" / row["files"]["pdf"]
        error = None
        try:
            reader = PdfReader(source)
            text = "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as exc:
            text, error = "", type(exc).__name__
        basics = row["ground_truth"].get("basics", {})
        names = [" ".join(str(basics.get(k, "")) for k in ["fname", "lname"]).strip(), basics.get("name", "")]
        text = scrub(text, names)
        expected = {k: clean_tree(row["ground_truth"].get(k), names) for k in ["experience", "education", "projects", "certifications", "skills"]}
        prepared.append({"record_id": f"extractbench-{index:03d}", "source_resume_id": row["resume_id"],
            "source_type": row.get("source"), "domain": row.get("domain"), "split": "publisher_test",
            "pdf_path": str(source.relative_to(raw.parent)), "pdf_sha256": digest(source.read_bytes()),
            "source_text": text, "text_status": "extracted_needs_review" if len(text.strip()) >= 50 else "needs_ocr",
            "extraction_error": error, "expected_fields": expected, "label_type": "publisher_structured_extraction_ground_truth",
            "readiness_label": None})
    write_jsonl(output / "resume_extract_bench" / "extraction_evaluation.jsonl", prepared)
    mini_ids = {r["resume_id"] for r in read_jsonl(raw / "ResumeExtractBench" / "mini.jsonl")}
    return {"source_rows": len(rows), "prepared_records": len(prepared), "text_status": dict(Counter(r["text_status"] for r in prepared)),
        "mini_overlap_with_test": sum(r["resume_id"] in mini_ids for r in rows),
        "origins": dict(Counter(r.get("source") for r in rows)),
        "warning": "Published test set retained for extraction evaluation; mini is not added as independent training data. OCR/reading-order errors and source domain mismatch need review."}


CAMPUS_NUMERIC = {"CGPA": "cgpa", "Internships": "internship_count", "Projects": "project_count",
    "Workshops/Certifications": "workshop_certification_count", "AptitudeTestScore": "aptitude_test_score",
    "SoftSkillsRating": "soft_skills_rating_original", "SSC_Marks": "ssc_marks", "HSC_Marks": "hsc_marks"}
CAMPUS_CATEGORICAL = {"ExtracurricularActivities": "extracurricular_activities", "PlacementTraining": "placement_training"}


def prepare_campus(raw, output):
    records, rejected = [], []
    for split in ["train", "validation", "test"]:
        with (raw / "Campus_Recruitment_CSV" / "raw_datasets" / f"{split}.csv").open(encoding="utf-8-sig", newline="") as stream:
            for index, row in enumerate(csv.DictReader(stream)):
                features = {}
                try:
                    for source, target in CAMPUS_NUMERIC.items():
                        value = row[source].strip()
                        features[target] = float(value) if value else None
                        maximum = 10 if target == "cgpa" else 5 if target == "soft_skills_rating_original" else 100 if target.endswith(("score", "marks")) else None
                        if features[target] is not None and (not math.isfinite(features[target]) or features[target] < 0 or (maximum is not None and features[target] > maximum)):
                            raise ValueError("Out-of-range numeric value")
                    for source, target in CAMPUS_CATEGORICAL.items():
                        features[target] = row[source].strip() or None
                        if features[target] not in {None, "Yes", "No"}:
                            raise ValueError("Unknown Yes/No category")
                    if row["PlacementStatus"] not in {"Placed", "NotPlaced"}:
                        raise ValueError("Unknown placement label")
                except (ValueError, KeyError):
                    rejected.append({"source_split": split, "source_row": index+1, "reason": "invalid_schema_or_value"})
                    continue
                records.append({"record_id": f"campus-{split}-{index:05d}", "source_split": split,
                    "source_row": index+1, "features": features, "label": row["PlacementStatus"],
                    "label_source": "publisher_placement_status_unverified", "group_id": "campus-"+digest(features)[:20]})
    labels_by_group = defaultdict(set)
    for row in records:
        labels_by_group[row["group_id"]].add(row["label"])
    conflicting = {group for group, labels in labels_by_group.items() if len(labels) > 1}
    kept, seen = [], set()
    for row in records:
        if row["group_id"] in conflicting:
            rejected.append({"record_id": row["record_id"], "reason": "identical_features_conflicting_labels"})
        elif row["group_id"] in seen:
            rejected.append({"record_id": row["record_id"], "reason": "duplicate_features_removed_keep_earliest_publisher_split"})
        else:
            seen.add(row["group_id"])
            kept.append(row)
    for split in ["train", "validation", "test"]:
        write_jsonl(output / "campus_baseline" / f"{split}.jsonl", [r for r in kept if r["source_split"] == split])
    write_jsonl(output / "campus_baseline" / "quarantine.jsonl", rejected)
    return {"source_rows": len(records), "prepared_rows": len(kept), "rejections": dict(Counter(r["reason"] for r in rejected)),
        "conflicting_feature_groups": len(conflicting), "splits": dict(Counter(r["source_split"] for r in kept)),
        "labels": dict(Counter(r["label"] for r in kept)),
        "warning": "Separate binary baseline only. Soft-skills rating retains its original scale; counts are not semantic levels. Source placement authenticity not established."}


def prepare_survey(raw, output):
    paths = list((raw / "placement_survey").rglob("Placement_Readiness_Analysis_Ready.csv"))
    if len(paths) != 1:
        raise ValueError("Exactly one analysis-ready survey CSV is required.")
    with paths[0].open(encoding="utf-8-sig", newline="") as stream:
        source_rows = list(csv.DictReader(stream))
    prepared, seen, duplicates = [], set(), 0
    categories = defaultdict(Counter)
    for index, row in enumerate(source_rows):
        clean = {key.strip(): value.strip() or None for key, value in row.items()}
        for key, value in clean.items():
            categories[key][str(value)] += 1
        fingerprint = digest(clean)
        if fingerprint in seen:
            duplicates += 1
            continue
        seen.add(fingerprint)
        label = clean.pop("self_reported_placement_ready")
        group = "survey-" + digest(clean)[:20]
        prepared.append({"record_id": f"survey-{index:05d}", "source_row": index+1,
            "features": clean, "label": label, "label_source": "self_reported_readiness",
            "group_id": group, "split": assigned_split(group), "source_population": "publisher_survey_provenance_incomplete"})
    for split in ["train", "validation", "test"]:
        write_jsonl(output / "survey" / f"{split}.jsonl", [r for r in prepared if r["split"] == split])
    (output / "survey" / "observed_categories.json").write_text(json.dumps(categories, indent=2), encoding="utf-8")
    return {"source_rows": len(source_rows), "prepared_rows": len(prepared), "exact_duplicate_rows_removed": duplicates,
        "splits": dict(Counter(r["split"] for r in prepared)), "labels": dict(Counter(r["label"] for r in prepared)),
        "warning": "Self-reported outcome only. CGPA bands and skill categories remain unchanged. Publisher README leaves sampling/consent/origin details incomplete."}


def validate_outputs(output):
    from .schemas import AssessmentRequest
    rows = read_jsonl(output / "resumes" / "annotation_queue.jsonl")
    hash_groups = {}
    for row in rows:
        AssessmentRequest.model_validate(row["profile"])
        assert row["readiness_label"] is None and row["label_source"] == "unlabelled"
        for value in row["artifact_hashes"]:
            previous = hash_groups.setdefault(value, row["group_id"])
            assert previous == row["group_id"], "Duplicate artifact crosses a leakage group"
    for name in ["resumes", "campus_baseline", "survey"]:
        split_groups = {}
        for split in ["train", "validation", "test"]:
            for row in read_jsonl(output / name / f"{split}.jsonl"):
                previous = split_groups.setdefault(row["group_id"], split)
                assert previous == split, f"Leakage between {name} splits"
    return {"api_profiles_validated": len(rows), "group_leakage_checks": "passed", "invented_readiness_labels": 0}


def prepare(root=ROOT):
    raw, output = root / "raw", root / "prepared"
    output.mkdir(parents=True, exist_ok=True)
    report = {"prepared_at": datetime.now(timezone.utc).isoformat(), "preparation_version": "public-sources-v1",
        "datasets": {}, "sources": SOURCES}
    for name, function in [("ResumeExtractBench", prepare_benchmark), ("resumes", prepare_resumes),
                           ("Campus_Recruitment_CSV", prepare_campus), ("placement_survey", prepare_survey)]:
        report["datasets"][name] = function(raw, output)
    report["validation"] = validate_outputs(output)
    report["raw_files"] = [{"path": str(path.relative_to(root)), "bytes": path.stat().st_size, "sha256": digest(path.read_bytes())}
        for path in sorted(raw.rglob("*")) if path.is_file()]
    for name in ["ResumeExtractBench", "resumes", "Campus_Recruitment_CSV"]:
        info = json.loads((raw / name / "source-info.json").read_text(encoding="utf-8"))
        report["sources"][name]["revision"] = info["revision"]
    (output / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"datasets": report["datasets"], "validation": report["validation"]}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    prepare(args.root)
