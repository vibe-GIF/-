import math

from server.models import RuleResult, TraceRequest
from .base import BaseRule
from .config import StepDistanceConfig


def geo_dist_m(lat1, lon1, lat2, lon2) -> float:
    return math.hypot(lat2 - lat1, lon2 - lon1) * 111_320


class StepDistanceRule(BaseRule):
    """微信步数 vs GPS 里程 一致性校验。

    小程序体系里最硬的信号：步数在微信+硬件层，模拟器控不了。
    GPS 跑了几公里但步数≈0 → 直接判定伪造。
    """

    name = "step_distance"

    def evaluate(self, trace: TraceRequest, config: StepDistanceConfig) -> RuleResult:
        if trace.total_steps is None:
            return RuleResult(
                rule_name=self.name, passed=True, score=0.0,
                detail="No step count provided", applicable=False,
            )

        gps_distance = sum(
            geo_dist_m(
                trace.gps_points[i - 1].lat, trace.gps_points[i - 1].lon,
                trace.gps_points[i].lat, trace.gps_points[i].lon,
            )
            for i in range(1, len(trace.gps_points))
        )

        steps = trace.total_steps
        implied_distance = steps * config.stride_length_m

        # GPS 有里程但几乎没步数 → 典型模拟器伪造
        if gps_distance > config.min_gps_m and steps < config.min_steps:
            return RuleResult(
                rule_name=self.name, passed=False, score=1.0,
                detail=f"GPS {gps_distance:.0f}m but only {steps} steps",
            )

        if implied_distance <= 0:
            ratio = float("inf")
        else:
            ratio = gps_distance / implied_distance

        # 步幅换算后与 GPS 里程差距过大 → 不一致
        if ratio > config.max_ratio or ratio < config.min_ratio:
            return RuleResult(
                rule_name=self.name, passed=False,
                score=min(1.0, abs(1 - ratio)),
                detail=f"GPS/implied distance ratio {ratio:.2f} out of range",
            )

        return RuleResult(
            rule_name=self.name, passed=True, score=0.0,
            detail=f"GPS {gps_distance:.0f}m vs {steps} steps (ratio {ratio:.2f})",
        )
