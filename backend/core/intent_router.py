from __future__ import annotations


class IntentRouter:
    """Routes a WebSocket message to the right handler based on its ``type`` field."""

    _KNOWN = frozenset({"start_debate", "start_interaction", "end_practice_debate"})

    def route(self, message: dict) -> str:
        """Return one of: ``start_debate``, ``start_interaction``, ``end_practice_debate``, ``unknown``."""
        msg_type = message.get("type", "")
        if msg_type in self._KNOWN:
            return msg_type
        return "unknown"
