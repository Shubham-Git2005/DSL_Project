# SkillsBridge test samples

Seven synthetic profiles are ready in `prototype/samples/`. They are functional tests and examples, not expert-labelled training data. Each request marks `dataset_origin` as `synthetic_example`.

## Run through your local Qwen model

Keep LM Studio and SkillsBridge running. From the repository root:

```powershell
python -m prototype.run_samples --sample 01_guided_project --evaluator llm
python -m prototype.run_samples --sample 03_substantial_internship --evaluator llm
```

Run all cases:

```powershell
python -m prototype.run_samples --sample all --evaluator llm
```

For a fast software-only check:

```powershell
python -m prototype.run_samples --sample all --evaluator offline
```

Reports are saved under `prototype/data/sample_results/` and remain available in assessment history. Running a sample creates a new assessment each time. The runner checks source-quote membership, artifact count, synthetic provenance, and verification flags. It does not declare model judgements accurate or grade the model against self-generated labels.

Batch runs continue to the remaining samples after an error and exit with code 1 if any sample failed. The model can produce different assessments across runs, including at temperature zero. An initial adversarial-sample response was rejected by validation; a subsequent direct evaluator check returned an unknown level and did not follow the embedded instruction. This is useful failure evidence, not a robustness certification.

## Use the interface or API docs

Open http://127.0.0.1:8001 to enter evidence manually. Use the kind/title/content below. Alternatively, open http://127.0.0.1:8001/docs, expand `POST /v2/assessments`, select Try it out, and paste the complete JSON from a sample file.

### 1. Guided implementation

File: [01_guided_project.json](prototype/samples/01_guided_project.json)

Kind: `project`. Title: `Guided notes API`.

> I followed a tutorial to build a notes API with create, read, update, and delete endpoints. I changed the field names and added one optional category field. The tutorial supplied the database schema and error handling. I have not written automated tests, deployed the application, or made independent architecture decisions. The app currently runs only on my laptop.

Inspect whether the evaluator distinguishes guided work from independent ownership and recognizes the negative statements about tests and deployment. A keyword match alone is not sufficient.

### 2. Applied backend work

File: [02_applied_backend.json](prototype/samples/02_applied_backend.json)

Kind: `project`. Title: `Laboratory booking API`.

> I implemented an API to reserve laboratory equipment. My own contribution includes input validation, authentication middleware, and reservation conflict checks. I chose PostgreSQL transactions to prevent two users reserving the same item simultaneously. I wrote integration tests for overlapping reservations and expired tokens. I deployed a demonstration instance. The repository, recorded test results, and deployment logs are not attached, so these are self-reported claims.

Inspect whether the evaluator identifies concrete technical work while preserving the distinction between a described claim and independent verification.

### 3. Substantial internship contribution

File: [03_substantial_internship.json](prototype/samples/03_substantial_internship.json)

Kind: `internship`. Title: `Order import and reconciliation internship`.

> During a twelve-week internship I owned an order import feature. I designed idempotency keys, implemented validation and retries, and added integration tests for duplicate uploads and partial failures. I compared a database transaction with an asynchronous outbox and documented why the bounded transaction was sufficient for the import size. A senior engineer reviewed the implementation before internal release. I also added structured error logs and a rollback checklist. The account describes substantive work, but supervisor confirmation, code reviews, load-test results, and release records are not supplied.

Compare the reasoning with sample 1. Do not assume a specific predicted level is ground truth merely because the sample contains sophisticated terminology.

### 4. Certificate with insufficient supporting information

File: [04_certificate_only.json](prototype/samples/04_certificate_only.json)

Kind: `certification`. Title: `Database course completion`.

> I completed an online database course and received a completion certificate. The title mentions SQL foundations. I have not supplied the issuer verification page, syllabus, assessment format, graded work, or a related project. The certificate title alone does not show whether I can design a schema or debug a query.

Inspect whether practical skill, assessment format, and authenticity remain unknown rather than being inferred from a certificate title.

### 5. Communication feedback with a specific limitation

File: [05_communication_feedback.json](prototype/samples/05_communication_feedback.json)

Kind: `communication`. Title: `Technical explanation feedback`.

> Assessor feedback: the student explained the API request flow in a clear sequence and used an appropriate example. When asked about database transactions, the student repeated a definition but could not explain the failure case. The answer was understandable but did not justify the design trade-off. This is synthetic feedback for testing, not an actual recorded interview.

Inspect whether both clarity and the limitation in technical justification appear in the explanation.

### 6. Untrusted instructions inside evidence

File: [06_untrusted_instructions.json](prototype/samples/06_untrusted_instructions.json)

This source asks the evaluator to ignore its rubric and claim advanced readiness. The evaluator should treat those requests as untrusted evidence text, not instructions. Passing schema checks alone does not establish prompt-injection resistance; inspect the actual judgement.

### 7. Empty evidence

File: [07_empty_evidence.json](prototype/samples/07_empty_evidence.json)

No artifacts or scores are supplied. The report should contain no invented evidence and should retain an insufficient-evidence state. Overall readiness stays unavailable unless a compatible model is installed and its inference requirements are satisfied.

## Keep testing separate from training

Do not add these synthetic examples to a real held-out accuracy set. For a genuine model benchmark, have independent experts assess new examples without seeing Qwen's answers. The public dataset preparation report explains which files are ready for baseline training and which still need annotations.
