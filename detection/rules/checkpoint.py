import math

from server.models import RuleResult, TraceRequest
from .base import BaseRule
from .config import CheckpointConfig


def geo_dist_m(lat1, lon1, lat2, lon2) -> float:
    return math.hypot(lat2 - lat1, lon2 - lon1) * 111_320


class CheckpointRule(BaseRule):
    """跑步过程中须在操场指定打卡点完成至少一次打卡。"""

    name = "checkpoint"

    def evaluate(self, trace: TraceRequest, config: CheckpointConfig) -> RuleResult:
        if not config.checkpoints:
            return RuleResult(
                rule_name=self.name, passed=True, score=0.0,
                detail="No checkpoints configured", applicable=False,
            )

        hit = 0
        for cp_lon, cp_lat in config.checkpoints:
            for p in trace.gps_points:
                if geo_dist_m(p.lat, p.lon, cp_lat, cp_lon) <= config.checkpoint_radius_m:
                    hit += 1
                    break

        if hit == 0:
            return RuleResult(
                rule_name=self.name, passed=False, score=1.0,
                detail="Trace never passed any checkpoint",
            )
        if hit < config.min_checkpoints:
            return RuleResult(
                rule_name=self.name, passed=False, score=0.5,
                detail=f"Only {hit} checkpoint(s) hit, need {config.min_checkpoints}",
            )

        return RuleResult(
            rule_name=self.name, passed=True, score=0.0,
            detail=f"Hit {hit} checkpoint(s)",
        )
