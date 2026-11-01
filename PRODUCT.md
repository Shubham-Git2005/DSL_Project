# SkillsBridge

## Platform

web

## Users

Students collecting evidence of internship, project, certification, coding, communication, and academic readiness. Faculty can review evidence and supply future training labels.

## Product purpose

Interpret the substance of student evidence and present grounded, role-specific assessments through a functional prototype and integrable API.

## Stack

Existing Python/FastAPI repository. New prototype is isolated under prototype/ and served by FastAPI with browser-native HTML, CSS, and JavaScript. The legacy notebook and application remain available.

## Confirmed constraints

The user confirmed no labelled dataset is available. Build a working prototype and training pipeline, not fabricated accuracy claims. Support an external LLM evaluator with an explicitly labelled offline fallback. Preserve distinctions between self-reported claims, observed source contents, and independent verification. Missing evidence must remain unknown.

## Brand commitments

SkillsBridge. The user requests a beautiful, smooth, functional interface without generic AI design patterns.

## Evidence on hand

Legacy Colab notebook, six-feature training schema, fourteen-feature saved model, and FastAPI service. No expert-labelled evidence dataset or validated replacement readiness model is supplied.

## Open decisions

Deployment audience, identity provider, expert labelling panel, and external model provider credentials. Prototype scope assumes a single workspace on localhost; multi-user authorization is not implied.
