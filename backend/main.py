from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from storage.database import create_all_tables, close_engine
from repositories.runtime_diary_repo import RuntimeDiaryRepo
from storage.database import get_session_factory

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await create_all_tables()
    async with get_session_factory()() as db:
        diary = RuntimeDiaryRepo(db)
        await diary.log("backend terminal", "startup", "Yojaka backend v2 starting")
    yield
    # Shutdown
    await close_engine()


def create_app() -> FastAPI:
    app = FastAPI(title="Yojaka API", version="2.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REST routers
    from api.rest.system       import router as system_router
    from api.rest.sessions     import router as sessions_router
    from api.rest.settings     import router as settings_router
    from api.rest.messages     import router as messages_router
    from api.rest.analytics    import router as analytics_router
    from api.rest.user_profile import router as user_profile_router
    from api.rest.observability import router as observability_router

    app.include_router(system_router)
    app.include_router(sessions_router)
    app.include_router(settings_router)
    app.include_router(messages_router)
    app.include_router(analytics_router)
    app.include_router(user_profile_router)
    app.include_router(observability_router)

    # WebSocket
    from api.ws.debates import router as ws_router
    app.include_router(ws_router)

    return app


app = create_app()
