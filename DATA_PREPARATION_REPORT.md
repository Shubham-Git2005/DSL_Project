# Prepared datasets and training handoff

Prepared on 1 November 2026. All four requested sources are downloaded under `prototype/data/datasets/raw/`. Original files are retained. Derived files are under `prototype/data/datasets/prepared/`; they are ignored by Git because they include third-party source material.

## What is ready

| Source | Downloaded records | Prepared output | Training status |
| --- | ---: | --- | --- |
| ResumeExtractBench | 30 | 26 PDF texts extracted; 4 need OCR | Structured extraction evaluation; original published test set retained. |
| Structured resumes | 4,817 | 4,659 usable profiles | Annotation-ready; no independent readiness labels. |
| Campus Recruitment CSV | 10,000 | 9,912 rows | Ready for a separate binary placement baseline using source labels. |
| Placement-readiness survey | 1,118 | 1,118 rows | Ready for a separate self-reported-readiness baseline. |

These datasets are not joined into fictitious student profiles. Their targets, populations, missing fields, and source provenance remain separate. No trained readiness model or fabricated expert labels were created.

## Prepared files

- [Full preparation manifest](prototype/data/datasets/prepared/manifest.json): source URLs, declared licences, pinned Hugging Face revisions, SHA-256 hashes of raw files, counts, splits, and validation results.
- [Extraction evaluation records](prototype/data/datasets/prepared/resume_extract_bench/extraction_evaluation.jsonl): source PDF text, linked publisher extraction ground truth, domain/origin, and OCR status. Contact details/known names receive best-effort redaction.
- [Resume annotation queue](prototype/data/datasets/prepared/resumes/annotation_queue.jsonl): API-valid evidence profiles, source row IDs, artifact hashes, leakage groups, and empty independent-readiness labels.
- [Campus training data](prototype/data/datasets/prepared/campus_baseline/train.jsonl), [validation](prototype/data/datasets/prepared/campus_baseline/validation.jsonl), [test](prototype/data/datasets/prepared/campus_baseline/test.jsonl), and [quarantine](prototype/data/datasets/prepared/campus_baseline/quarantine.jsonl).
- [Survey training data](prototype/data/datasets/prepared/survey/train.jsonl), [validation](prototype/data/datasets/prepared/survey/validation.jsonl), [test](prototype/data/datasets/prepared/survey/test.jsonl), and [observed categories](prototype/data/datasets/prepared/survey/observed_categories.json).
- [Synthetic test profiles and instructions](TEST_SAMPLES.md).

## Exact splits

| Dataset | Train | Validation | Test |
| --- | ---: | ---: | ---: |
| Unlabelled resume profiles | 3,325 | 655 | 679 |
| Campus binary baseline | 7,171 | 1,258 | 1,483 |
| Self-reported survey | 771 | 182 | 165 |

For resume profiles, these are reserved development/evaluation partitions of unlabelled source evidence, not a completed supervised dataset. Shared exact artifact hashes are placed in the same connected leakage group. The survey groups identical feature combinations; its answers remain categorical, including CGPA bands. Campus publisher splits are retained after removing cross-split duplicates and conflicting feature/label records.

## Cleaning and provenance findings

- ResumeExtractBench mini contains five records already in its test set; they were not added as independent examples.
- The structured-resume adapter excluded 101 profiles without usable supported artifact types and 57 duplicate normalized profiles. It produced 7,069 project artifacts, 3,165 explicitly identified internship artifacts, and only 6 usable certification artifacts. Regular employment was not relabelled as an internship.
- Structured resumes have 4,650 connected groups; the largest has three profiles. Source population is mixed real/synthetic without reliable per-record origin flags. Best-effort contact/name redaction is not certified anonymization.
- Campus data has 72 duplicate-feature records removed and 16 records quarantined in eight feature-identical groups with conflicting placement labels. The original soft-skills rating remains on its source scale; it was not invented as a communication score.
- Survey data contains no exact duplicate rows in this download. Its outcome is self-reported Yes/No readiness, not verified offers or expert judgement. The accompanying README leaves sampling, participant provenance, and consent details incomplete.
- Missing CGPA, coding scores, and communication measurements are left null in resume API profiles. No GitHub activity, LeetCode rating, or readiness scores are fabricated.
- All 4,659 generated resume profiles passed the API request schema; split-group leakage checks passed.

