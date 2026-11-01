import asyncio
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles

from .evaluator import evaluate, semantic_configuration
from .modeling import model_status, predict_report
from .schemas import AssessmentReport, AssessmentRequest, Evidence, GitHubRequest, JobCreated, JobStatus, ReviewRequest, RUBRIC_VERSION, SCHEMA_VERSION
from .store import Store

ROOT = Path(__file__).resolve().parent
logger = logging.getLogger("skillsbridge")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def create_app(data_dir: Path | None = None):
    directory = data_dir or Path(os.getenv("SKILLSBRIDGE_DATA_DIR", str(ROOT / "data")))
    store = Store(directory / "assessments.sqlite3")
    model_dir = Path(os.getenv("SKILLSBRIDGE_MODEL_DIR", str(ROOT / "models")))
    semaphore = asyncio.Semaphore(2)

    @asynccontextmanager
    async def lifespan(app):
        store.recover()
        yield

    app = FastAPI(title="SkillsBridge Evidence API", version="2.0.0", lifespan=lifespan,
        description="Evidence assessments with grounded findings. Single-workspace prototype. Configure X-API-Key before exposing beyond localhost.")
    origins = [s.strip() for s in os.getenv("CORS_ORIGINS", "").split(",") if s.strip()]
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Content-Type", "X-API-Key"])

    async def authorize(key: str | None = Security(api_key_header)):
        expected = os.getenv("SKILLSBRIDGE_API_KEY")
        if expected and (not key or not hmac.compare_digest(key, expected)):
            raise HTTPException(401, "A valid X-API-Key header is required.")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        if request.headers.get("content-length", "0").isdigit() and int(request.headers.get("content-length", "0")) > 250000:
            return JSONResponse({"detail": "Request exceeds 250 KB."}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/v2") else "no-cache"
        if not request.url.path.startswith(("/docs", "/redoc")):
            response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        return response

    from .baselines import router
    app.include_router(router(authorize))
    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

    @app.get("/", include_in_schema=False)
    async def home():
        return FileResponse(ROOT / "static" / "index.html")

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "2.0.0"}

    @app.get("/v2/capabilities", dependencies=[Depends(authorize)])
    async def capabilities():
        config = semantic_configuration()
        return {"semantic_evaluator": config["configured"],
            "semantic_provider": config["provider"], "semantic_model": config["model_tag"],
            "offline_evaluator": True, "auth_required": bool(os.getenv("SKILLSBRIDGE_API_KEY")),
            "schema_version": SCHEMA_VERSION, "rubric_version": RUBRIC_VERSION,
            "roles": ["junior_backend", "junior_frontend", "junior_data"],
            "model": model_status(model_dir)}

    async def run_assessment(key, profile):
        async with semaphore:
            store.update(key, status="processing")
            try:
                report = await evaluate(profile)
                report = await asyncio.to_thread(predict_report, report, model_dir)
                store.update(key, status="completed", report=report)
            except Exception as error:
                logger.warning("Assessment %s failed (%s)", key, type(error).__name__)
                message = "Assessment could not be completed. Check evaluator configuration or retry in offline mode."
                if isinstance(error, httpx.HTTPStatusError):
                    message = f"Evaluator provider returned HTTP {error.response.status_code}. Check configuration or retry later."
                store.update(key, status="failed", error=message)

    @app.post("/v2/assessments", status_code=202, response_model=JobCreated, dependencies=[Depends(authorize)])
    async def create_assessment(profile: AssessmentRequest, tasks: BackgroundTasks):
        key = str(uuid4())
        store.insert(key, datetime.now(timezone.utc).isoformat(), profile.model_dump(mode="json"))
        tasks.add_task(run_assessment, key, profile)
        return {"id": key, "status": "queued", "status_url": f"/v2/assessments/{key}"}

    @app.get("/v2/assessments", dependencies=[Depends(authorize)])
    async def list_assessments():
        return {"items": store.list()}

    def get_record(key):
        item = store.get(key)
        if not item:
            raise HTTPException(404, "Assessment not found.")
        return item

    @app.get("/v2/assessments/{key}", response_model=JobStatus, dependencies=[Depends(authorize)])
    async def get_assessment(key: str):
        item = get_record(key)
        return {field: item[field] for field in ["id", "created_at", "status", "error", "review_note"]} | {
            "student_name": item["payload"]["student_name"], "target_role": item["payload"]["target_role"]}

    @app.get("/v2/assessments/{key}/report", response_model=AssessmentReport, dependencies=[Depends(authorize)])
    async def get_report(key: str):
        item = get_record(key)
        if item["status"] != "completed":
            raise HTTPException(409, f"Report is not ready: {item['status']}.")
        return {"id": key, "student_name": item["payload"]["student_name"],
            "target_role": item["payload"]["target_role"], "created_at": item["created_at"], **item["report"]}

    @app.post("/v2/assessments/{key}/reviews", status_code=201, dependencies=[Depends(authorize)])
    async def request_review(key: str, review: ReviewRequest):
        get_record(key)
        store.update(key, review_note=review.note)
        return {"status": "requested", "note": review.note}

    @app.delete("/v2/assessments/{key}", status_code=204, dependencies=[Depends(authorize)])
    async def delete_assessment(key: str):
        get_record(key)
        store.delete(key)

    @app.get("/v2/example", dependencies=[Depends(authorize)])
    async def example():
        return json.loads((ROOT / "fixtures" / "example.json").read_text(encoding="utf-8"))

    @app.post("/v2/standardize", dependencies=[Depends(authorize)])
    async def standardize_measurements(profile: AssessmentRequest):
        from .standardize import standardize
        try:
            return await standardize(profile)
        except Exception:
            raise HTTPException(422, "Measurement extraction failed validation. Supply source measurements manually or retry with clearer evidence.")

    @app.post("/v2/assessments/{key}/standardize", dependencies=[Depends(authorize)])
    async def standardize_saved_assessment(key: str):
        from .standardize import standardize
        item = get_record(key)
        if item["status"] != "completed":
            raise HTTPException(409, "Complete the evidence assessment first.")
        try:
            result = await standardize(AssessmentRequest.model_validate(item["payload"]))
        except Exception:
            raise HTTPException(422, "Extraction could not be validated. No estimated measurements were substituted.")
        report = item["report"]
        report["standardized_inputs"] = result
        store.update(key, report=report)
        return result

    @app.post("/v2/import/github", dependencies=[Depends(authorize)])
    async def github_import(body: GitHubRequest):
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "SkillsBridge-evidence-prototype"}
        if os.getenv("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
        # Fixed upstream; never fetch arbitrary URLs supplied by users.
        url = f"https://api.github.com/repos/{body.repository}/readme"
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
                response = await client.get(url, headers=headers)
            if response.status_code != 200:
                raise HTTPException(502, f"GitHub returned HTTP {response.status_code}. Check repository visibility or try later.")
            import base64
            data = response.json()
            if data.get("size", 0) > 100000:
                raise HTTPException(422, "README exceeds the prototype import limit.")
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")[:22000]
            return {"evidence": Evidence(kind="project", title=body.repository, content=content,
                    source_url=f"https://github.com/{body.repository}").model_dump(mode="json"),
                "scope": "README only; implementation, tests, authorship, and deployment are not verified.", "source_sha": data.get("sha")}
        except httpx.HTTPError:
            raise HTTPException(502, "GitHub could not be reached. Retry or paste evidence manually.")

    return app


app = create_app()
