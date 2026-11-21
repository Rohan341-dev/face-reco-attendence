from __future__ import annotations

import base64

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.evaluation.harness import ScoredPair, evaluate
from app.main import app
from app.pipeline import service
from app.schemas import DetectionResult, LivenessResult, QualityResult

client = TestClient(app)


def override_settings() -> Settings:
    return Settings(service_token="test-token", recognition_threshold=0.8, embedding_backend="stub")


@pytest.fixture(autouse=True)
def _settings():
    app.dependency_overrides[get_settings] = override_settings
    yield
    app.dependency_overrides.clear()


def fake_prepare(image_b64, settings):
    detection = DetectionResult(detected=True, bbox=[0, 0, 100, 100], detector="test")
    quality = QualityResult(score=0.9, sharpness=500.0, brightness=0.5, passed=True)
    liveness = LivenessResult(score=0.9, passed=True, method="test", certified_pad=False)
    face = np.zeros((100, 100, 3), dtype=np.uint8)
    return None, detection, face, quality, liveness, []


def test_health_and_auth():
    assert client.get("/healthz").json()["status"] == "ok"
    assert client.post("/v1/attendance/verify", json={"image_b64": "x"}).status_code == 401


def test_consent_is_required(monkeypatch):
    monkeypatch.setattr(service, "_prepare", fake_prepare)
    response = client.post(
        "/v1/attendance/verify",
        headers={"X-Internal-Token": "test-token"},
        json={"image_b64": "AAAA", "capture_consent": False},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "consent_required"


def test_verify_returns_signal_not_authorization(monkeypatch):
    monkeypatch.setattr(service, "_prepare", fake_prepare)
    vector = np.zeros(128, dtype=np.float32)
    vector[0] = 1.0
    monkeypatch.setattr(service, "generate_embedding", lambda face, settings: vector)
    template = base64.b64encode(vector.tobytes()).decode()

    response = client.post(
        "/v1/attendance/verify",
        headers={"X-Internal-Token": "test-token"},
        json={
            "image_b64": "AAAA",
            "capture_consent": True,
            "candidate_templates_b64": [template],
            "person_ids": ["person-1"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["matched"] is True
    assert body["status"] == "verified_face"
    assert body["person_id"] == "person-1"
    assert body["eligible_for_attendance"] is False


def test_below_threshold_is_rejected(monkeypatch):
    monkeypatch.setattr(service, "_prepare", fake_prepare)
    probe = np.zeros(128, dtype=np.float32)
    probe[0] = 1.0
    candidate = np.zeros(128, dtype=np.float32)
    candidate[1] = 1.0
    monkeypatch.setattr(service, "generate_embedding", lambda face, settings: probe)
    template = base64.b64encode(candidate.tobytes()).decode()

    response = client.post(
        "/v1/attendance/verify",
        headers={"X-Internal-Token": "test-token"},
        json={
            "image_b64": "AAAA",
            "capture_consent": True,
            "candidate_templates_b64": [template],
            "person_ids": ["person-1"],
        },
    )
    assert response.status_code == 200
    assert response.json()["matched"] is False


def test_harness_reports_descriptive_metrics():
    pairs = [ScoredPair(True, 0.9), ScoredPair(True, 0.2), ScoredPair(False, 0.1), ScoredPair(False, 0.95)]
    result = evaluate(pairs, 0.5)
    assert result["tar"] == 0.5
    assert result["far"] == 0.5
    assert result["samples"] == 4