## Training the two available tabular baselines

These are separate research baselines. They cannot be installed as the seventeen-feature evidence readiness model. Their performance, if trained, will measure agreement with source labels rather than verified employability.

```powershell
python -m prototype.train_tabular --dataset campus --output prototype/evaluation/campus-run-001
python -m prototype.train_tabular --dataset survey --output prototype/evaluation/survey-run-001
```

The script fits logistic regression and random forest on the training partition, selects by validation macro F1, and evaluates the winner on the test partition once. It outputs `baseline.joblib` and `baseline-report.json`, with clearly separated target semantics. It has not been run on these real-source holdouts during preparation, preserving them for the intended training run.

## Preparing expert-labelled evidence training

1. Copy a manageable subset of `resumes/annotation_queue.jsonl` to a working annotation file. Keep source IDs, groups, and reserved splits intact.
2. Review whether each profile belongs to a supported role and is suitable for your target population. Leave unsupported or unsuitable profiles unlabelled; do not force them into a readiness class.
3. An independent reviewer sets `target_role`, `readiness_label`, `label_source: human_expert`, `reviewer_id`, and `review_notes`. Valid labels: `foundation_developing`, `developing_independence`, `entry_level_ready`. These are human fields, not Qwen predictions.
4. Reviewers assess original evidence and appropriate practical tasks before looking at model answers. Prefer two assessors for a representative subset and resolve disagreements.
5. Compile labelled development records using local Qwen. The compiler refuses invented/LLM labels and excludes records in the reserved test partition.

```powershell
python -m prototype.compile_labels --annotations path/to/reviewed-profiles.jsonl --output prototype/data/datasets/labelled-development.jsonl --provider lmstudio
python -m prototype.train --data prototype/data/datasets/labelled-development.jsonl --output prototype/models/evidence-run-001
```

At least 60 independently identified profiles and sufficient class/group coverage are required by the existing trainer; this is not a guarantee of representative real-world performance. Keep the public mixed-population development set separate from actual student validation. The readiness trainer creates its own grouped internal holdout from the compiled development pool; the prepared external test partition remains reserved.

## Reproduce and check

```powershell
python -m prototype.prepare_datasets
python -m pytest prototype/tests/test_data_preparation.py -q
python -m prototype.run_samples --sample all --evaluator offline
```

The preparation command is offline and reuses the downloaded raw sources. It does not execute dataset scripts or arbitrary repository code. To refresh upstream data, obtain the explicit files from the linked publishers, save them in a new raw snapshot, and regenerate/compare the manifest before replacing a dataset version.

## Source links and attribution

- [Careerflow ResumeExtractBench](https://huggingface.co/datasets/Careerflow/ResumeExtractBench) — publisher-declared CC BY 4.0.
- [uhfew/resumes](https://huggingface.co/datasets/uhfew/resumes) — publisher-declared MIT; mixed sources.
- [Campus Recruitment CSV](https://huggingface.co/datasets/surya5678/Campus_Recruitment_CSV) — publisher-declared CC0 1.0; outcome provenance not independently established.
- [Nihaal sharma, placement-readiness survey, version 1](https://data.mendeley.com/datasets/f52mmcsbsn/1) — DOI 10.17632/f52mmcsbsn.1, publisher-declared CC BY 4.0.

The raw cards/README, source PDFs, survey dictionary, cleaning log, article, and ZIP archive are retained for provenance. Source licences and publisher declarations do not establish participant consent or suitability for high-stakes decisions.

## Validation completed

The full prototype suite passed 48 tests, including eight dataset/sample/annotation/baseline checks. All seven samples completed offline API checks. Live Qwen reports are separate provisional assessments; an adversarial sample was rejected once and was explicitly rechecked, rather than counted as a pass. See TEST_SAMPLES.md for the behaviour and run commands.

The campus label-conflict audit inspected source labels across publisher partitions. These are audited public benchmark splits, not an untouched external cohort. Independent student validation is still needed.
