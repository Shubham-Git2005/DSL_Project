import csv
import json

import pytest

from prototype.compile_labels import eligible_records
from prototype.prepare_datasets import (CAMPUS_CATEGORICAL, CAMPUS_NUMERIC, assigned_split,
    intern_experience, prepare_campus, read_jsonl, scrub)
from prototype.schemas import AssessmentRequest


def test_samples_are_api_valid_and_clearly_synthetic():
    from pathlib import Path
    paths = list((Path(__file__).parents[1] / "samples").glob("*.json"))
    assert len(paths) == 7
    for path in paths:
        sample = AssessmentRequest.model_validate_json(path.read_text(encoding="utf-8"))
        assert sample.dataset_origin == "synthetic_example"


def test_redaction_removes_known_identity_and_contact_fields():
    text = scrub("Mira Patil: mira@example.com, +91 9876543210. https://linkedin.com/in/mira", ["Mira Patil"])
    assert "Mira Patil" not in text
    assert "mira@example.com" not in text
    assert "9876543210" not in text
    assert "linkedin.com" not in text


def test_jobs_are_not_invented_as_internships():
    assert intern_experience({"title": "Backend intern"})
    assert intern_experience({"employment_type": "internship"})
    assert not intern_experience({"title": "Senior software engineer", "responsibilities": ["Built an internal service"]})


def test_campus_duplicates_and_conflicting_labels_are_quarantined(tmp_path):
    folder = tmp_path / "raw" / "Campus_Recruitment_CSV" / "raw_datasets"
    folder.mkdir(parents=True)
    fields = [*CAMPUS_NUMERIC, *CAMPUS_CATEGORICAL, "PlacementStatus"]
    def row(cgpa, label):
        return {"CGPA": cgpa, "Internships": 1, "Projects": 2, "Workshops/Certifications": 1,
            "AptitudeTestScore": 70, "SoftSkillsRating": 4, "SSC_Marks": 80, "HSC_Marks": 75,
            "ExtracurricularActivities": "Yes", "PlacementTraining": "No", "PlacementStatus": label}
    sources = {"train": [row(8, "Placed"), row(7, "Placed")],
        "validation": [row(8, "Placed"), row(7, "NotPlaced")], "test": [row(9, "Placed")]}
    for split, rows in sources.items():
        with (folder / f"{split}.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    report = prepare_campus(tmp_path / "raw", tmp_path / "prepared")
    assert report["prepared_rows"] == 2
    assert report["conflicting_feature_groups"] == 1
    assert len(read_jsonl(tmp_path / "prepared" / "campus_baseline" / "quarantine.jsonl")) == 3


def test_unlabelled_and_test_profiles_cannot_become_readiness_training():
    selected, counts = eligible_records([{"split": "train", "readiness_label": None},
        {"split": "test", "readiness_label": "entry_level_ready"}])
    assert selected == []
    assert counts == {"unlabelled": 1, "reserved_test": 1}
    with pytest.raises(ValueError, match="independent"):
        eligible_records([{"split": "train", "readiness_label": "entry_level_ready", "label_source": "llm"}])


def test_reviewer_role_and_notes_required():
    with pytest.raises(ValueError, match="reviewer_id"):
        eligible_records([{"split": "train", "readiness_label": "entry_level_ready", "label_source": "human_expert"}])


def test_split_is_stable_for_repeated_groups():
    assert assigned_split("same-student") == assigned_split("same-student")


def test_separate_tabular_baseline_can_train_without_becoming_readiness_model(tmp_path):
    from prototype.prepare_datasets import write_jsonl
    from prototype.train_tabular import train
    folder = tmp_path / "datasets" / "prepared" / "campus_baseline"
    for split in ["train", "validation", "test"]:
        rows = [{"group_id": f"{split}-{i}", "features": {"cgpa": 6.0 + i/10,
            "internship_count": i % 2, "placement_training": "Yes" if i % 2 else "No"},
            "label": "Placed" if i % 2 else "NotPlaced"} for i in range(20)]
        write_jsonl(folder / f"{split}.jsonl", rows)
    report = train("campus", tmp_path / "output", tmp_path / "datasets")
    assert report["purpose"] == "published_binary_placement_baseline"
    assert len(report["candidates"]) == 2
    assert (tmp_path / "output" / "baseline.joblib").exists()
    assert not (tmp_path / "output" / "model.joblib").exists()
    assert not (tmp_path / "output" / "metadata.json").exists()
