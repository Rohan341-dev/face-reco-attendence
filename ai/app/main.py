"""FaceTrack AI service.

Internal-only API. No raw images are stored and no attendance decision is made
here: results are verification signals consumed by the Django attendance engine.
"""

from __future__ import annotations

import hmac

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import Settings, get_settings
from app.pipeline.service import enroll, verify
from app.pipeline.stages import PipelineError
from app.schemas import (
    EnrollRequest,
    EnrollResponse,
    HealthResponse,
    VerifyRequest,
    VerifyResponse,
)

app = FastAPI(title="FaceTrack AI Service", version="0.1.0")


@app.exception_handler(PipelineError)
async def pipeline_error_handler(_: Request, exc: PipelineError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"status": 422, "code": exc.code, "stage": exc.stage, "detail": exc.message}},
    )


def require_internal_token(
    x_internal_token: str = Header(default="", alias="X-Internal-Token"),
    settings: Settings = Depends(get_settings),
) -> None:
    if not hmac.compare_digest(x_internal_token, settings.service_token):
        raise HTTPException(status_code=401, detail="Invalid internal service token.")


@app.get("/healthz", response_model=HealthResponse)
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        embedding_backend=settings.embedding_backend,
        model_version=settings.embedding_model_name,
        recognition_threshold=settings.recognition_threshold,
    )


@app.post(
    "/v1/biometric/enroll",
    response_model=EnrollResponse,
    dependencies=[Depends(require_internal_token)],
)
def enroll_endpoint(body: EnrollRequest, settings: Settings = Depends(get_settings)) -> EnrollResponse:
    return enroll(body.image_b64, body.capture_consent, settings)


@app.post(
    "/v1/attendance/verify",
    response_model=VerifyResponse,
    dependencies=[Depends(require_internal_token)],
)
def verify_endpoint(body: VerifyRequest, settings: Settings = Depends(get_settings)) -> VerifyResponse:
    return verify(
        body.image_b64,
        body.capture_consent,
        body.candidate_templates_b64,
        body.person_ids,
        settings,
    )
