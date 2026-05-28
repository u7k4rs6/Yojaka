from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[dict], Awaitable[None]]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[dict], Awaitable[None]]) -> None:
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        handlers = self._handlers.get(event_type, [])
        try:
            handlers.remove(handler)
        except ValueError:
            pass

    async def publish(self, event_type: str, payload: dict) -> None:
        handlers = list(self._handlers.get(event_type, []))
        if not handlers:
            return

        results = await asyncio.gather(
            *(h(payload) for h in handlers),
            return_exceptions=True,
        )
        for handler, result in zip(handlers, results):
            if isinstance(result, BaseException):
                logger.exception(
                    "EventBus handler %r raised an error for event %r",
                    handler,
                    event_type,
                    exc_info=result,
                )
