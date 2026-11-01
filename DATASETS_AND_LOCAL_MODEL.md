# SkillsBridge: datasets and local Qwen integration

Researched on 1 November 2026. These sources serve different tasks; they are not a single joined student dataset. Dataset sizes and licences below are publisher/card statements, not an independent data audit. Links lead to the source pages and their download/file controls.

## 1. Recommended data sources

### A. ResumeExtractBench: extraction of experience, projects, certifications

- [Dataset and files](https://huggingface.co/datasets/Careerflow/ResumeExtractBench)
- [Author's benchmark implementation](https://github.com/careerflow/resume-extract-bench)
- Card reports 30 documents covering anonymized real, synthetic, handwritten, and expert-created examples.
- Ground truth covers structured resume fields, including experience, projects, education, and certifications.
- Declared licence: CC BY 4.0.
- Best use: check whether an extraction layer preserves the source facts before assessment.
- Not a readiness or internship-quality dataset. The text-only prototype needs prepared text; Qwen2.5-7B-Instruct does not itself read scanned pages.

### B. Structured resumes: raw evidence examples

- [uhfew/resumes dataset and files](https://huggingface.co/datasets/uhfew/resumes)
- Viewer reports approximately 4.82k records with experience, education, skills, projects, certifications, and internships fields.
- Card describes mixed real and synthetic sources and declares MIT.
- Best use: select source passages to test evidence ingestion and rubric application.
- Not independently annotated for readiness; fields can be sparse and synthetic provenance must be retained. Audit the data card and source records before reuse.

### C. Campus Recruitment CSV: numerical placement baseline

- [Dataset and CSV files](https://huggingface.co/datasets/surya5678/Campus_Recruitment_CSV)
- Card reports 10,000 rows, with CGPA, internship/project/certification counts, aptitude, soft-skills rating, and placement status.
- Declared licence: CC0 1.0.
- Best use: a separate numerical baseline and pipeline comparison.
- It does not contain project code, detailed internship responsibilities, or expert quality rankings. The card's campus provenance is vague; verified real outcomes are not established. A soft-skills rating is not automatically a communication assessment on your scale.

### D. Placement-readiness survey: relevant questionnaire design

- [Mendeley dataset, dictionary, and download](https://data.mendeley.com/datasets/f52mmcsbsn/1)
- Covers CGPA range, programming/DSA, projects, internships, coding practice, communication, preparation, and self-reported readiness.
- Declared licence: CC BY 4.0.
- Best use: design a student intake survey and inspect relevant variable categories.
- The publisher explicitly states readiness is self-reported, not verified placement outcomes. Do not relabel those answers as independent expert readiness judgements.

### E. APPS: coding assessment tasks

- [Authors' repository and original download link](https://github.com/hendrycks/apps)
- [Hugging Face mirror](https://huggingface.co/datasets/codeparrot/apps)
- Provides 10,000 programming problems with introductory, interview, and competition difficulty categories, problem statements, solutions, and test data.
- Best use: build a coding task bank and compare a student's tested solution with the task requirements.
- Problem difficulty is not a student-readiness label. Existing public tasks can be memorized by LLMs; reserve fresh assessments for final evaluation.
- The repository/mirror show MIT labels; inspect the original dataset terms and source-task rights separately rather than assuming the code licence covers all task content.
- The mirror currently uses a legacy loading script; prefer directly downloaded data files over enabling arbitrary dataset scripts without inspection.

### F. PERSUADE 2.0: written communication proxy

- [Authors' dataset README and train/test download links](https://github.com/scrosseye/persuade_corpus_2.0)
- More than 25,000 argumentative essays by US school students, with holistic and discourse-element assessments.
- Declared licence: CC BY-NC-SA 4.0, with noncommercial/share-alike restrictions.
- Best use: research written clarity and argument structure.
- It does not measure spoken technical interviews or Indian engineering placement communication. Do not directly transfer its scores to your 0–100 communication field or use it as placement ground truth.

### G. ESCO: role/skill vocabulary

- [Official European Commission download](https://esco.ec.europa.eu/en/use-esco/download)
- Skills/occupations classification available in formats including CSV.
- Best use: normalize skill names and relate project/course descriptions to role requirements.
- It is a taxonomy, not a dataset ranking certificates or students. The official download flow requests an email address and privacy-statement acceptance; use its current access and reuse terms.

### H. RepoReapers: project-engineering reference tooling

- [Authors' repository](https://github.com/RepoReapers/reaper)
- Tooling for examining engineering-practice signals in GitHub repositories.
- Best use: inform deterministic project checks and the design of project-quality annotations.
- This is an auxiliary research/tooling source, not a ready-to-train student-level dataset. Check the repository, related research, and any separate data terms before collection. Project engineering signals do not prove individual ownership.

## 2. What is still missing

None of the verified sources above supplies the complete linked training target required by the new classifier:

```text
One real student's CGPA + communication assessment + coding assessment
+ internship evidence + attributable project evidence + certification evidence
+ an independent, role-specific expert readiness judgement
```

Do not join unrelated people across datasets, fabricate missing GitHub/LeetCode values, turn self-ratings into expert labels, or train on Qwen labels and describe agreement with Qwen as independent accuracy.

For an initial project-specific dataset:

1. Use public sources for extraction and artifact-level development tests.
2. Collect consented profiles from real students, initially for one role.
3. Have two independent reviewers label a representative subset using the rubric and practical tasks; resolve disagreements.
4. Keep original evidence, source IDs/hashes, verification status, expert labels, and label provenance.
5. Keep related students and copied/shared projects in one leakage group.
6. Use the frozen evaluator to create features, then train using the existing grouped pipeline.
7. Evaluate once on untouched students; add a later or external cohort when available.

The script's 60-student guard is not a guarantee that 60 students establish reliable performance. Collection size should follow class coverage, error analysis, and uncertainty.

## 3. Local LM Studio integration

The server at `http://127.0.0.1:1234/v1/models` was reachable and listed `qwen2.5-7b-instruct`. The prototype now supports its OpenAI-compatible chat-completions endpoint using plain httpx; no OpenAI API key or SDK is required.

[LM Studio structured-output documentation](https://lmstudio.ai/docs/developer/openai-compat/structured-output) explains JSON-schema response formats. [Qwen's model card](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) documents the base instruction model; a particular local quantization and runtime still require their own evaluation.

Launch the prototype with your already-running local model:

```powershell
python -m prototype.run_local
```

Stop the existing SkillsBridge process on port 8001 before starting another copy. Keep LM Studio running separately. The launcher sets:

```text
ASSESSOR_PROVIDER=lmstudio
ASSESSOR_MODEL=qwen2.5-7b-instruct        (default if unset)
LMSTUDIO_BASE_URL=http://127.0.0.1:1234/v1
```

For an explicit configuration:

```powershell
$env:ASSESSOR_PROVIDER = 'lmstudio'
$env:ASSESSOR_MODEL = 'qwen2.5-7b-instruct'
$env:LMSTUDIO_BASE_URL = 'http://127.0.0.1:1234/v1'
python -m uvicorn prototype.app:app --host 127.0.0.1 --port 8001
```

If your LM Studio server requires authentication, set `LMSTUDIO_API_KEY` on the server. The local endpoint is restricted to loopback HTTP(S) addresses and does not use environment proxy settings.

## 4. Local assessment safeguards

- Requests go to `/v1/chat/completions` with structured JSON output, temperature zero, a 2,400-token output budget, and a 300-second client timeout.
- Quotes are constrained to actual source excerpts rather than allowing the model to paraphrase them.
- Findings use a keyed transport schema, ensuring one required entry per dimension under constrained generation. The server converts that structure to the existing public findings list.
- Local schema/grounding checks still run; truncated or invalid responses fail instead of becoming successful reports.
- The report model identifier is `lmstudio/qwen2.5-7b-instruct`. Its evaluator signature differs from the Anthropic and offline paths.
- Begin with short representative excerpts. Available context and speed depend on the model loaded in LM Studio, its quantization, and the hardware.

An exact quote can still be poorly chosen or misinterpreted. These constraints validate structure and source membership, not the correctness of the judgement. A local Qwen assessment is provisional until benchmarked against independent expert labels.

This integration enables semantic evidence assessment. It does not supply the missing expert labels or enable a validated overall readiness prediction by itself.
