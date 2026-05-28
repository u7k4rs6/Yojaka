from __future__ import annotations


def ensemble_vote(stances: list[str]) -> str:
    if not stances:
        return "Mixed"

    counts: dict[str, int] = {}
    for s in stances:
        counts[s] = counts.get(s, 0) + 1

    max_count = max(counts.values())
    leaders = [stance for stance, cnt in counts.items() if cnt == max_count]

    if len(leaders) == 1:
        return leaders[0]
    return "Mixed"
