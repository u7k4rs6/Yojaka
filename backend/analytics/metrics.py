from __future__ import annotations

from typing import Literal, Optional

CERTAINTY_MARKERS = {"definitely", "certainly", "proven", "must", "always"}
SUPPORT_MARKERS   = {"support", "agree", "benefit", "advantage"}
OPPOSE_MARKERS    = {"oppose", "disagree", "flaw", "risk", "however"}
EVIDENCE_MARKERS  = {"because", "data", "study", "research", "observed"}
REBUTTAL_MARKERS  = {"however", "flaw", "counter", "unless"}

ROLE_WEIGHTS: dict[str, float] = {
    "lead_advocate":      1.0,
    "rebuttal_critic":    1.1,
    "evidence_researcher": 1.15,
    "cross_examiner":     1.05,
}


def _words(text: str) -> set[str]:
    return {w.lower().strip(".,!?;:\"'()[]") for w in text.split() if w}


def compute_confidence(text: str, base: float = 0.5) -> float:
    words = _words(text)
    count = sum(1 for m in CERTAINTY_MARKERS if m in words)
    raw = base + count * 0.05
    return max(0.2, min(1.25, raw))


def compute_novelty(text: str, prior_texts: list[str]) -> float:
    if not prior_texts:
        return 1.0
    current = _words(text)
    prior   = _words(" ".join(prior_texts))
    union        = current | prior
    intersection = current & prior
    if not union:
        return 1.0
    return 1.0 - len(intersection) / len(union)


def detect_stance(
    text: str,
    role: Optional[str] = None,
) -> Literal["Support", "Oppose", "Mixed"]:
    words = _words(text)
    support_count = sum(1 for m in SUPPORT_MARKERS if m in words)
    oppose_count  = sum(1 for m in OPPOSE_MARKERS  if m in words)
    if support_count > oppose_count:
        return "Support"
    if oppose_count > support_count:
        return "Oppose"
    return "Mixed"


def detect_evidence(text: str) -> bool:
    words = _words(text)
    return any(m in words for m in EVIDENCE_MARKERS)


def detect_rebuttal(text: str) -> bool:
    words = _words(text)
    return any(m in words for m in REBUTTAL_MARKERS)
