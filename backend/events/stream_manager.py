from __future__ import annotations

import asyncio
import logging
from asyncio import QueueFull
from datetime import datetime, timezone
from typing import AsyncIterator, Optional
from uuid import UUID, uuid4

from core.schemas import AgentAssignment, Message

logger = logging.getLogger(__name__)


class StreamManager:
    QUEUE_MAX: int = 256

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue] = {}

    # ── Client lifecycle ──────────────────────────────────────────────────────

    def add_client(self, client_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=self.QUEUE_MAX)
        self._queues[client_id] = queue
        return queue

    def remove_client(self, client_id: str) -> None:
        self._queues.pop(client_id, None)

    # ── Fan-out helpers ───────────────────────────────────────────────────────

    async def broadcast(self, event: dict) -> None:
        disconnected: list[str] = []
        for client_id, queue in list(self._queues.items()):
            try:
                queue.put_nowait(event)
            except QueueFull:
                logger.warning("Queue full for client %r — disconnecting", client_id)
                disconnected.append(client_id)
        for client_id in disconnected:
            self.remove_client(client_id)

    async def send_to(self, client_id: str, event: dict) -> None:
        queue = self._queues.get(client_id)
        if queue is None:
            return
        try:
            queue.put_nowait(event)
        except QueueFull:
            logger.warning("Queue full for client %r — disconnecting", client_id)
            self.remove_client(client_id)

    # ── Stream → Message ──────────────────────────────────────────────────────

    async def stream_to_message(
        self,
        stream: AsyncIterator[str],
        assignment: AgentAssignment,
        stream_id: str,
        session_id: UUID,
        debate_id: Optional[UUID],
        round_number: int,
    ) -> Message:
        role     = f"{assignment.team.value}_{assignment.archetype.value}"
        msg_id   = uuid4()
        now      = datetime.now(timezone.utc)
        speaker  = assignment.archetype.value if assignment.archetype else role
        model    = assignment.model or ""

        def _msg_stub(content: str) -> dict:
            return {
                "id":          str(msg_id),
                "role":        role,
                "speaker":     speaker,
                "model":       model,
                "content":     content,
                "phase_key":   "",
                "phase_title": "",
                "phase_kind":  "",
                "phase_index": None,
                "sequence":    round_number,
                "created_at":  now.isoformat(),
            }

        await self.broadcast(
            {
                "type":      "message_started",
                "stream_id": stream_id,
                "message":   _msg_stub(""),
                "round":     round_number,
            }
        )

        chunks: list[str] = []
        async for chunk in stream:
            chunks.append(chunk)
            await self.broadcast(
                {
                    "type":      "message_delta",
                    "stream_id": stream_id,
                    "delta":     chunk,
                    "round":     round_number,
                }
            )

        content = "".join(chunks)

        msg = Message(
            id=msg_id,
            session_id=session_id,
            debate_id=debate_id,
            stream_id=stream_id,
            role=role,
            team=assignment.team,
            content=content,
            round=round_number,
            phase=None,
            model=model,
            temperature=assignment.settings.temperature if assignment.settings else None,
            created_at=now,
        )

        await self.broadcast(
            {
                "type":      "message_completed",
                "stream_id": stream_id,
                "message":   _msg_stub(content),
                "round":     round_number,
            }
        )

        return msg
