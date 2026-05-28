from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from core.intent_router import IntentRouter
from core.orchestrator import DebateOrchestrator
from core.schemas import CouncilSettings
from events.stream_manager import StreamManager
from providers.health_cache import HealthCache
from providers.router import ProviderRouter, MODEL_TO_PROVIDER
from providers.utility_tier import UtilityTier
from repositories.debates_repo import DebatesRepo
from repositories.intelligence_repo import IntelligenceRepo
from repositories.messages_repo import MessagesRepo
from repositories.runtime_diary_repo import RuntimeDiaryRepo
from repositories.sessions_repo import SessionsRepo
from repositories.user_profile_repo import UserProfileRepo
from storage.database import get_session_factory
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

intent_router = IntentRouter()

# Council settings singleton (shared with rest/settings.py module)
_council = CouncilSettings()

# Shared StreamManager — one per app process
_stream_manager = StreamManager()


def _build_orchestrator(db_factory: async_sessionmaker[AsyncSession]) -> DebateOrchestrator:
    """Build a fresh orchestrator with a scoped DB session."""
    # Providers
    health_cache = HealthCache()

    from providers.mock import MockProvider
    clients: dict = {"mock": MockProvider()}

    if settings.google_api_key:
        from providers.google import GoogleProvider
        clients["google"] = GoogleProvider()
    if settings.groq_api_key:
        from providers.groq import GroqProvider
        clients["groq"] = GroqProvider()
    if settings.openai_api_key:
        from providers.openai import OpenAIProvider
        clients["openai"] = OpenAIProvider()
    if settings.anthropic_api_key:
        from providers.anthropic import AnthropicProvider
        clients["anthropic"] = AnthropicProvider()
    if settings.openrouter_api_key:
        from providers.openrouter import OpenRouterProvider
        clients["openrouter"] = OpenRouterProvider()
    if settings.moonshot_api_key:
        from providers.moonshot import MoonshotProvider
        clients["moonshot"] = MoonshotProvider()

    provider_router = ProviderRouter(clients, health_cache)
    utility_tier    = UtilityTier(provider_router)

    # We inject repo factories; orchestrator creates per-call session via factory
    return _OrchestratorFactory(
        provider_router=provider_router,
        utility_tier=utility_tier,
        stream_manager=_stream_manager,
        db_factory=db_factory,
        council=_council,
    )


class _OrchestratorFactory:
    """Thin wrapper that creates a fresh DebateOrchestrator per debate with its own DB session."""

    def __init__(self, *, provider_router, utility_tier, stream_manager, db_factory, council):
        self._router    = provider_router
        self._utility   = utility_tier
        self._stream    = stream_manager
        self._factory   = db_factory
        self._council   = council

    async def run_debate(self, session_id: UUID, topic: str, model: str, client_id: str = "") -> None:
        async with self._factory() as db:
            sessions_repo = SessionsRepo(db)
            session = await sessions_repo.get(session_id)
            if not session:
                await self._stream.broadcast({"type": "error", "message": "Session not found"})
                return
        async with self._factory() as db:
            try:
                orch = DebateOrchestrator(
                    sessions_repo     = SessionsRepo(db),
                    debates_repo      = DebatesRepo(db),
                    messages_repo     = MessagesRepo(db),
                    intelligence_repo = IntelligenceRepo(db),
                    user_profile_repo = UserProfileRepo(db),
                    diary_repo        = RuntimeDiaryRepo(db),
                    stream_manager    = self._stream,
                    provider_router   = self._router,
                    utility_tier      = self._utility,
                    council           = self._council,
                )
                await orch.run_debate(session, topic, model, client_id)
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def run_interaction(self, session_id: UUID, topic: str, model: str, practice_side: str = "") -> None:
        async with self._factory() as db:
            sessions_repo = SessionsRepo(db)
            session = await sessions_repo.get(session_id)
            if not session:
                await self._stream.broadcast({"type": "error", "message": "Session not found"})
                return
        async with self._factory() as db:
            try:
                orch = DebateOrchestrator(
                    sessions_repo     = SessionsRepo(db),
                    debates_repo      = DebatesRepo(db),
                    messages_repo     = MessagesRepo(db),
                    intelligence_repo = IntelligenceRepo(db),
                    user_profile_repo = UserProfileRepo(db),
                    diary_repo        = RuntimeDiaryRepo(db),
                    stream_manager    = self._stream,
                    provider_router   = self._router,
                    utility_tier      = self._utility,
                    council           = self._council,
                )
                await orch.run_interaction(session, topic, model, practice_side)
                await db.commit()
            except Exception:
                await db.rollback()
                raise


_orch_factory: Optional[_OrchestratorFactory] = None


def get_orchestrator_factory() -> _OrchestratorFactory:
    global _orch_factory
    if _orch_factory is None:
        _orch_factory = _build_orchestrator(get_session_factory())
    return _orch_factory


@router.websocket("/ws/debates/{session_id}")
async def debates_ws(
    websocket: WebSocket,
    session_id: UUID,
    client_id: str = "",
):
    await websocket.accept()
    client_key = f"{session_id}:{client_id or id(websocket)}"
    queue = _stream_manager.add_client(client_key)

    # Fan-out task: forward queued events to this WS client
    async def sender():
        try:
            while True:
                event = await queue.get()
                if event is None:   # sentinel
                    break
                await websocket.send_text(json.dumps(event))
        except Exception:
            pass

    sender_task = asyncio.create_task(sender())

    try:
        async for raw in websocket.iter_text():
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
                continue

            try:
                # Log WS message received
                db_factory = get_session_factory()
                async with db_factory() as db:
                    diary = RuntimeDiaryRepo(db)
                    await diary.log("backend terminal", "interaction_received", str(msg.get("type")), session_id)

                intent = intent_router.route(msg)

                async with db_factory() as db:
                    diary = RuntimeDiaryRepo(db)
                    await diary.log("backend terminal", "intent_routed", intent, session_id)

                orch = get_orchestrator_factory()
                topic  = msg.get("topic", "")
                model  = msg.get("model") or settings.default_model

                if intent == "start_debate":
                    asyncio.create_task(
                        orch.run_debate(session_id, topic, model, client_id=client_id)
                    )
                elif intent == "start_interaction":
                    side = msg.get("practice_side", "")
                    asyncio.create_task(
                        orch.run_interaction(session_id, topic, model, practice_side=side)
                    )
                elif intent == "unknown":
                    await websocket.send_text(json.dumps({
                        "type":    "error",
                        "message": f"Unknown message type: {msg.get('type')}",
                    }))

            except Exception as exc:
                logger.exception("ws_handler_error: %s", exc)
                async with db_factory() as db:
                    diary = RuntimeDiaryRepo(db)
                    await diary.log("backend terminal", "ws_handler_error", str(exc), session_id)
                await websocket.send_text(json.dumps({"type": "error", "message": str(exc)}))

    except WebSocketDisconnect:
        async with get_session_factory()() as db:
            diary = RuntimeDiaryRepo(db)
            await diary.log("backend terminal", "debate_client_disconnected", f"client={client_key}", session_id)
    finally:
        _stream_manager.remove_client(client_key)
        sender_task.cancel()
        try:
            await sender_task
        except asyncio.CancelledError:
            pass
