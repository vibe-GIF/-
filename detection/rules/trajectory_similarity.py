from server.models import RuleResult, TraceRequest
from .base import BaseRule
from .config import TrajectorySimilarityConfig


class TrajectorySimilarityRule(BaseRule):
    name = "trajectory_similarity"

    _history: list = []

    def evaluate(
        self, trace: TraceRequest, config: TrajectorySimilarityConfig
    ) -> RuleResult:
        current_grid = set()
        for p in trace.gps_points:
            col = int(p.lon * config.grid_size)
            row = int(p.lat * config.grid_size)
            current_grid.add((col, row))

        if self._history:
            high_sim = 0.0
            for prev_grid in self._history:
                intersection = current_grid & prev_grid
                union = current_grid | prev_grid
                sim = len(intersection) / len(union) if union else 0
                high_sim = max(high_sim, sim)
            if high_sim > config.jaccard_threshold:
                return RuleResult(
                    rule_name=self.name, passed=False, score=0.8,
                    detail=f"Trajectory Jaccard similarity {high_sim:.3f} "
                    f"exceeds threshold {config.jaccard_threshold} — "
                    "possible route reuse",
                )

        self._history.append(current_grid)
        if len(self._history) > 100:
            self._history = self._history[-50:]

        return RuleResult(
            rule_name=self.name, passed=True, score=0.0,
            detail="Trajectory does not match recent routes",
        )