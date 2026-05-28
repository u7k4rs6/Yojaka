from __future__ import annotations

from collections import deque

from core.schemas import Message


_ASSISTANT_ROLE_PREFIXES = ("pro_", "con_", "judge")


def _openai_role(role: str) -> str:
    for prefix in _ASSISTANT_ROLE_PREFIXES:
        if role.startswith(prefix):
            return "assistant"
    return "user"


class ContextWindow:
    """L1 sliding window of recent messages."""

    def __init__(self, max_turns: int = 6) -> None:
        self._max_turns = max_turns
        self._window: deque[Message] = deque()

    def push(self, message: Message) -> None:
        """Add a message to the window, evicting the oldest entry if full."""
        if self._max_turns > 0 and len(self._window) >= self._max_turns:
            self._window.popleft()
        self._window.append(message)

    def get(self) -> list[Message]:
        """Return recent messages in chronological order."""
        return list(self._window)

    def clear(self) -> None:
        """Remove all messages from the window."""
        self._window.clear()

    def to_openai_messages(self) -> list[dict]:
        """Convert window contents to [{role, content}] dicts for provider calls."""
        return [
            {"role": _openai_role(msg.role), "content": msg.content}
            for msg in self._window
        ]
