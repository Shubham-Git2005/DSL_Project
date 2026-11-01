# SkillsBridge evidence prototype

A separate, working prototype of the proposed evidence-assessment architecture. The existing `main.py`, model artifacts, and Colab notebook are not replaced.

## Run locally

From the repository root, with Python 3.12 or 3.13:

```powershell
python -m venv .venv-prototype
.\.venv-prototype\Scripts\python.exe -m pip install -r prototype/requirements.txt
.\.venv-prototype\Scripts\python.exe -m uvicorn prototype.app:app --host 127.0.0.1 --port 8001
```

Open http://127.0.0.1:8001. API docs: http://127.0.0.1:8001/docs. The app uses one worker; queued/in-progress jobs become failed after a restart so they never remain silently pending. Background jobs are in-process, not a durable distributed queue.

The UI is served by FastAPI and has no Node build step or external runtime assets. It includes profile and evidence editing, text/source-file import, GitHub README import, background assessment status, quote-backed reports, JSON export, history, deletion, review requests, model status, and integration examples. The bundled example is synthetic and remains marked as such in reports.

## What works without credentials

`offline` is an intentionally limited text scan. It locates related wording and returns `partial` or `unknown`; it never verifies claims, assesses quality, or predicts readiness. It can find a keyword in a negated sentence, so the UI explicitly asks users to read the quote. This is not a semantic-model accuracy claim.

No replacement readiness model is bundled. The UI/API return `readiness.status = unavailable` until a compatible trained model is installed. The old synthetic-data model is not reused with incompatible evidence features.

## Enable the semantic evaluator

### Local Qwen through LM Studio

With LM Studio already serving `qwen2.5-7b-instruct` on port 1234, stop an existing SkillsBridge server on port 8001, then run:

```powershell
python -m prototype.run_local
```

This uses `ASSESSOR_PROVIDER=lmstudio`, defaults `ASSESSOR_MODEL` to `qwen2.5-7b-instruct`, and defaults `LMSTUDIO_BASE_URL` to `http://127.0.0.1:1234/v1`. If local server authentication is enabled, set `LMSTUDIO_API_KEY`. The model remains a separate LM Studio process. Local source quotes are grammar-constrained to supplied excerpts and rubric dimensions are keyed before conversion to the public findings list. The endpoint is restricted to loopback addresses. Reports identify the model as `lmstudio/qwen2.5-7b-instruct`; use that full identity in training signatures.

See [dataset sources and local integration](../DATASETS_AND_LOCAL_MODEL.md) for verified dataset links and limits. The five-artifact synthetic example completed a live local evaluation; this does not establish predictive accuracy.

### Remote Anthropic evaluator

Set environment variables in the shell before starting the server. `.env.example` documents names; it is not automatically loaded.

```powershell
$env:ANTHROPIC_API_KEY = "your-provider-key"
$env:ASSESSOR_MODEL = "a-supported-model-id-from-your-provider-account"
python -m uvicorn prototype.app:app --host 127.0.0.1 --port 8001
```

Use `ASSESSOR_PROVIDER=anthropic` (the default) with a provider model supporting structured JSON output. Model IDs and account access change; choose from your account rather than copying an unverified name. The remote evaluator uses Anthropic's Messages endpoint with a constrained JSON schema. Full Pydantic validation and exact-quote checks run locally afterward. Provider failure produces a failed job rather than silently switching to a weaker evaluator. `auto` chooses offline only when semantic configuration is absent. A live Anthropic call requires your credentials and has not been established by offline tests.

Server-side provider credentials never enter browser code. Submitted evidence is sent to the configured provider when semantic mode runs; use appropriately consented evidence and redact confidential material before submission. Keep original provider secrets and private repositories out of pasted text.

Rubric/prompt changes require bumping `RUBRIC_VERSION` and regenerating features for training. Reports record evaluator, model, rubric, feature values, evidence hashes, and verification limitations. Provider generation does not independently verify internship attendance, credential authenticity, code authorship, passing tests, or production usage.

## GitHub import scope

The prototype calls the official GitHub README endpoint on a fixed upstream hostname. It does not crawl arbitrary links. Set `GITHUB_TOKEN` on the server for authenticated access where appropriate. Only the README is imported, not the entire repository. The imported editable text is treated as student-supplied evidence; code quality, tests, ownership, and deployment remain unverified. Network timeouts and rate-limit errors are surfaced.

