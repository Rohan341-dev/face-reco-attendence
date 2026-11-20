from __future__ import annotations

from pydantic import BaseModel, Field


class VerifyRequest(BaseModel):
    image_b64: str
    candidate_templates_b64: list[str] = Field(default_factory=list)
    person_ids: list[str] = Field(default_factory=list)
    capture_consent: bool = False
    metadata: dict = Field(default_factory=dict)


class EnrollRequest(BaseModel):
    image_b64: str
    capture_consent: bool = False
    metadata: dict = Field(default_factory=dict)


class DetectionResult(BaseModel):
    detected: bool
    bbox: list[int] | None = None
    detector: str


class QualityResult(BaseModel):
    score: float
    sharpness: float
    brightness: float
    passed: bool


class LivenessResult(BaseModel):
    score: float
    passed: bool
    method: str
    certified_pad: bool = False


class EnrollResponse(BaseModel):
    status: str
    template_b64: str | None = None
    model_version: str
    detection: DetectionResult
    quality: QualityResult
    liveness: LivenessResult
    reasons: list[str] = Field(default_factory=list)


class VerifyResponse(BaseModel):
    status: str
    matched: bool
    person_id: str | None = None
    score: float | None = None
    threshold: float
    model_version: str
    detection: DetectionResult
    quality: QualityResult
    liveness: LivenessResult
    reasons: list[str] = Field(default_factory=list)
    eligible_for_attendance: bool = False
    eligibility_note: str = "Eligibility is decided by the attendance engine, not by this service."


class HealthResponse(BaseModel):
    status: str
    embedding_backend: str
    model_version: str
    recognition_threshold: float
    accuracy_claims: bool = False
