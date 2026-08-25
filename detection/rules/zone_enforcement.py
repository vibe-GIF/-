from server.models import RuleResult, TraceRequest
from .base import BaseRule
from .config import ZoneEnforcementConfig


class ZoneEnforcementRule(BaseRule):
    """跑步任务必须在对应校区跑区内开启，跑区外启动的成绩无效。"""

    name = "zone_enforcement"

    def evaluate(self, trace: TraceRequest, config: ZoneEnforcementConfig) -> RuleResult:
        if not config.zone_bounds:
            return RuleResult(
                rule_name=self.name, passed=True, score=0.0,
                detail="No zone configured", applicable=False,
            )

        if not trace.gps_points:
            return RuleResult(
                rule_name=self.name, passed=True, score=0.0,
                detail="No GPS points", applicable=False,
            )

        lon_min, lat_min, lon_max, lat_max = config.zone_bounds
        first = trace.gps_points[0]

        inside = (
            lon_min <= first.lon <= lon_max
            and lat_min <= first.lat <= lat_max
        )
        if not inside:
            return RuleResult(
                rule_name=self.name, passed=False, score=1.0,
                detail=f"Run started outside zone at ({first.lon:.5f},{first.lat:.5f})",
            )

        outside = sum(
            1 for p in trace.gps_points
            if not (lon_min <= p.lon <= lon_max and lat_min <= p.lat <= lat_max)
        )
        ratio = outside / len(trace.gps_points)
        if ratio > config.max_outside_ratio:
            return RuleResult(
                rule_name=self.name, passed=False, score=min(1.0, ratio),
                detail=f"{ratio:.0%} of points outside zone",
            )

        return RuleResult(
            rule_name=self.name, passed=True, score=0.0,
            detail="Run within zone",
        )
