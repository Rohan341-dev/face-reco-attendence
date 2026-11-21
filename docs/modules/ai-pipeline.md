# AI pipeline

Separate FastAPI service under `ai/`. It is internal-only (shared service
token) and returns verification signals, never attendance decisions.

Stages (`ai/app/pipeline/`):

1. `capture` — decode and size-check the base64 image; require an explicit
   `capture_consent` flag. No frame is written to disk or retained.
2. `detection` — YuNet when `AI_DETECTOR_MODEL_PATH` is set, otherwise the
   OpenCV Haar cascade bundled with OpenCV.
3. `quality` — sharpness, brightness and face-size score.
4. `liveness` — passive single-frame texture heuristic, explicitly marked
   `certified_pad: false`. Not a PAD system.
5. `embedding` — `stub` (deterministic, non-biometric, tests/dev only) or
   `insightface` ArcFace with locally provisioned weights.
6. `verification` — cosine similarity against candidate templates, compared to
   `RECOGNITION_THRESHOLD`.

Responses include `eligible_for_attendance: false`. The Django engine performs
the actual authorization after consent, device, schedule and duplicate checks.

See `docs/ai/evaluation/INITIAL_REPORT.md`: no evaluation has been performed
and no accuracy is claimed. Thresholds are provisional.
