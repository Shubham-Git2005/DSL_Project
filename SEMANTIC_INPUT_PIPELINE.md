# Evidence-to-model inputs

The UI now supports a source-linked measurement extraction step in addition to semantic evidence ratings.

1. Submit projects, internships, certificates, assessment feedback, and record excerpts as evidence.
2. Qwen applies the role-specific semantic rubric; the existing seventeen-feature representation is exposed in the report.
3. In the campus prediction panel, select **Extract inputs from my evidence**.
4. A separate local Qwen request extracts only explicitly stated measurements matching the campus model's original features. Missing values stay blank. Quotes, field anchors, ranges, and explicit assessment scales are checked in Python.
5. Review the values and source quotes, resolve conflicts, and supply missing measurements.
6. Select **Predict placement label**. The saved pipeline performs its fitted imputation, scaling, and encoding, then runs the trained Random Forest.

## Example evidence containing original measurements

```text
Academic record: CGPA 8.2 out of 10. SSC marks: 82%. HSC marks: 79%.
Profile totals: 2 completed internships and 3 completed projects.
Completed workshops and certifications combined: 2.
Aptitude test score: 84 out of 100.
Soft skills rating: 4.2 out of 5.
Extracurricular activities: Yes. Completed placement training: Yes.
```

These are synthetic test values. Extraction may leave a field unknown when ambiguous; that is preferable to estimation.

## API

- `POST /v2/standardize` accepts the same student/evidence request as assessment creation and returns original measurements, source quotes, missing fields, and conflicts.
- `POST /v2/assessments/{id}/standardize` extracts from the saved original request and persists the result with its evidence report.
- `GET /v2/assessments/{id}/report` includes `standardized_inputs` after extraction.

Both endpoints use the existing API-key access checks. The local extraction input is bounded to the first 10,000 evidence characters, and the response reports truncation. The browser's corrected values can be used in prediction and export; corrections are not currently separately persisted as verified measurements.

## Important boundaries

Semantic ratings are not converted into counts or source test scores. Project count is not inferred merely by counting submitted paragraphs. CGPA, aptitude, and soft-skills measurement scales must be explicit in source quotations. A 0–100 communication score is never silently converted into a 0–5 soft-skills score. Source-quote checks do not prove authenticity or complete semantic correctness, so human review remains required.

The campus model's measured 78.62% accuracy is from its original structured test data. It has not been remeasured on LLM-extracted inputs. A genuinely fused semantic readiness classifier must be trained and independently evaluated using frozen Qwen-generated features and expert readiness labels; its existing training path remains available without invented labels or substituted schemas.
