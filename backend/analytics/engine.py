from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from core.schemas import Message
from analytics.metrics import (
    ROLE_WEIGHTS,
    compute_confidence,
    compute_novelty,
    detect_evidence,
    detect_rebuttal,
    detect_stance,
)
from analytics.bayesian import BayesianUpdater
from analytics.argument_graph import ArgumentGraph
from analytics.delphi import compute_delphi_variance
from analytics.game_theory import compute_nash_pressure as _nash_pressure
from analytics.moe import ensemble_vote


class TurnMetrics(BaseModel):
    confidence:     float
    novelty:        float
    credibility:    float
    stance:         Literal["Support", "Oppose", "Mixed"]
    has_evidence:   bool
    is_rebuttal:    bool
    weighted_score: float


class AnalyticsEngine:
    def __init__(self) -> None:
        self._bayesian = BayesianUpdater()
        self._graph    = ArgumentGraph()

    async def analyze_turn(
        self,
        message: Message,
        prior_turns: list[Message],
    ) -> TurnMetrics:
        text        = message.content
        prior_texts = [m.content for m in prior_turns]

        confidence = compute_confidence(text)
        novelty    = compute_novelty(text, prior_texts)

        # credibility = role weight (default 1.0 if role not in map)
        role        = (message.metadata or {}).get("archetype") or message.role or ""
        credibility = ROLE_WEIGHTS.get(role, 1.0)

        stance      = detect_stance(text, role=role)
        has_evidence = detect_evidence(text)
        is_rebuttal  = detect_rebuttal(text)

        weighted_score = confidence * novelty * credibility

        return TurnMetrics(
            confidence=confidence,
            novelty=novelty,
            credibility=credibility,
            stance=stance,
            has_evidence=has_evidence,
            is_rebuttal=is_rebuttal,
            weighted_score=weighted_score,
        )

    async def update_bayesian(self, turn_metrics: TurnMetrics) -> None:
        self._bayesian.update(turn_metrics.stance, turn_metrics.confidence)

    async def build_argument_graph(
        self,
        debate_id: UUID,
        messages: list[Message],
    ) -> dict:
        graph = ArgumentGraph()
        prior_id: str | None = None
        for msg in messages:
            claim_id = str(msg.id)
            speaker  = msg.role or "unknown"
            # Truncate text to a short label for the graph node
            snippet  = msg.content[:120].strip()
            graph.add_claim(claim_id, snippet, speaker)

            if prior_id is not None:
                edge_type = "attacks" if detect_rebuttal(msg.content) else "extends"
                graph.add_edge(prior_id, claim_id, edge_type)

            prior_id = claim_id

        return graph.to_dict()

    async def compute_delphi(self, scores: list[float]) -> float:
        return compute_delphi_variance(scores)

    async def compute_nash_pressure(
        self,
        pro_score: float,
        con_score: float,
    ) -> float:
        return _nash_pressure(pro_score, con_score)

    async def finalize(
        self,
        debate_id: UUID,
        rounds: list[dict],
    ) -> dict:
        """
        Build the full analytics payload (spec §10.2).

        Each element in `rounds` is expected to have the shape:
            {
                "round_number": int,
                "turns": [{"message": Message, "prior_turns": [Message]}],
            }
        """
        processed_rounds: list[dict] = []
        all_pro_scores:  list[float] = []
        all_con_scores:  list[float] = []
        all_messages:    list[Message] = []
        strongest_claims: list[dict] = []

        for rnd in rounds:
            round_number: int   = rnd.get("round_number", 0)
            turn_dicts:   list  = rnd.get("turns", [])

            round_turns:   list[dict]  = []
            round_stances: list[str]   = []
            round_scores:  list[float] = []

            for t in turn_dicts:
                msg: Message       = t["message"]
                prior: list[Message] = t.get("prior_turns", [])

                metrics = await self.analyze_turn(msg, prior)
                await self.update_bayesian(metrics)

                all_messages.append(msg)

                turn_entry = {
                    "message_id":    str(msg.id),
                    "role":          msg.role,
                    "team":          msg.team.value if msg.team else None,
                    "round":         msg.round,
                    "confidence":    metrics.confidence,
                    "novelty":       metrics.novelty,
                    "credibility":   metrics.credibility,
                    "stance":        metrics.stance,
                    "has_evidence":  metrics.has_evidence,
                    "is_rebuttal":   metrics.is_rebuttal,
                    "weighted_score": metrics.weighted_score,
                }
                round_turns.append(turn_entry)
                round_stances.append(metrics.stance)
                round_scores.append(metrics.weighted_score)

                # Collect pro / con scores for Nash
                if msg.team and msg.team.value == "pro":
                    all_pro_scores.append(metrics.weighted_score)
                elif msg.team and msg.team.value == "con":
                    all_con_scores.append(metrics.weighted_score)

                # Track top claim candidates
                strongest_claims.append(
                    {
                        "message_id":    str(msg.id),
                        "weighted_score": metrics.weighted_score,
                        "snippet":       msg.content[:120].strip(),
                    }
                )

            delphi_var = await self.compute_delphi(round_scores)
            pro_avg    = sum(all_pro_scores) / len(all_pro_scores) if all_pro_scores else 0.0
            con_avg    = sum(all_con_scores) / len(all_con_scores) if all_con_scores else 0.0
            nash       = await self.compute_nash_pressure(pro_avg, con_avg)

            processed_rounds.append(
                {
                    "round_number":    round_number,
                    "turns":           round_turns,
                    "ensemble_vote":   ensemble_vote(round_stances),
                    "bayesian":        self._bayesian.snapshot(),
                    "delphi_variance": delphi_var,
                    "nash_pressure":   nash,
                }
            )

        argument_graph = await self.build_argument_graph(debate_id, all_messages)

        # Return top 5 strongest claims sorted by weighted_score desc
        strongest_claims.sort(key=lambda c: c["weighted_score"], reverse=True)

        return {
            "debate_id":       str(debate_id),
            "rounds":          processed_rounds,
            "argument_graph":  argument_graph,
            "strongest_claims": strongest_claims[:5],
        }
