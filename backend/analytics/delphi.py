from __future__ import annotations

import math


def compute_delphi_variance(scores: list[float]) -> float:
    if len(scores) < 2:
        return 0.0
    n    = len(scores)
    mean = sum(scores) / n
    variance = sum((s - mean) ** 2 for s in scores) / n
    return math.sqrt(variance)
