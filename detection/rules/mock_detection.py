import math
from typing import List

from server.models import GPSPoint, RuleResult, TraceRequest
from .base import BaseRule
from .config import MockDetectionConfig


class MockDetectionRule(BaseRule):
    name = "mock_detection"

    def evaluate(self, trace: TraceRequest, config: MockDetectionConfig) -> RuleResult:
        mock_flags = sum(
            1 for p in trace.gps_points
            if getattr(p, "mock_mark", False)
        )
        if mock_flags >= config.mock_mark_threshold:
            return RuleResult(
                rule_name=self.name,
                passed=False,
                score=1.0,
                detail=f"Mock location flag detected in {mock_flags} points",
            )
        return RuleResult(
            rule_name=self.name,
            passed=True,
            score=0.0,
            detail="No mock location flag detected",
        )