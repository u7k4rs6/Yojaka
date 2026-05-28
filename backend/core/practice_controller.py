from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

from core.schemas import Debate, Session, SessionSettings, Team, Archetype, AgentAssignment


class PracticeController:
    """
    Manages practice mode session state and determines whose turn it is.
    """

    def __init__(self, session: Session, debate: Debate) -> None:
        self.session = session
        self.debate  = debate
        self._state: dict = {
            "human_side": self._resolve_human_side(),
            "turn":       "human",
            "round":      1,
            "rounds_completed": 0,
            "ending":     False,
        }

    def _resolve_human_side(self) -> str:
        settings = self.session.settings
        if settings.human_side == "Auto":
            # Default to Pro
            return "pro"
        return settings.human_side.lower()

    def get_state(self) -> dict:
        return dict(self._state)

    def is_human_turn(self) -> bool:
        return self._state["turn"] == "human"

    def is_ending(self) -> bool:
        return self._state["ending"]

    def advance_turn(self) -> None:
        """Flip between human and AI turn, increment round if needed."""
        if self._state["turn"] == "human":
            self._state["turn"] = "ai"
        else:
            self._state["turn"] = "human"
            self._state["rounds_completed"] += 1
            self._state["round"] += 1

        settings = self.session.settings
        if settings.practice_flow == "Structured":
            if self._state["rounds_completed"] >= settings.structured_rounds:
                self._state["ending"] = True

    def get_ai_assignment(self) -> Optional[AgentAssignment]:
        """Return the AI practice debater assignment."""
        for a in self.debate.assignments:
            if a.archetype == Archetype.PRACTICE_DEBATER:
                return a
        return None

    def get_trainer_assignment(self) -> Optional[AgentAssignment]:
        """Return the debate trainer assignment (for post-practice feedback)."""
        for a in self.debate.assignments:
            if a.archetype == Archetype.DEBATE_TRAINER:
                return a
        return None