LeetCode scraping is not implemented. Paste permitted activity records or direct assessment evidence. Certificates are not verified by uploading a title or URL. Text import supports source files and plain text, not PDF/OCR or arbitrary binary files.

## API integration

```text
GET    /health
GET    /v2/capabilities
GET    /v2/example
POST   /v2/import/github
POST   /v2/assessments                 -> 202 {id,status,status_url}
GET    /v2/assessments                 -> bounded recent history
GET    /v2/assessments/{id}            -> queued / processing / completed / failed
GET    /v2/assessments/{id}/report     -> 409 until completed
POST   /v2/assessments/{id}/reviews    -> saves a note, sends no notification
DELETE /v2/assessments/{id}            -> deletes the database record
```

Example request:

```json
{
  "student_name": "Mira Patil",
  "target_role": "junior_backend",
  "cgpa": 8.1,
  "communication_score": null,
  "coding_score": null,
  "evaluator": "auto",
  "evidence": [
    {
      "kind": "project",
      "title": "Laboratory reservations",
      "content": "I implemented a reservation API with validation. Integration tests cover concurrent booking conflicts.",
      "source_url": null
    }
  ]
}
```

Allowed kinds: `project`, `internship`, `certification`, `coding`, `communication`. Roles: `junior_backend`, `junior_frontend`, `junior_data`. These role rubrics are prototype definitions, not validated occupational standards. Scores are optional; CGPA is 0–10, assessment scores 0–100. Per item: 2–160-character title, 20–24,000-character content, up to 12 items and 72,000 total evidence characters. Extra fields are rejected, including student-supplied `verified` flags.

For remote integration, set:

```powershell
$env:SKILLSBRIDGE_API_KEY = "a-long-random-workspace-key"
$env:CORS_ORIGINS = "https://your-project.example"
```

Send `X-API-Key` on every `/v2` request. The browser access dialog holds this key in memory for the current page only. This is a shared-workspace key, not user identity or per-student authorization. Do not expose a multi-student deployment until authentication, ownership checks, rate limits, TLS, a durable worker, and backups are added. CORS does not replace authorization. Binding to localhost is the default launch command.

SQLite records are under `prototype/data/`, ignored by Git. Configure `SKILLSBRIDGE_DATA_DIR` to change location. Deleting an assessment removes its stored row; this is not a forensic erasure guarantee for filesystem pages, backups, or provider retention.

## Training data contract

Export reports and have independent experts label readiness. Do not use LLM-generated readiness as ground truth. One JSON object per line:

```json
{
  "student_id": "anon-student-001",
  "group_id": "leakage-component-001",
  "label": "developing_independence",
  "label_source": "human_expert",
  "evaluator_signature": "offline:offline-text-scan-v1:role-rubric-1.1",
  "artifact_hashes": ["sha256-from-report"],
  "features": {
    "cgpa": 8.1,
    "communication_score": null,
    "coding_score": null,
    "evidence_count": 1,
    "target_role": "junior_backend",
    "implementation": "partial",
    "testing": "partial",
    "delivery": "unknown",
    "ownership": "unknown",
    "relevance": "partial",
    "assessment": "unknown",
    "communication": "unknown",
    "project_level": "unknown",
    "internship_level": "unknown",
    "certification_level": "unknown",
    "coding_level": "unknown",
    "communication_level": "unknown"
  }
}
```

Use the exact `features` from a report, not hand-invented score mappings. For semantic reports, signature is `llm:<evaluator_model>:<rubric_version>`. Freeze the evaluator/prompt before dataset generation. Independent experts should assess readiness from original evidence and practical tasks rather than simply accepting the model's explanations.

Labels: `foundation_developing`, `developing_independence`, `entry_level_ready`. Unknown evidence is not a low-readiness label. Document the rubric, assessors, inter-rater agreement, disputes, consent, and collection dates outside the feature matrix. The script checks declarations and consistency; it cannot prove that labels are authentic human judgements.

Make `group_id` a connected component of related students/artifacts: all snapshots of one student, copied projects, shared repositories, and substantially similar templates must stay together. Exact repeated artifact hashes crossing groups are rejected. Detecting paraphrased or modified copies requires a separate dataset audit. Do not include holdout examples in evaluator prompts.

## Compare and train

```powershell
python -m prototype.train --data path/to/expert-labels.jsonl --output prototype/models/run-001
```

The initial guard requires 60 distinct students and at least 8 leakage groups in each of the three classes. This is a software guard, not a guarantee of statistical adequacy. More data, especially an external cohort, may be required.

