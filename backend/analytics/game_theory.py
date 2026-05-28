from __future__ import annotations


def compute_nash_pressure(pro_score: float, con_score: float) -> float:
    raw = abs(pro_score - con_score) / (pro_score + con_score + 0.001)
    return max(0.0, min(1.0, raw))
