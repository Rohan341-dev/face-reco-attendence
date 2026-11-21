"""Threshold evaluation harness.

Usage:
    python -m app.evaluation.harness --pairs pairs.json --threshold 0.45

pairs.json is a list of {"label": true|false, "score": 0.0..1.0} where label
true means "same identity". Metrics are descriptive only: they describe the
supplied sample, not a claimed production accuracy figure.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScoredPair:
    label: bool
    score: float


def evaluate(pairs: list[ScoredPair], threshold: float) -> dict[str, float | int]:
    tp = sum(1 for pair in pairs if pair.label and pair.score >= threshold)
    fn = sum(1 for pair in pairs if pair.label and pair.score < threshold)
    fp = sum(1 for pair in pairs if not pair.label and pair.score >= threshold)
    tn = sum(1 for pair in pairs if not pair.label and pair.score < threshold)
    total = len(pairs) or 1
    return {
        "samples": len(pairs),
        "threshold": threshold,
        "true_accepts": tp,
        "false_rejects": fn,
        "false_accepts": fp,
        "true_rejects": tn,
        "tar": round(tp / (tp + fn), 4) if tp + fn else 0.0,
        "far": round(fp / (fp + tn), 4) if fp + tn else 0.0,
        "frr": round(fn / (tp + fn), 4) if tp + fn else 0.0,
        "descriptive_accuracy": round((tp + tn) / total, 4),
    }


def main() -> None:  # pragma: no cover - CLI entry point
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=Path, required=True)
    parser.add_argument("--threshold", type=float, required=True)
    args = parser.parse_args()
    raw = json.loads(args.pairs.read_text())
    pairs = [ScoredPair(label=bool(item["label"]), score=float(item["score"])) for item in raw]
    result = evaluate(pairs, args.threshold)
    result["note"] = "Descriptive metrics for the supplied sample only; not a production accuracy claim."
    print(json.dumps(result, indent=2))
