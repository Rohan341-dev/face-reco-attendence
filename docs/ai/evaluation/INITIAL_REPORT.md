# AI evaluation status — no accuracy claims

**Status: no evaluation has been performed on real face data. No accuracy,
FAR, FRR or TAR figures are claimed by this project.**

This document exists so that the requirement "no accuracy claims without an
evaluation report in `docs/ai/evaluation/`" is met honestly. It records what is
and is not known about the recognition pipeline.

## What is implemented

- A modular pipeline: authorized capture → detection → quality → liveness →
  embedding → verification.
- Detection via YuNet when a model path is configured, otherwise the OpenCV
  Haar cascade bundled with `opencv-python-headless`.
- Two embedding backends:
  - `stub` (default): a deterministic, **non-biometric** vector used only for
    development and automated tests. It must never be used to identify people.
  - `insightface`: ArcFace embeddings, requiring locally provisioned weights.
    No weights are committed to this repository.
- A passive single-frame texture heuristic labelled `certified_pad: false`.
  **It is not a presentation-attack-detection system.** Production deployments
  must integrate an independently evaluated PAD model before enabling
  face-verified attendance.

## Why thresholds are provisional

`RECOGNITION_THRESHOLD` (default 0.45) and `LIVENESS_THRESHOLD` (default 0.70)
are configuration placeholders. They are not derived from a validation set and
must not be presented as validated operating points.

## Required before any production claim

1. Obtain an appropriate license for the chosen recognition model and record it
   here.
2. Assemble a representative, consented evaluation set covering the deployment
   population, lighting, cameras and attack scenarios.
3. Run `python -m app.evaluation.harness --pairs <pairs.json> --threshold <t>`
   and commit the generated metrics alongside the dataset description.
4. Evaluate presentation attacks separately with an evaluated PAD model.
5. Document FAR/FRR at the selected operating point, demographic breakdowns,
   known limitations, and the decision to enable or disable face attendance per
   tenant.

## Relation to attendance authorization

The AI service returns a verification signal only. The Django attendance
engine decides eligibility after checking active consent, verification status,
device authorization, shifts, leave and duplicate prevention. Detecting or
matching a face never authorizes attendance by itself.
