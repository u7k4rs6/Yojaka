from __future__ import annotations

import logging
import re
from typing import Optional, TYPE_CHECKING

from fastapi import HTTPException

if TYPE_CHECKING:
    from providers.utility_tier import UtilityTier

logger = logging.getLogger(__name__)

BLOCKED_PATTERNS = [
    r"\b(how\s+to\s+(make|build|create)\s+(bomb|weapon|explosive|poison))\b",
    r"\b(suicide\s+method|how\s+to\s+kill\s+(myself|yourself))\b",
    r"\b(child\s+(porn|abuse|sexual))\b",
    r"\b(hack\s+(password|account|bank))\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in BLOCKED_PATTERNS]


class SafetyGuard:
    def __init__(self, utility_tier: Optional[UtilityTier] = None) -> None:
        self._utility_tier = utility_tier

    def _regex_blocked(self, text: str) -> bool:
        return any(pat.search(text) for pat in _COMPILED)

    def is_safe(self, text: str) -> bool:
        # Fast path: regex check
        if self._regex_blocked(text):
            return False

        # LLM fallback when a utility tier is available
        if self._utility_tier is not None:
            import asyncio
            from prompts.safety.classifier import SAFETY_PROMPT

            prompt = SAFETY_PROMPT.format(topic=text)
            try:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = None

                if loop and loop.is_running():
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(asyncio.run, self._utility_tier.ask_yes_no(prompt))
                        answer = future.result(timeout=10)
                else:
                    answer = asyncio.run(self._utility_tier.ask_yes_no(prompt))

                return answer == "YES"
            except Exception as exc:
                logger.warning(
                    "SafetyGuard: LLM classifier failed (%s); falling back to regex-only result",
                    exc,
                    extra={"diary": "safety_lock_classifier_fallback"},
                )
                # Regex already passed — treat as safe
                return True

        return True

    def check(self, text: str) -> None:
        if not self.is_safe(text):
            raise HTTPException(
                status_code=400,
                detail="Topic blocked by safety filter.",
            )
