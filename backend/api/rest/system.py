from __future__ import annotations

from fastapi import APIRouter

from config import settings
from storage.database import get_engine

router = APIRouter()

# Active debate count tracked in a module-level set (updated by the orchestrator)
_active_debates: set[str] = set()


def register_active_debate(debate_id: str) -> None:
    _active_debates.add(debate_id)


def unregister_active_debate(debate_id: str) -> None:
    _active_debates.discard(debate_id)


def get_active_debate_count() -> int:
    return len(_active_debates)


@router.get("/health")
async def health():
    db_url = settings.database_url
    return {
        "status":        "ok",
        "db_path":       db_url,
        "active_debates": get_active_debate_count(),
    }


@router.get("/api/models")
async def get_models():
    from providers import MODEL_TO_PROVIDER

    available_providers = set()
    if settings.google_api_key:     available_providers.add("google")
    if settings.groq_api_key:       available_providers.add("groq")
    if settings.openai_api_key:     available_providers.add("openai")
    if settings.anthropic_api_key:  available_providers.add("anthropic")
    if settings.openrouter_api_key: available_providers.add("openrouter")
    if settings.moonshot_api_key:   available_providers.add("moonshot")
    if settings.enable_mock_provider: available_providers.add("mock")

    _labels = {"google": "Google", "groq": "Groq", "openrouter": "OpenRouter",
               "moonshot": "Moonshot", "openai": "OpenAI", "anthropic": "Anthropic", "mock": "Mock"}
    models = sorted(
        [
            {
                "name":           model,
                "id":             model,
                "provider":       provider,
                "provider_label": _labels.get(provider, provider.title()),
                "available":      provider in available_providers,
            }
            for model, provider in MODEL_TO_PROVIDER.items()
        ],
        key=lambda m: (0 if m["available"] else 1),
    )
    return {
        "models":    models,
        "providers": list(available_providers),
        "mock_mode": settings.enable_mock_provider,
    }
