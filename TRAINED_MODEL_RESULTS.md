# Trained baseline models

Models selected by validation macro F1; test partitions evaluated after selection. These are public-data baselines, not the expert-labelled evidence readiness classifier.

| Model | Algorithm | Test records | Accuracy | Balanced accuracy | Macro F1 | Majority accuracy |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| campus | Random forest | 1483 | 78.62% | 78.49% | 0.7818 | 58.60% |
| survey | Logistic regression | 165 | 64.85% | 62.96% | 0.6080 | 72.12% |

The survey classifier does not beat majority guessing on accuracy; it is retained as an experimental comparison, not promoted as a reliable readiness predictor. Campus labels are publisher-provided placement statuses with unverified real-world provenance. Survey labels are self-reported readiness. The public splits were audited during preparation and do not constitute external-cohort validation. Probabilities are uncalibrated.

## Artifacts

- [Campus model](prototype/models/campus-final/baseline.joblib) and [full evaluation](prototype/models/campus-final/baseline-report.json).
- [Survey model](prototype/models/survey-final/baseline.joblib) and [full evaluation](prototype/models/survey-final/baseline-report.json).

## API integration

`GET /v2/baselines/campus` and `GET /v2/baselines/survey` return metrics and original feature schemas.

`POST /v2/baselines/{name}/predict` accepts `{"features": {...}}`. Supply the original named features; do not substitute Qwen categories or fabricated measurements. Exact examples are saved next to the models as example-request.json. Shared API-key authorization applies when configured.

The normal evidence assessment endpoint continues using local Qwen. Its overall readiness probability remains unavailable until independent expert labels support a separate trained classifier. No source schema or target was silently substituted.
