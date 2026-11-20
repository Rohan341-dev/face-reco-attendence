from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AI_", env_file="../.env", extra="ignore")

    service_token: str = "dev-ai-token-change-me"
    recognition_threshold: float = Field(default=0.45, validation_alias="RECOGNITION_THRESHOLD")
    liveness_threshold: float = Field(default=0.70, validation_alias="LIVENESS_THRESHOLD")
    quality_threshold: float = 0.35
    min_face_size: int = 64
    max_image_bytes: int = 5_000_000

    # YuNet ONNX detector. When unset, the OpenCV Haar cascade shipped with
    # opencv-python is used so the pipeline runs without downloaded weights.
    detector_model_path: str = ""

    # "stub" is deterministic and for development/tests only. "insightface"
    # requires local ArcFace weights; no weights are committed to this repo.
    embedding_backend: str = "stub"
    embedding_model_name: str = "stub-deterministic-v1"
    embedding_dim: int = 128


@lru_cache
def get_settings() -> Settings:
    return Settings()
