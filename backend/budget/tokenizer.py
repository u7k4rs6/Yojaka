from __future__ import annotations

import unicodedata


def count_cjk(text: str) -> int:
    """Count CJK (Chinese/Japanese/Korean) characters in text."""
    return sum(1 for c in text if unicodedata.east_asian_width(c) in ("W", "F"))


def estimate_tokens(text: str) -> int:
    """
    CJK chars: 1.6 chars/token
    Latin/other: 1.3 chars/token
    Returns floor, minimum 1.
    """
    if not text:
        return 1
    cjk  = count_cjk(text)
    rest = len(text) - cjk
    tokens = int(cjk / 1.6) + int(rest / 1.3)
    return max(1, tokens)


def count_tokens(text: str) -> int:
    """Same formula as estimate_tokens; used for post-generation counting."""
    return estimate_tokens(text)
