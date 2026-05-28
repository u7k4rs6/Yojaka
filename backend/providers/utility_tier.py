from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from providers.router import ProviderRouter

logger = logging.getLogger(__name__)


class UtilityTier:
    """Cheap YES/NO and short-completion calls using the fastest available models."""

    PRIORITY = ["llama-3.1-8b-instant", "gemini-2.5-flash-lite"]

    def __init__(self, router: ProviderRouter) -> None:
        self._router = router

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cheapest_model(self) -> str | None:
        """Return the first PRIORITY model whose provider is available."""
        from providers.router import MODEL_TO_PROVIDER  # local to avoid circular at module level

        for model in self.PRIORITY:
            provider_name = MODEL_TO_PROVIDER.get(model)
            if provider_name is None:
                continue
            client = self._router._clients.get(provider_name)
            if client and client.available:
                cached = self._router._health.get(provider_name)
                if cached is not False:
                    return model
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ask_yes_no(
        self,
        prompt: str,
        context: str = "",
    ) -> Literal["YES", "NO"]:
        """Send a YES/NO question using the cheapest available model.

        Returns "NO" on any failure.
        """
        model = self._cheapest_model()
        if model is None:
            logger.warning("UtilityTier.ask_yes_no: no cheap model available, defaulting NO")
            return "NO"

        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        messages = [
            {
                "role": "system",
                "content": "Answer only YES or NO. Do not include any other text.",
            },
            {"role": "user", "content": full_prompt},
        ]

        try:
            provider_name = _model_to_provider(model)
            client = self._router._clients.get(provider_name)
            if client is None:
                return "NO"
            raw = await client.complete(full_prompt, model=model, max_tokens=5)
            raw = raw.strip().upper()
            if "YES" in raw:
                return "YES"
            if "NO" in raw:
                return "NO"
            return "NO"
        except Exception as exc:
            logger.warning("UtilityTier.ask_yes_no error: %s", exc)
            return "NO"

    async def complete(self, prompt: str, max_tokens: int = 120) -> str:
        """Short completion using the cheapest available model."""
        model = self._cheapest_model()
        if model is None:
            logger.warning("UtilityTier.complete: no cheap model available")
            return ""

        try:
            provider_name = _model_to_provider(model)
            client = self._router._clients.get(provider_name)
            if client is None:
                return ""
            return await client.complete(prompt, model=model, max_tokens=max_tokens)
        except Exception as exc:
            logger.warning("UtilityTier.complete error: %s", exc)
            return ""


# ---------------------------------------------------------------------------
# Module-level helper (avoids importing router at the top of the module)
# ---------------------------------------------------------------------------

def _model_to_provider(model: str) -> str:
    from providers.router import MODEL_TO_PROVIDER
    return MODEL_TO_PROVIDER.get(model, "")
