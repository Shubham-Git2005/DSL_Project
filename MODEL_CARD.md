# Model Card: SkillsBridge Placement Readiness Model

## Overview
Predicts a student's placement readiness (0-100%) from academic, project, certification, and coding-activity signals, with per-prediction explanations via SHAP.

## Intended Use
- **Primary use:** Give students a directional, explainable readiness signal and highlight specific improvement areas (weakest contributing factors).
- **Not intended for:** Sole/automated placement or admission decisions. This is a guidance tool, not a gatekeeping tool — output should always be presented alongside human mentorship (TPC/faculty guidance), not as a final verdict.

## Training Data
- Source: Kaggle "Campus Placement Prediction Dataset 2026" family (synthetic).
- Size: ~20,000 rows (verify exact count from your actual pull).
- **Known limitation — synthetic generation:** Preliminary correlation and cross-validation checks (see notebook Cells 4b/7) should be reviewed before trusting reported accuracy; near-perfect accuracy on this dataset family has been observed elsewhere and typically indicates the target label was generated via a deterministic formula rather than real-world noisy outcomes. Real-world performance is expected to be lower.
- **Known limitation — feature coverage:** The dataset captures static academic-record fields (CGPA, internship/certification counts). It does NOT capture live platform activity (GitHub commit history, Codeforces/CodeChef contest performance, LinkedIn engagement) that the broader SkillsBridge vision depends on. This model should be treated as a prototype/baseline, to be retrained on real scraped activity data before production use.

## Evaluation
- Metrics: Accuracy, Precision, Recall, F1, ROC-AUC (see notebook Cell 8 comparison table).
- Class imbalance was addressed via SMOTE during training only (not applied to the test set).
- Calibration was verified via reliability curve (notebook Cell 9) — probabilities should be interpreted with this calibration in mind.

## Fairness Considerations
- If the dataset contains any demographic fields (gender, category, region, college tier), a subgroup performance audit (e.g., via Fairlearn) should be run before deployment to check for disparate error rates. Not yet performed in this version — flagged as required follow-up before production rollout.

## Explainability
- Global feature importance via Random Forest / XGBoost built-ins.
- Per-prediction explanation via SHAP — surfaced to end users as "weakest factors" / "strongest factors" in the API response.

## Limitations & Future Work
1. Validate against real student outcomes (a small real-world holdout set from actual GitHub/Codeforces/placement records) before trusting reported metrics.
2. Re-run with live-activity features once GitHub/CodeChef API integration is built.
3. Run a fairness audit if demographic columns exist.
4. Set up drift monitoring (e.g., Evidently AI) once live traffic begins, to detect when the model's assumptions stop matching new student cohorts.
5. Periodically retrain as new placement cycles complete, using MLflow's run history to compare each new model against the currently deployed one before promoting it.

## Maintainers
SkillsBridge/SentinelAI project team — [Shubham et al.], final-year BE-IT project.
