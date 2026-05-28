from __future__ import annotations


class BayesianUpdater:
    def __init__(self) -> None:
        self.support: float = 0.5
        self.oppose:  float = 0.5
        self.mixed:   float = 0.0

    def update(self, stance: str, confidence: float) -> None:
        if stance == "Support":
            self.support += confidence * 0.1
        elif stance == "Oppose":
            self.oppose += confidence * 0.1
        else:  # Mixed
            self.mixed += confidence * 0.05

        total = self.support + self.oppose + self.mixed
        if total > 0:
            self.support /= total
            self.oppose  /= total
            self.mixed   /= total

    def snapshot(self) -> dict:
        return {
            "support": round(self.support, 4),
            "oppose":  round(self.oppose,  4),
            "mixed":   round(self.mixed,   4),
        }
