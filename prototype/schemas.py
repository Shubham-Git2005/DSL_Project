from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EvidenceKind(StrEnum):
    PROJECT = "project"
    INTERNSHIP = "internship"
    CERTIFICATION = "certification"
    CODING = "coding"
    COMMUNICATION = "communication"


class Evidence(StrictModel):
    kind: EvidenceKind
    title: str = Field(min_length=2, max_length=160)
    content: str = Field(min_length=20, max_length=24000)
    source_url: HttpUrl | None = None


class AssessmentRequest(StrictModel):
    student_name: str = Field(min_length=2, max_length=100)
    target_role: Literal["junior_backend", "junior_frontend", "junior_data"] = "junior_backend"
    cgpa: float | None = Field(default=None, ge=0, le=10)
    communication_score: float | None = Field(default=None, ge=0, le=100)
    coding_score: float | None = Field(default=None, ge=0, le=100)
    evidence: list[Evidence] = Field(default_factory=list, max_length=12)
    evaluator: Literal["auto", "offline", "llm"] = "auto"
    dataset_origin: Literal["user_supplied", "synthetic_example"] = "user_supplied"

    @model_validator(mode="after")
    def bound_total(self):
        if sum(len(item.content) for item in self.evidence) > 72000:
            raise ValueError("Total evidence must not exceed 72,000 characters.")
        return self


class Finding(StrictModel):
    dimension: Literal["implementation", "testing", "delivery", "ownership", "relevance", "assessment", "communication"]
    category: Literal["supported", "partial", "not_demonstrated", "unknown"]
    explanation: str = Field(min_length=5, max_length=700)
    quote: str = Field(default="", max_length=700)


class ArtifactAssessment(StrictModel):
    title: str = Field(max_length=160)
    kind: EvidenceKind
    summary: str = Field(min_length=5, max_length=1000)
    findings: list[Finding] = Field(min_length=1, max_length=7)
    level: Literal["foundation", "applied", "independent", "advanced", "unknown"] = "unknown"
    level_reason: str = Field(default="Insufficient assessed evidence to assign a level.", max_length=700)
    level_quote: str = Field(default="", max_length=700)


class ReviewRequest(StrictModel):
    note: str = Field(min_length=10, max_length=2000)


class GitHubRequest(StrictModel):
    repository: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}$")

    @model_validator(mode="after")
    def no_path_segments(self):
        if self.repository.split("/")[1] in {".", ".."}:
            raise ValueError("A repository name cannot be a relative path segment.")
        return self


class JobCreated(BaseModel):
    id: str
    status: Literal["queued"]
    status_url: str


class JobStatus(BaseModel):
    id: str
    created_at: str
    status: Literal["queued", "processing", "completed", "failed"]
    error: str | None
    review_note: str | None
    student_name: str
    target_role: str


class ReadinessResult(BaseModel):
    status: Literal["unavailable", "experimental"]
    label: str | None
    probabilities: dict[str, float] | None
    reason: str
    model_name: str | None = None


class ArtifactReport(ArtifactAssessment):
    evidence_id: str
    source_type: str
    independently_verified: bool
    source_url: str | None
    content_sha256: str


class AssessmentReport(BaseModel):
    id: str
    student_name: str
    target_role: str
    created_at: str
    dataset_origin: str
    evaluator: Literal["offline", "llm"]
    evaluator_model: str
    rubric_version: str
    features: dict[str, str | float | int | None]
    evidence_status: str
    supported_dimensions: int
    total_dimensions: int
    artifacts: list[ArtifactReport]
    next_steps: list[str]
    readiness: ReadinessResult
    limitations: list[str]
    standardized_inputs: dict | None = None


NUMERIC_FEATURES = ["cgpa", "communication_score", "coding_score", "evidence_count"]
CATEGORICAL_FEATURES = ["target_role", "implementation", "testing", "delivery", "ownership", "relevance", "assessment", "communication"]
CATEGORICAL_FEATURES += ["project_level", "internship_level", "certification_level", "coding_level", "communication_level"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
LABELS = ["foundation_developing", "developing_independence", "entry_level_ready"]
SCHEMA_VERSION = "evidence-v2"
RUBRIC_VERSION = "role-rubric-1.1"
LEVELS = ["unknown", "foundation", "applied", "independent", "advanced"]
