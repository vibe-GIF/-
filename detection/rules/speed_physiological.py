import math

import numpy as np

from server.models import RuleResult, TraceRequest
from .base import BaseRule
from .config import SpeedPhysiologicalConfig


def geo_dist_m(lat1, lon1, lat2, lon2) -> float:
    return math.hypot(lat2 - lat1, lon2 - lon1) * 111_320


class SpeedPhysiologicalRule(BaseRule):
    name = "speed_physiological"

    def evaluate(
        self, trace: TraceRequest, config: SpeedPhysiologicalConfig
    ) -> RuleResult:
        points = trace.gps_points
        if len(points) < 2:
            return RuleResult(
                rule_name=self.name, passed=True, score=0.0,
                detail="Insufficient points",
            )
        speeds = []
        accelerations = []
        for i in range(1, len(points)):
            p0, p1 = points[i - 1], points[i]
            dt = p1.timestamp - p0.timestamp
            if dt <= 0:
                continue
            dist = geo_dist_m(p0.lat, p0.lon, p1.lat, p1.lon)
            speed = dist / dt
            speeds.append(speed)
            if speeds:
                accelerations.append(
                    (speed - speeds[-2]) / dt if len(speeds) >= 2 else 0
                )
        max_speed = max(speeds) if speeds else 0
        max_acc = max(abs(a) for a in accelerations) if accelerations else 0
        speed_var = float(np.var(speeds)) if len(speeds) > 1 else 0

        details = []
        score = 0.0

        if max_speed > config.max_instant_speed:
            score = max(score, 0.6)
            details.append(
                f"Instant speed {max_speed:.2f}m/s exceeds "
                f"{config.max_instant_speed}m/s"
            )
        if max_acc > config.max_acceleration:
            score = max(score, 0.8)
            details.append(
                f"Acceleration {max_acc:.2f}m/s² exceeds "
                f"{config.max_acceleration}m/s²"
            )
        if speed_var < config.max_speed_variance and len(speeds) > 10:
            score = max(score, 0.4)
            details.append(
                f"Speed variance {speed_var:.3f} suspiciously low — "
                "possible constant-speed injection"
            )
        if not details:
            return RuleResult(
                rule_name=self.name, passed=True, score=0.0,
                detail=f"Max speed {max_speed:.2f}m/s, max accel {max_acc:.2f}m/s²",
            )
        return RuleResult(
            rule_name=self.name, passed=False, score=score,
            detail="; ".join(details),
        )