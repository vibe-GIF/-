from typing import Dict, List

from server.models import RuleResult
from .config import DetectionConfig


class RiskScorer:
    def __init__(self, config: DetectionConfig):
        self.config = config

    def score(self, results: List[RuleResult]) -> float:
        total = 0.0
        weight_sum = 0.0
        for r in results:
            cfg = getattr(self.config, r.rule_name, None)
            weight = cfg.weight if cfg else 1.0
            total += r.score * weight
            weight_sum += weight
        return total / weight_sum if weight_sum > 0 else 0.0

    def verdict(self, risk: float) -> str:
        if risk >= self.config.risk_thresholds["high"]:
            return "high_risk"
        elif risk >= self.config.risk_thresholds["medium"]:
            return "medium_risk"
        elif risk >= self.config.risk_thresholds["low"]:
            return "low_risk"
        return "normal"