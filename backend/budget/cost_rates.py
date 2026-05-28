from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx

from core.schemas import CostRate

if TYPE_CHECKING:
    pass

# ─── Local fallback rates (per 1M tokens, USD) ────────────────────────────────

LOCAL_FALLBACK_RATES: dict[str, CostRate] = {
    # Google
    "gemini-3.1-pro":       CostRate(model="gemini-3.1-pro",       provider="google",     input_rate_per_1m=3.50,   output_rate_per_1m=10.50,  pricing_available=True,  source="local_fallback"),
    "gemini-3-flash":       CostRate(model="gemini-3-flash",       provider="google",     input_rate_per_1m=0.075,  output_rate_per_1m=0.30,   pricing_available=True,  source="local_fallback"),
    "gemini-2.5-flash-lite":CostRate(model="gemini-2.5-flash-lite",provider="google",     input_rate_per_1m=0.03,   output_rate_per_1m=0.10,   pricing_available=True,  source="local_fallback"),
    "gemini-2.0-flash":     CostRate(model="gemini-2.0-flash",     provider="google",     input_rate_per_1m=0.10,   output_rate_per_1m=0.40,   pricing_available=True,  source="local_fallback"),
    # Groq
    "llama-3.1-8b-instant": CostRate(model="llama-3.1-8b-instant", provider="groq",       input_rate_per_1m=0.05,   output_rate_per_1m=0.08,   pricing_available=True,  source="local_fallback"),
    "llama-3.3-70b-versatile": CostRate(model="llama-3.3-70b-versatile", provider="groq", input_rate_per_1m=0.59,  output_rate_per_1m=0.79,   pricing_available=True,  source="local_fallback"),
    # OpenAI
    "gpt-4o":               CostRate(model="gpt-4o",               provider="openai",     input_rate_per_1m=5.00,   output_rate_per_1m=15.00,  pricing_available=True,  source="local_fallback"),
    "gpt-4o-mini":          CostRate(model="gpt-4o-mini",          provider="openai",     input_rate_per_1m=0.15,   output_rate_per_1m=0.60,   pricing_available=True,  source="local_fallback"),
    # Anthropic
    "claude-opus-4-6":      CostRate(model="claude-opus-4-6",      provider="anthropic",  input_rate_per_1m=15.00,  output_rate_per_1m=75.00,  pricing_available=True,  source="local_fallback"),
    "claude-sonnet-4-6":    CostRate(model="claude-sonnet-4-6",    provider="anthropic",  input_rate_per_1m=3.00,   output_rate_per_1m=15.00,  pricing_available=True,  source="local_fallback"),
    "claude-haiku-4-5":     CostRate(model="claude-haiku-4-5",     provider="anthropic",  input_rate_per_1m=0.25,   output_rate_per_1m=1.25,   pricing_available=True,  source="local_fallback"),
    "claude-3.5-sonnet":    CostRate(model="claude-3.5-sonnet",    provider="anthropic",  input_rate_per_1m=3.00,   output_rate_per_1m=15.00,  pricing_available=True,  source="local_fallback"),
    # Moonshot
    "kimi-latest":          CostRate(model="kimi-latest",           provider="moonshot",   input_rate_per_1m=0.60,   output_rate_per_1m=2.50,   pricing_available=True,  source="local_fallback"),
    "kimi-k2-thinking":     CostRate(model="kimi-k2-thinking",      provider="moonshot",   input_rate_per_1m=2.00,   output_rate_per_1m=8.00,   pricing_available=True,  source="local_fallback"),
    "kimi-k2-turbo-preview":CostRate(model="kimi-k2-turbo-preview", provider="moonshot",   input_rate_per_1m=1.00,   output_rate_per_1m=3.00,   pricing_available=True,  source="local_fallback"),
    # OpenRouter Free
    "deepseek-r1-free":     CostRate(model="deepseek-r1-free",     provider="openrouter", input_rate_per_1m=0.0,    output_rate_per_1m=0.0,    pricing_available=True,  source="local_fallback"),
    "qwq-32b-free":         CostRate(model="qwq-32b-free",         provider="openrouter", input_rate_per_1m=0.0,    output_rate_per_1m=0.0,    pricing_available=True,  source="local_fallback"),
    "llama-3.1-8b-free":    CostRate(model="llama-3.1-8b-free",    provider="openrouter", input_rate_per_1m=0.0,    output_rate_per_1m=0.0,    pricing_available=True,  source="local_fallback"),
    "gemma-3-27b-free":     CostRate(model="gemma-3-27b-free",     provider="openrouter", input_rate_per_1m=0.0,    output_rate_per_1m=0.0,    pricing_available=True,  source="local_fallback"),
    "qwen3-14b-free":       CostRate(model="qwen3-14b-free",       provider="openrouter", input_rate_per_1m=0.0,    output_rate_per_1m=0.0,    pricing_available=True,  source="local_fallback"),
    # Mock
    "mock-debate-model":    CostRate(model="mock-debate-model",    provider="mock",       input_rate_per_1m=0.0,    output_rate_per_1m=0.0,    pricing_available=True,  source="local_fallback"),
}


async def fetch_openrouter_pricing(client: httpx.AsyncClient) -> dict[str, CostRate]:
    """Fetch live OpenRouter pricing. Returns empty dict on any failure."""
    try:
        resp = await client.get("https://openrouter.ai/api/v1/models", timeout=10.0)
        resp.raise_for_status()
        data   = resp.json()
        result = {}
        now    = datetime.now(timezone.utc)
        for m in data.get("data", []):
            model_id = m.get("id", "")
            pricing  = m.get("pricing", {})
            try:
                inp  = float(pricing.get("prompt",     0)) * 1_000_000
                out  = float(pricing.get("completion", 0)) * 1_000_000
            except (ValueError, TypeError):
                continue
            result[model_id] = CostRate(
                model=model_id,
                provider="openrouter",
                input_rate_per_1m=inp,
                output_rate_per_1m=out,
                pricing_available=True,
                source="openrouter_api",
                fetched_at=now,
            )
        return result
    except Exception:
        return {}