The pipeline:

1. Validates features, provenance declarations, evaluator signature, labels, and groups.
2. Creates one fixed 20% group holdout. It stops if class coverage is inadequate.
3. Compares logistic regression (3 configurations), random forest (6), and extra trees (6) using four grouped CV folds on training data only.
4. Fits median imputation, scaling, and categorical encoding inside each training fold.
5. Selects the candidate by CV macro F1, then evaluates the holdout once.
6. Writes the fitted model and metadata to a new version directory.

No ordinary SMOTE on categorical data, no synthetic label generation, no test-set-driven tuning, no reuse of the old numeric artifact. Unknown categories and missing scores are handled by the preprocessing pipeline. Reported metrics include per-class performance, macro F1, balanced accuracy, log loss, and variation across CV folds. They do not establish global optimality.

Only install a run after reviewing real-label data, holdout errors, and a suitable external validation set:

```powershell
$env:SKILLSBRIDGE_MODEL_DIR = "C:\absolute\path\to\prototype\models\run-001"
```

Restart the server. Feature schema and evaluator signature must match before inference. An installable artifact is experimental: probability outputs are uncalibrated expert-readiness category estimates, not placement probabilities. Calibration, subgroup evaluation, uncertainty intervals, and external-cohort validation remain future work.

## Tests

The semantic evaluator also produces provisional artifact levels: `foundation`, `applied`, `independent`, `advanced`, or `unknown`, with an exact supporting quote. These are role-relative rubric categories, not fixed prestige scores. Offline mode always leaves levels unknown. Compare experiences within the same type and role; a certification and a project are not interchangeable. A supported claim is still not independent verification.

To benchmark the evaluator separately against gold artifact labels:

```powershell
python -m prototype.benchmark --data path/to/expert-artifacts.jsonl --mode llm --output prototype/evaluation/assessor.json
```

Each benchmark JSONL record requires `label_source: human_expert`, `evidence` (same object as the API), `target_role`, `expected_categories` (one expected category for each required dimension), and `expected_level`. For example, a communication artifact has `expected_categories: {"communication": "partial"}` and `expected_level: "unknown"`. Never include those gold answers in provider inputs. The report records agreement, per-class errors, failure counts, and completion coverage. Failed items are not counted as successful agreement; interpret agreement jointly with coverage. Small or unrepresentative samples cannot establish production performance.

```powershell
python -m pytest prototype/tests -q
node --check prototype/static/app.js
```

Tests cover persistence, authentication, validation, failed providers, grounding checks, unknown values, malicious-looking evidence, GitHub import boundaries, CORS, training leakage guards, model comparison, unseen categories, and incompatible models. Provider behavior is mocked; external live API performance is not measured. The synthetic training smoke test compares all three models but cannot export `model.joblib` or installable metadata. Its scores are test mechanics only.

The repository's legacy `test_api.py` tests `main:app`, not this prototype. Its old trained model and dependency versions are a separate compatibility concern.

## Prepared datasets and test profiles

The first four researched sources are downloaded and normalized. See [DATA_PREPARATION_REPORT.md](../DATA_PREPARATION_REPORT.md) for exact counts, local file links, duplicate/quarantine findings, source hashes, split boundaries, and baseline/annotation training commands. See [TEST_SAMPLES.md](../TEST_SAMPLES.md) for seven synthetic API-ready profiles and local Qwen commands.

```powershell
python -m prototype.prepare_datasets
python -m prototype.run_samples --sample all --evaluator llm
```

Preparation runs offline against existing raw files and uses the tested `pypdf` dependency for source text extraction. Public resume evidence remains unlabelled until independent review; source placement and survey targets remain separate from expert readiness labels. The prepared public baseline test partitions have been audited for duplicates/conflicting labels and do not replace an external student cohort.

## Deployment boundaries

This is a functional local prototype. A production multiuser service needs per-student authorization, a durable task queue, bounded upload/traffic handling at the reverse proxy, provider retries/backoff, verified source connectors, redaction, model monitoring, and an independently collected evaluation set. The Dockerfile is for local packaging, not a declaration that these concerns have been solved.

```powershell
docker build -f prototype/Dockerfile -t skillsbridge-evidence .
docker run --rm -p 127.0.0.1:8001:8001 skillsbridge-evidence
```

For persistence, mount `/app/prototype/data`; supply provider and API keys using runtime environment variables. Never bake keys or real evidence into images.
