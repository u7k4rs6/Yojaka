from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID, uuid4

from core.schemas import AgentAssignment, Debate, SessionMode, Team, Archetype


@dataclass
class Phase:
    id:           UUID
    type:         str   # 'constructive'|'cross_exam'|'evidence'|'discussion'|'rebuttal'|'closing'|'judgment'
    execution:    Literal["SEQUENTIAL", "PARALLEL"]
    dependencies: list[UUID]
    participants: list[AgentAssignment]
    round_number: int = 1


class PhaseGraphBuilder:
    """
    Build a materialized phase queue for a debate based on debaters_per_team.

    Phase matrix per spec §17:
    1 debater:  Constructive → Discussion(N rounds) → Closing → Judgment
    2 debaters: + Rebuttal phases
    3 debaters: + Evidence Researcher phases
    4 debaters: + Cross-Examiner phases
    """

    def build(self, debate: Debate) -> list[Phase]:
        settings = debate.assignments
        pro_agents = [a for a in settings if a.team == Team.PRO]
        con_agents = [a for a in settings if a.team == Team.CON]
        judge_agents = [a for a in settings if a.archetype in (Archetype.JUDGE, Archetype.JUDGE_ASSISTANT)]

        debaters_per_team = max(len(pro_agents), 1)
        phases: list[Phase] = []

        def pro_by_arch(arch: Archetype) -> list[AgentAssignment]:
            return [a for a in pro_agents if a.archetype == arch]

        def con_by_arch(arch: Archetype) -> list[AgentAssignment]:
            return [a for a in con_agents if a.archetype == arch]

        last_ids: list[UUID] = []

        def add(phase: Phase) -> Phase:
            phase.dependencies = list(last_ids)
            phases.append(phase)
            return phase

        def add_parallel(pro_phase: Phase, con_phase: Phase) -> list[Phase]:
            for p in (pro_phase, con_phase):
                p.dependencies = list(last_ids)
            phases.extend([pro_phase, con_phase])
            return [pro_phase, con_phase]

        # ── Constructive (sequential: Pro then Con) ───────────────────────────
        pro_advocates = pro_by_arch(Archetype.LEAD_ADVOCATE) or pro_agents[:1]
        con_advocates = con_by_arch(Archetype.LEAD_ADVOCATE) or con_agents[:1]

        p_con = Phase(id=uuid4(), type="constructive", execution="SEQUENTIAL", dependencies=[], participants=pro_advocates, round_number=1)
        phases.append(p_con)
        last_ids = [p_con.id]

        c_con = Phase(id=uuid4(), type="constructive", execution="SEQUENTIAL", dependencies=list(last_ids), participants=con_advocates, round_number=1)
        phases.append(c_con)
        last_ids = [c_con.id]

        # ── Evidence phase (debaters >= 3) ────────────────────────────────────
        if debaters_per_team >= 3:
            pro_ev = pro_by_arch(Archetype.EVIDENCE_RESEARCHER)
            con_ev = con_by_arch(Archetype.EVIDENCE_RESEARCHER)
            if pro_ev and con_ev:
                p_ev = Phase(id=uuid4(), type="evidence", execution="PARALLEL", dependencies=[], participants=pro_ev, round_number=1)
                c_ev = Phase(id=uuid4(), type="evidence", execution="PARALLEL", dependencies=[], participants=con_ev, round_number=1)
                paired = add_parallel(p_ev, c_ev)
                last_ids = [p.id for p in paired]

        # ── Discussion rounds ─────────────────────────────────────────────────
        # Use debate settings (round_count from assignments context, default 1)
        debate_rounds = 1
        for round_num in range(1, debate_rounds + 1):
            p_disc = Phase(id=uuid4(), type="discussion", execution="SEQUENTIAL", dependencies=[], participants=pro_advocates, round_number=round_num)
            phases.append(p_disc)
            p_disc.dependencies = list(last_ids)
            last_ids = [p_disc.id]

            c_disc = Phase(id=uuid4(), type="discussion", execution="SEQUENTIAL", dependencies=list(last_ids), participants=con_advocates, round_number=round_num)
            phases.append(c_disc)
            last_ids = [c_disc.id]

            # Rebuttal (debaters >= 2)
            if debaters_per_team >= 2:
                pro_reb = pro_by_arch(Archetype.REBUTTAL_CRITIC)
                con_reb = con_by_arch(Archetype.REBUTTAL_CRITIC)
                if pro_reb and con_reb:
                    p_r = Phase(id=uuid4(), type="rebuttal", execution="PARALLEL", dependencies=[], participants=pro_reb, round_number=round_num)
                    c_r = Phase(id=uuid4(), type="rebuttal", execution="PARALLEL", dependencies=[], participants=con_reb, round_number=round_num)
                    paired = add_parallel(p_r, c_r)
                    last_ids = [p.id for p in paired]

        # ── Closing (parallel) ────────────────────────────────────────────────
        p_cl = Phase(id=uuid4(), type="closing", execution="PARALLEL", dependencies=[], participants=pro_advocates, round_number=1)
        c_cl = Phase(id=uuid4(), type="closing", execution="PARALLEL", dependencies=[], participants=con_advocates, round_number=1)
        paired = add_parallel(p_cl, c_cl)
        last_ids = [p.id for p in paired]

        # ── Judge assistant (optional) ────────────────────────────────────────
        ja_agents = [a for a in judge_agents if a.archetype == Archetype.JUDGE_ASSISTANT]
        if ja_agents:
            ja_phase = Phase(id=uuid4(), type="judgment", execution="SEQUENTIAL", dependencies=list(last_ids), participants=ja_agents, round_number=1)
            phases.append(ja_phase)
            last_ids = [ja_phase.id]

        # ── Judgment ─────────────────────────────────────────────────────────
        j_agents = [a for a in judge_agents if a.archetype == Archetype.JUDGE]
        if j_agents:
            j_phase = Phase(id=uuid4(), type="judgment", execution="SEQUENTIAL", dependencies=list(last_ids), participants=j_agents, round_number=1)
            phases.append(j_phase)

        return phases
