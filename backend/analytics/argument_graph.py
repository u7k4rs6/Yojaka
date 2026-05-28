from __future__ import annotations

from typing import Literal


class ArgumentGraph:
    def __init__(self) -> None:
        self._nodes: list[dict] = []
        self._edges: list[dict] = []
        self._node_ids: set[str] = set()

    def add_claim(self, claim_id: str, text: str, speaker: str) -> None:
        if claim_id not in self._node_ids:
            self._nodes.append({"id": claim_id, "text": text, "speaker": speaker})
            self._node_ids.add(claim_id)

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        edge_type: Literal["attacks", "supports", "extends"],
    ) -> None:
        self._edges.append({"from": from_id, "to": to_id, "type": edge_type})

    def to_dict(self) -> dict:
        return {
            "nodes": list(self._nodes),
            "edges": list(self._edges),
        }
