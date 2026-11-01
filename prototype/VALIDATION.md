# Prototype validation

## LM Studio integration update

The updated prototype suite passes **40 tests**, including local provider identity, a keyed rubric schema, source-constrained quote choices, loopback endpoint restrictions, and incomplete-generation rejection. A live synthetic five-artifact evaluation using `qwen2.5-7b-instruct` on LM Studio completed in approximately 37 seconds and passed schema/source checks. This establishes integration mechanics, not expert agreement or predictive accuracy. Remote Anthropic tests remain mocked. Earlier counts and limits below describe the original validation pass.

Validated locally on 1 November 2026.

## Automated checks

- `python -m pytest prototype/tests -q`: **37 passed**.
- `python -m pytest test_api.py -q`: **5 passed** (existing legacy API).
- `node --check prototype/static/app.js`: passed.

The prototype tests cover API input boundaries, key authentication, explicit CORS, SQLite persistence/restart recovery, report lifecycle, review/deletion, quote and level grounding, safe provider failure, mocked structured semantic responses, malicious-looking source text, GitHub import boundaries, evaluator benchmarking, model-schema checks, and missing values.

The model-comparison smoke test fits all 15 configurations across four grouped development folds and evaluates one untouched group holdout. It tests all three candidate families and verifies that synthetic data cannot export an installable model. Its synthetic metrics are intentionally not presented as model accuracy.

The installed environment emits Starlette/httpx deprecation and SciPy optimizer-option warnings. Legacy tests additionally emit SHAP and older XGBoost serialization warnings. All tests completed successfully; these warnings are dependency-maintenance concerns, not evidence of predictive validity.

## Browser checks

Checked desktop at 1280 CSS pixels and mobile at 390 CSS pixels, plus the narrower app panel. No horizontal page overflow was observed at tested widths. Verified example loading, persistent synthetic disclosure, assessment submission and completion, exact-quote findings, unavailable readiness state, saved history, and a saved human-review request. Report completion focused its H2 and announced completion in a status region. File attachment is a real keyboard-focusable button. Reduced motion is respected in CSS and scroll behavior.

An independent Impeccable review identified three issues: keyboard attachment access, accessible completion feedback, and persistent synthetic disclosure. The correction verdict marked all three resolved. That verdict applies to those fixes, not a comprehensive certification of every screen.

## Not established

- No real labelled dataset was provided; real readiness accuracy has not been measured.
- The external LLM path was tested with mocked provider responses, not a paid live account.
- Live GitHub access depends on network availability, repository visibility, and optional server token; tests mock the upstream.
- No claim of globally best model, calibrated placement probability, credential verification, internship verification, code execution, plagiarism detection, or production multiuser readiness.
- No screen-reader session, load test, deployment, Docker build, or external-cohort validation was performed.

See README.md for credentials, API integration, independent labelling, evaluator benchmarking, grouped training, and deployment boundaries.
