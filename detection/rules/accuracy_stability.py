import numpy as np

from server.models import RuleResult, TraceRequest
from .base import BaseRule
from .config import AccuracyStabilityConfig


class AccuracyStabilityRule(BaseRule):
    name = "accuracy_stability"

    def evaluate(
        self, trace: TraceRequest, config: AccuracyStabilityConfig
    ) -> RuleResult:
        accuracies = [p.accuracy for p in trace.gps_points if p.accuracy is not None]
        if len(accuracies) < config.window_size:
            return RuleResult(
                rule_name=self.name,
                passed=True,
                score=0.0,
                detail=f"Too few accuracy samples ({len(accuracies)})",
            )
        variance = float(np.var(accuracies[-config.window_size:]))
        if variance < config.accuracy_variance_min:
            score = self.normalize_score(
                config.accuracy_variance_min - variance,
                config.accuracy_variance_min,
            )
            return RuleResult(
                rule_name=self.name,
                passed=False,
                score=score,
                detail=(
                    f"Accuracy variance {variance:.4f} below threshold "
                    f"{config.accuracy_variance_min} — possible GPS injection"
                ),
            )
        return RuleResult(
            rule_name=self.name,
            passed=True,
            score=0.0,
            detail=f"Accuracy variance {variance:.4f} within normal range",
        )