"""
SkillsBridge Placement Readiness API
Loads the calibrated model trained in the Colab notebook and serves predictions.

Run locally:
    pip install -r requirements.txt
    uvicorn main:app --reload

Run in Docker:
    docker build -t skillsbridge-api .
    docker run -p 8000:8000 skillsbridge-api

Then visit http://localhost:8000/docs for interactive API testing (Swagger UI).
"""

import joblib
import numpy as np
import pandas as pd
import shap
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="SkillsBridge Placement Readiness API",
    version="1.0.0",
    description="Predicts placement readiness and explains the result."
)

# Loaded once at startup, not per-request (important for performance)
model = joblib.load("skillsbridge_readiness_model.pkl")
feature_order = joblib.load("model_feature_order.pkl")

# The artifact is a multiclass calibrated XGBoost model. A model-agnostic
# explainer keeps working across the saved XGBoost/SHAP versions.
ready_class_index = list(model.classes_).index(0)
shap_background = np.array([[
    7.0, 10.0, 1.0, 1.0, 2.0, 60.0, 60.0, 500.0,
    50.0, 1.0, 50.0, 40.0, 60.0, 60.0
]], dtype=float)


def readiness_probability(values: np.ndarray) -> np.ndarray:
    rows = pd.DataFrame(values, columns=feature_order)
    return model.predict_proba(rows)[:, ready_class_index]


explainer = shap.Explainer(
    readiness_probability,
    shap_background,
    algorithm="permutation",
)


class StudentProfile(BaseModel):
    cgpa: float = Field(..., ge=0, le=10, description="CGPA on a 0-10 scale")
    internships: int = Field(..., ge=0)
    projects: int = Field(..., ge=0)
    certifications: int = Field(..., ge=0)
    coding_score: float = Field(..., ge=0, le=100)
    communication_score: float = Field(..., ge=0, le=100)

    # Model training also uses additional placement signals; these are optional
    # compatibility fields for newer payloads and default to neutral values.
    dsa_problems: int | None = Field(None, ge=0)
    aptitude_score: float | None = Field(None, ge=0, le=100)
    leetcode_rating: float | None = Field(None, ge=800, le=3000)
    github_contributions: int | None = Field(None, ge=0)
    hackathons: int | None = Field(None, ge=0)
    ai_ml_skill: float | None = Field(None, ge=1, le=10)
    system_design: float | None = Field(None, ge=1, le=10)
    resume_score: float | None = Field(None, ge=0, le=100)
    mock_interview_score: float | None = Field(None, ge=0, le=100)


class ReadinessResponse(BaseModel):
    readiness_percent: float
    label: str
    weakest_factors: list[str] = []
    strongest_factors: list[str] = []
    explanations: list[dict[str, float | str]] = []


