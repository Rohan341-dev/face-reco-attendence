"""Pipeline stage implementations.

Each stage is independent and returns a structured result. Stages never write
images to disk and never retain frames after the request ends.
"""

from __future__ import annotations

import hashlib

import cv2
import numpy as np

from app.config import Settings
from app.schemas import DetectionResult, LivenessResult, QualityResult


class PipelineError(Exception):
    def __init__(self, code: str, message: str, stage: str):
        super().__init__(message)
        self.code = code
        self.message = message
        self.stage = stage


def decode_image(image_b64: str, settings: Settings) -> np.ndarray:
    import base64

    if len(image_b64) > settings.max_image_bytes:
        raise PipelineError("image_too_large", "Image exceeds the configured size limit.", "capture")
    try:
        raw = base64.b64decode(image_b64, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise PipelineError("invalid_image", "Image is not valid base64.", "capture") from exc
    array = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None or image.size == 0:
        raise PipelineError("invalid_image", "Image could not be decoded.", "capture")
    return image


def detect_face(image: np.ndarray, settings: Settings) -> DetectionResult:
    if settings.detector_model_path:
        try:
            detector = cv2.FaceDetectorYN.create(
                settings.detector_model_path, "", (image.shape[1], image.shape[0])
            )
            _, faces = detector.detect(image)
            if faces is not None and len(faces):
                x, y, width, height = (int(value) for value in faces[0][:4])
                return DetectionResult(
                    detected=True,
                    bbox=[x, y, width, height],
                    detector="yunet",
                )
            return DetectionResult(detected=False, detector="yunet")
        except Exception as exc:  # noqa: BLE001
            raise PipelineError("detector_unavailable", f"YuNet detector failed: {exc}", "detection") from exc

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4)
    if len(faces) == 0:
        return DetectionResult(detected=False, detector="opencv-haar")
    x, y, width, height = (int(value) for value in faces[0])
    return DetectionResult(detected=True, bbox=[x, y, width, height], detector="opencv-haar")


def crop_face(image: np.ndarray, bbox: list[int]) -> np.ndarray:
    x, y, width, height = bbox
    height, width_total = image.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(width_total, x + width), min(height, y + height)
    crop = image[y0:y1, x0:x1]
    if crop.size == 0:
        raise PipelineError("empty_crop", "Face crop is empty.", "detection")
    return crop


def assess_quality(face: np.ndarray, settings: Settings) -> QualityResult:
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray)) / 255.0
    sharpness_score = min(1.0, sharpness / 500.0)
    brightness_score = 1.0 - min(1.0, abs(brightness - 0.5) * 2)
    size_score = min(1.0, min(face.shape[:2]) / max(1, settings.min_face_size))
    score = round(0.5 * sharpness_score + 0.25 * brightness_score + 0.25 * size_score, 4)
    return QualityResult(
        score=score,
        sharpness=round(sharpness, 3),
        brightness=round(brightness, 4),
        passed=score >= settings.quality_threshold,
    )


def assess_liveness(face: np.ndarray, settings: Settings) -> LivenessResult:
    """Passive single-frame texture heuristic.

    This is NOT a certified presentation attack detection (PAD) system. It is a
    cheap gate for obviously flat/blank inputs. Production deployments must
    plug in an independently evaluated PAD model before enabling face-based
    attendance. See docs/ai/evaluation/INITIAL_REPORT.md.
    """
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    texture = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    score = round(min(1.0, texture / 400.0), 4)
    return LivenessResult(
        score=score,
        passed=score >= settings.liveness_threshold,
        method="single-frame-texture-heuristic",
        certified_pad=False,
    )


def stub_embedding(face: np.ndarray, settings: Settings) -> np.ndarray:
    """Deterministic non-biometric embedding for development and tests.

    It is derived from a downscaled grayscale crop and is NOT a face
    recognition model. It exists so the pipeline can be exercised without
    downloaded weights. Never use it for production identification.
    """
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (16, 16), interpolation=cv2.INTER_AREA)
    values = small.astype(np.float32).flatten() / 255.0
    digest = hashlib.sha256(values.tobytes()).digest()
    seed = int.from_bytes(digest[:8], "big")
    rng = np.random.default_rng(seed)
    vector = rng.normal(size=settings.embedding_dim).astype(np.float32)
    vector = np.concatenate([values[: settings.embedding_dim], vector])[: settings.embedding_dim]
    norm = float(np.linalg.norm(vector)) or 1.0
    return vector / norm


def insightface_embedding(face: np.ndarray, settings: Settings) -> np.ndarray:
    try:
        from insightface.app import FaceAnalysis
    except ImportError as exc:  # pragma: no cover
        raise PipelineError("model_unavailable", "insightface is not installed.", "embedding") from exc
    app = FaceAnalysis(name=settings.embedding_model_name)
    app.prepare(ctx_id=-1)
    faces = app.get(face)
    if not faces:
        raise PipelineError("no_embedding", "No embedding could be produced.", "embedding")
    vector = np.asarray(faces[0].embedding, dtype=np.float32)
    norm = float(np.linalg.norm(vector)) or 1.0
    return vector / norm


def generate_embedding(face: np.ndarray, settings: Settings) -> np.ndarray:
    if settings.embedding_backend == "stub":
        return stub_embedding(face, settings)
    if settings.embedding_backend == "insightface":
        return insightface_embedding(face, settings)
    raise PipelineError("unknown_backend", "Unknown embedding backend.", "embedding")


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    if left.shape != right.shape:
        return 0.0
    return round(float(np.dot(left, right) / ((np.linalg.norm(left) * np.linalg.norm(right)) or 1.0)), 4)
