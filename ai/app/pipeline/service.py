"""Authorized capture → detect → quality → liveness → embedding → verification.

The service reports a verification signal only. It never marks attendance as
eligible: the Django attendance engine makes that decision after checking
consent, device authorization, shift and leave state.
"""

from __future__ import annotations

import base64

import numpy as np

from app.config import Settings
from app.schemas import EnrollResponse, VerifyResponse

from .stages import (
    PipelineError,
    assess_liveness,
    assess_quality,
    cosine_similarity,
    crop_face,
    decode_image,
    detect_face,
    generate_embedding,
)


def _prepare(image_b64: str, settings: Settings):
    image = decode_image(image_b64, settings)
    detection = detect_face(image, settings)
    if not detection.detected or detection.bbox is None:
        return image, detection, None, None, None, ["no_face_detected"]
    face = crop_face(image, detection.bbox)
    quality = assess_quality(face, settings)
    liveness = assess_liveness(face, settings)
    reasons: list[str] = []
    if not quality.passed:
        reasons.append("poor_quality")
    if not liveness.passed:
        reasons.append("liveness_not_passed")
    return image, detection, face, quality, liveness, reasons


def enroll(image_b64: str, capture_consent: bool, settings: Settings) -> EnrollResponse:
    if not capture_consent:
        raise PipelineError("consent_required", "Authorized capture consent is required.", "capture")
    _, detection, face, quality, liveness, reasons = _prepare(image_b64, settings)
    if face is None or quality is None or liveness is None:
        return EnrollResponse(
            status="rejected",
            model_version=settings.embedding_model_name,
            detection=detection,
            quality=quality or _empty_quality(settings),
            liveness=liveness or _empty_liveness(settings),
            reasons=reasons,
        )
    if not quality.passed or not liveness.passed:
        return EnrollResponse(
            status="rejected",
            model_version=settings.embedding_model_name,
            detection=detection,
            quality=quality,
            liveness=liveness,
            reasons=reasons,
        )
    embedding = generate_embedding(face, settings)
    return EnrollResponse(
        status="accepted",
        template_b64=base64.b64encode(embedding.tobytes()).decode("ascii"),
        model_version=settings.embedding_model_name,
        detection=detection,
        quality=quality,
        liveness=liveness,
        reasons=reasons,
    )


def verify(
    image_b64: str,
    capture_consent: bool,
    candidate_templates_b64: list[str],
    person_ids: list[str],
    settings: Settings,
) -> VerifyResponse:
    if not capture_consent:
        raise PipelineError("consent_required", "Authorized capture consent is required.", "capture")
    _, detection, face, quality, liveness, reasons = _prepare(image_b64, settings)
    common = {
        "threshold": settings.recognition_threshold,
        "model_version": settings.embedding_model_name,
        "detection": detection,
        "quality": quality or _empty_quality(settings),
        "liveness": liveness or _empty_liveness(settings),
        "reasons": list(reasons),
    }
    if face is None or quality is None or liveness is None:
        return VerifyResponse(status="rejected", matched=False, **common)
    if not quality.passed or not liveness.passed:
        return VerifyResponse(status="rejected", matched=False, **common)

    probe = generate_embedding(face, settings)
    best_score = 0.0
    best_index: int | None = None
    for index, encoded in enumerate(candidate_templates_b64):
        try:
            raw = base64.b64decode(encoded, validate=True)
        except Exception:  # noqa: BLE001
            common["reasons"].append("invalid_template")
            continue
        candidate = np.frombuffer(raw, dtype=np.float32)
        if candidate.size != probe.size:
            common["reasons"].append("template_dimension_mismatch")
            continue
        score = cosine_similarity(probe, candidate)
        if score > best_score:
            best_score, best_index = score, index

    matched = best_index is not None and best_score >= settings.recognition_threshold
    person_id = person_ids[best_index] if matched and best_index < len(person_ids) else None
    if not matched:
        common["reasons"].append("below_threshold")
    return VerifyResponse(
        status="verified_face" if matched else "rejected",
        matched=matched,
        person_id=person_id,
        score=best_score if best_index is not None else None,
        **common,
    )


def _empty_quality(settings: Settings):
    from app.schemas import QualityResult

    return QualityResult(score=0.0, sharpness=0.0, brightness=0.0, passed=False)


def _empty_liveness(settings: Settings):
    from app.schemas import LivenessResult

    return LivenessResult(score=0.0, passed=False, method="none", certified_pad=False)