UI_HTML = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>SkillsBridge Placement Readiness</title>
    <style>
      :root {
        --bg: #0a0d12;
        --surface: #11161e;
        --surface-2: #171e28;
        --surface-3: #202936;
        --text: #f1f5f9;
        --muted: #9aa7b7;
        --faint: #64748b;
        --accent: #67e8f9;
        --accent-strong: #22d3ee;
        --positive: #86efac;
        --negative: #fda4af;
        --border: rgba(148, 163, 184, 0.18);
        --radius: 14px;
      }

      * { box-sizing: border-box; }
      body {
        margin: 0;
        min-height: 100vh;
        font-family: "Segoe UI", Arial, sans-serif;
        background:
          radial-gradient(circle at 82% 8%, rgba(34, 211, 238, 0.11), transparent 28rem),
          radial-gradient(circle at 6% 92%, rgba(14, 116, 144, 0.1), transparent 25rem),
          var(--bg);
        color: var(--text);
      }

      .container { max-width: 1240px; margin: 0 auto; padding: 34px 24px 64px; }
      .topbar { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin-bottom: 42px; }
      .brand { display: flex; align-items: center; gap: 12px; font-weight: 700; letter-spacing: -0.02em; }
      .brand-mark { display: grid; place-items: center; width: 34px; height: 34px; border: 1px solid rgba(103, 232, 249, 0.65); border-radius: 10px; color: var(--accent); font-size: 0.86rem; }
      .status { color: var(--muted); font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; }
      .status::before { content: ""; display: inline-block; width: 7px; height: 7px; margin-right: 8px; border-radius: 50%; background: var(--positive); box-shadow: 0 0 12px rgba(134, 239, 172, 0.7); }
      .header { max-width: 760px; margin-bottom: 26px; }
      h1 { margin: 0 0 12px; max-width: 620px; font-size: clamp(2.5rem, 6vw, 5.3rem); line-height: 0.98; letter-spacing: -0.065em; }
      .sub { max-width: 590px; margin: 0; color: var(--muted); font-size: 1.03rem; line-height: 1.65; }

      .workspace { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr); gap: 18px; align-items: start; }
      .panel { background: rgba(17, 22, 30, 0.88); border: 1px solid var(--border); border-radius: var(--radius); padding: 24px; box-shadow: 0 24px 70px rgba(0, 0, 0, 0.22); backdrop-filter: blur(16px); }
      .panel-heading { display: flex; align-items: baseline; justify-content: space-between; gap: 16px; margin-bottom: 22px; }
      .panel-heading h2 { margin: 0; font-size: 1.05rem; letter-spacing: -0.02em; }
      .panel-heading span { color: var(--faint); font-size: 0.78rem; }
      .section-title { margin: 26px 0 13px; color: var(--accent); font-size: 0.72rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; }
      .section-title:first-of-type { margin-top: 0; }
      .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
      .field { display: flex; flex-direction: column; gap: 7px; }
      label { color: var(--muted); font-size: 0.82rem; }
      input { width: 100%; padding: 12px 13px; border: 1px solid var(--border); border-radius: 10px; outline: none; background: rgba(10, 13, 18, 0.82); color: var(--text); font: inherit; transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease; }
      input:hover { border-color: rgba(103, 232, 249, 0.36); }
      input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(103, 232, 249, 0.12); transform: translateY(-1px); }
      .actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; margin-top: 24px; }
      button { border: 1px solid transparent; border-radius: 10px; background: var(--accent); color: #083344; padding: 12px 17px; font-weight: 750; cursor: pointer; transition: transform 160ms ease, background 160ms ease, box-shadow 160ms ease; }
      button:hover { background: #a5f3fc; box-shadow: 0 10px 26px rgba(34, 211, 238, 0.18); transform: translateY(-1px); }
      button:active { transform: translateY(1px) scale(0.98); }
      .secondary { border-color: var(--border); background: transparent; color: var(--text); }
      .secondary:hover { border-color: rgba(103, 232, 249, 0.45); background: rgba(103, 232, 249, 0.07); }
      .error { min-height: 1.2em; margin-top: 10px; color: var(--negative); font-size: 0.86rem; }

      .result { min-height: 420px; }
      .result-empty { display: grid; min-height: 350px; place-items: center; padding: 30px; color: var(--muted); text-align: center; }
      .result-empty strong { display: block; margin-bottom: 8px; color: var(--text); font-size: 1.15rem; }
      .result.visible .result-empty { display: none; }
      .result-content { display: none; }
      .result.visible .result-content { display: block; }
      .result-kicker { color: var(--accent); font-size: 0.72rem; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; }
      .score { margin: 12px 0 4px; font-size: clamp(3.8rem, 8vw, 6rem); line-height: 0.92; letter-spacing: -0.08em; }
      .score-caption { color: var(--muted); font-size: 0.86rem; }
      .tag { display: inline-flex; margin: 18px 0 22px; padding: 7px 11px; border-radius: 999px; font-size: 0.78rem; font-weight: 700; }
      .tag.ready { background: rgba(134, 239, 172, 0.12); color: var(--positive); }
      .tag.improve { background: rgba(251, 191, 36, 0.12); color: #fcd34d; }
      .facts { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
      .fact-box { min-width: 0; padding: 15px; border: 1px solid var(--border); border-radius: 11px; background: rgba(32, 41, 54, 0.58); }
      .fact-box h3 { margin: 0 0 11px; color: var(--muted); font-size: 0.78rem; font-weight: 600; }
      ul { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
      li { color: #d7dee8; font-size: 0.83rem; line-height: 1.45; }
      .explanations { margin-top: 12px; }
      .explanations li { display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid rgba(148, 163, 184, 0.1); padding: 8px 0; }
      .explanations li:last-child { border-bottom: 0; }
      .impact-positive { color: var(--positive); }
      .impact-negative { color: var(--negative); }
      .loading { opacity: 0.6; pointer-events: none; }

      @media (max-width: 860px) {
        .workspace { grid-template-columns: 1fr; }
        .result { min-height: auto; }
      }
      @media (max-width: 560px) {
        .container { padding: 22px 14px 40px; }
        .topbar { margin-bottom: 30px; }
        .status { font-size: 0.66rem; }
        h1 { font-size: 3.2rem; }
        .panel { padding: 17px; }
        .grid, .facts { grid-template-columns: 1fr; }
        .actions button { width: 100%; }
        .explanations li { display: block; }
      }
      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after { scroll-behavior: auto !important; transition-duration: 0.01ms !important; }
      }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="topbar">
        <div class="brand"><span class="brand-mark">SB</span><span>SkillsBridge / Readiness Lab</span></div>
        <div class="status">Model online</div>
      </div>
      <div class="header">
        <h1>SkillsBridge Placement Readiness</h1>
        <p class="sub">Adjust the profile inputs, run a prediction, and see which signals move the result.</p>
      </div>

      <div class="workspace">
        <div class="panel">
          <div class="panel-heading">
          <h2>Student profile</h2>
          <span>15 signals</span>
          </div>
          <form id="readiness-form">
          <div class="section-title">Academic foundation</div>
          <div class="grid">
            <div class="field">
              <label for="cgpa">CGPA</label>
              <input id="cgpa" name="cgpa" type="number" min="0" max="10" step="0.1" value="8.2" required />
            </div>
            <div class="field">
              <label for="internships">Internships</label>
              <input id="internships" name="internships" type="number" min="0" step="1" value="1" required />
            </div>
            <div class="field">
              <label for="projects">Projects</label>
              <input id="projects" name="projects" type="number" min="0" step="1" value="4" required />
            </div>
            <div class="field">
              <label for="certifications">Certifications</label>
              <input id="certifications" name="certifications" type="number" min="0" step="1" value="2" required />
            </div>
            <div class="field">
              <label for="coding_score">Coding Score</label>
              <input id="coding_score" name="coding_score" type="number" min="0" max="100" step="1" value="75" required />
            </div>
            <div class="field">
              <label for="communication_score">Communication Score</label>
              <input id="communication_score" name="communication_score" type="number" min="0" max="100" step="1" value="60" required />
            </div>
          </div>

          <div class="section-title">Practical signals</div>
          <div class="grid">
            <div class="field">
              <label for="dsa_problems">DSA Problems</label>
              <input id="dsa_problems" name="dsa_problems" type="number" min="0" step="1" value="8" />
            </div>
            <div class="field">
              <label for="aptitude_score">Aptitude Score</label>
              <input id="aptitude_score" name="aptitude_score" type="number" min="0" max="100" step="1" value="60" />
            </div>
            <div class="field">
              <label for="leetcode_rating">LeetCode Rating</label>
              <input id="leetcode_rating" name="leetcode_rating" type="number" min="800" max="3000" step="1" value="1600" />
            </div>
            <div class="field">
              <label for="github_contributions">GitHub Contributions</label>
              <input id="github_contributions" name="github_contributions" type="number" min="0" step="1" value="50" />
            </div>
            <div class="field">
              <label for="hackathons">Hackathons</label>
              <input id="hackathons" name="hackathons" type="number" min="0" step="1" value="1" />
            </div>
            <div class="field">
              <label for="ai_ml_skill">AI/ML Skill</label>
              <input id="ai_ml_skill" name="ai_ml_skill" type="number" min="1" max="10" step="0.1" value="5" />
            </div>
            <div class="field">
              <label for="system_design">System Design</label>
              <input id="system_design" name="system_design" type="number" min="1" max="10" step="0.1" value="4" />
            </div>
            <div class="field">
              <label for="resume_score">Resume Score</label>
              <input id="resume_score" name="resume_score" type="number" min="0" max="100" step="1" value="60" />
            </div>
            <div class="field">
              <label for="mock_interview_score">Mock Interview Score</label>
              <input id="mock_interview_score" name="mock_interview_score" type="number" min="0" max="100" step="1" value="60" />
            </div>
          </div>

          <div class="actions">
            <button type="submit">Predict Readiness</button>
            <button type="button" class="secondary" id="sample-btn">Use Sample Data</button>
          </div>
          <div class="error" id="error-message"></div>
          </form>
        </div>

        <div id="result" class="result">
          <div class="panel">
            <div class="result-empty">
              <div><strong>Your result will appear here</strong><span>Run a prediction to inspect readiness and feature impact.</span></div>
            </div>
            <div class="result-content">
              <div class="result-kicker">Readiness score</div>
              <div class="score" id="score">--</div>
              <div class="score-caption">Model probability for the ready class</div>
              <div id="label-tag" class="tag">--</div>
              <div class="facts">
                <div class="fact-box">
                  <h3>Strongest signals</h3>
                  <ul id="strongest"></ul>
                </div>
                <div class="fact-box">
                  <h3>Needs attention</h3>
                  <ul id="weakest"></ul>
                </div>
              </div>
              <div class="fact-box explanations">
                <h3>Feature impact</h3>
                <ul id="explanations"></ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <script>
      const form = document.getElementById('readiness-form');
      const result = document.getElementById('result');
      const scoreEl = document.getElementById('score');
      const labelTag = document.getElementById('label-tag');
      const weakestEl = document.getElementById('weakest');
      const strongestEl = document.getElementById('strongest');
      const explanationsEl = document.getElementById('explanations');
      const errorMessage = document.getElementById('error-message');
      const sampleBtn = document.getElementById('sample-btn');

      sampleBtn.addEventListener('click', () => {
        document.getElementById('cgpa').value = 8.2;
        document.getElementById('internships').value = 1;
        document.getElementById('projects').value = 4;
        document.getElementById('certifications').value = 2;
        document.getElementById('coding_score').value = 75;
        document.getElementById('communication_score').value = 60;
        document.getElementById('dsa_problems').value = 8;
        document.getElementById('aptitude_score').value = 60;
        document.getElementById('leetcode_rating').value = 1600;
        document.getElementById('github_contributions').value = 50;
        document.getElementById('hackathons').value = 1;
        document.getElementById('ai_ml_skill').value = 5;
        document.getElementById('system_design').value = 4;
        document.getElementById('resume_score').value = 60;
        document.getElementById('mock_interview_score').value = 60;
      });

      form.addEventListener('submit', async (event) => {
        event.preventDefault();
        errorMessage.textContent = '';
        form.classList.add('loading');

        const payload = {
          cgpa: Number(document.getElementById('cgpa').value),
          internships: Number(document.getElementById('internships').value),
          projects: Number(document.getElementById('projects').value),
          certifications: Number(document.getElementById('certifications').value),
          coding_score: Number(document.getElementById('coding_score').value),
          communication_score: Number(document.getElementById('communication_score').value),
          dsa_problems: Number(document.getElementById('dsa_problems').value),
          aptitude_score: Number(document.getElementById('aptitude_score').value),
          leetcode_rating: Number(document.getElementById('leetcode_rating').value),
          github_contributions: Number(document.getElementById('github_contributions').value),
          hackathons: Number(document.getElementById('hackathons').value),
          ai_ml_skill: Number(document.getElementById('ai_ml_skill').value),
          system_design: Number(document.getElementById('system_design').value),
          resume_score: Number(document.getElementById('resume_score').value),
          mock_interview_score: Number(document.getElementById('mock_interview_score').value),
        };

        try {
          const response = await fetch('/v1/predict-readiness', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });

          const data = await response.json();
          if (!response.ok) {
            throw new Error(data.detail || 'Prediction failed.');
          }

          scoreEl.textContent = `${data.readiness_percent}%`;
          labelTag.textContent = data.label;
          labelTag.className = `tag ${data.label === 'Ready' ? 'ready' : 'improve'}`;

          weakestEl.innerHTML = (data.weakest_factors.length ? data.weakest_factors : ['Not enough data']).map(item => `<li>${item}</li>`).join('');
          strongestEl.innerHTML = (data.strongest_factors.length ? data.strongest_factors : ['No dominant signal']).map(item => `<li>${item}</li>`).join('');
          explanationsEl.innerHTML = data.explanations.map(item => `<li><span><strong>${item.factor}</strong><br><small>Input: ${item.value}</small></span><span class="${item.impact > 0 ? 'impact-positive' : item.impact < 0 ? 'impact-negative' : ''}">${item.impact > 0 ? '+' : ''}${item.impact} pts</span></li>`).join('');
          result.classList.add('visible');
        } catch (err) {
          errorMessage.textContent = err.message;
        } finally {
          form.classList.remove('loading');
        }
      });
    </script>
  </body>
</html>
"""


@app.get("/", include_in_schema=False)
@app.get("/ui", include_in_schema=False)
def ui_page():
    return HTMLResponse(UI_HTML)


@app.get("/health")
def health_check():
    """Basic liveness check — used by load balancers / uptime monitors."""
    return {"status": "ok"}


@app.post("/v1/predict-readiness", response_model=ReadinessResponse)
def predict_readiness(profile: StudentProfile):
    try:
        row_values = {}
        for field in feature_order:
            value = getattr(profile, field, None)
            if value is not None:
                row_values[field] = value
            elif field == "dsa_problems" and hasattr(profile, "coding_score"):
                row_values[field] = max(0, round(profile.coding_score / 10))
            elif field == "aptitude_score" and hasattr(profile, "coding_score"):
                row_values[field] = profile.coding_score
            elif field == "leetcode_rating" and hasattr(profile, "coding_score"):
                row_values[field] = 800 + profile.coding_score * 18.87
            elif field in {"ai_ml_skill", "system_design"} and hasattr(profile, "coding_score"):
                row_values[field] = max(1, min(10, profile.coding_score / 10))
            else:
                row_values[field] = 0

        row = pd.DataFrame([row_values], columns=feature_order)
        proba = model.predict_proba(row)[0][ready_class_index]
        label = "Ready" if proba >= 0.5 else "Needs Improvement"

        shap_values = explainer(row.to_numpy(), max_evals=2 * len(feature_order) + 1)
        contributions = sorted(
            zip(feature_order, shap_values.values[0]),
            key=lambda item: float(item[1]),
        )
        weakest = [f for f, value in contributions if value < 0][:3]
        strongest = [f for f, value in reversed(contributions) if value > 0][:3]
        explanations = [
            {
                "factor": factor,
                "impact": round(float(value) * 100, 2),
                "direction": (
                    "increases readiness"
                    if value > 0
                    else "decreases readiness"
                    if value < 0
                    else "has little measurable impact"
                ),
                "value": float(row_values[factor]),
            }
            for factor, value in sorted(
                contributions, key=lambda item: abs(float(item[1])), reverse=True
            )
        ]

        return ReadinessResponse(
            readiness_percent=round(proba * 100, 1),
            label=label,
            weakest_factors=weakest,
            strongest_factors=strongest,
            explanations=explanations,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Prediction failed: {str(e)}")
