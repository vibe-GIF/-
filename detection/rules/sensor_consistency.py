import math

import numpy as np

from server.models import RuleResult, TraceRequest
from .base import BaseRule
from .config import SensorConsistencyConfig


def geo_dist_m(lat1, lon1, lat2, lon2) -> float:
    """球面近似距离（米），经度按 cos(lat) 缩放。"""
    avg_lat = math.radians((lat1 + lat2) / 2.0)
    d_lat = (lat2 - lat1) * 111_320
    d_lon = (lon2 - lon1) * 111_320 * math.cos(avg_lat)
    return math.hypot(d_lat, d_lon)


class SensorConsistencyRule(BaseRule):
    name = "sensor_consistency"

    def evaluate(
        self, trace: TraceRequest, config: SensorConsistencyConfig
    ) -> RuleResult:
        sensors = trace.sensors
        if not sensors or len(sensors) < 5:
            return RuleResult(
                rule_name=self.name, passed=False, score=0.3,
                detail="No or insufficient sensor data — possible sensor gap",
            )
        # 步频信号：优先 step_rate(Hz)；缺省时用累计 step_count 差分估计，避免把累计值当步频
        sorted_sensors = sorted(
            [s for s in sensors if s.timestamp is not None], key=lambda s: s.timestamp
        )
        sensor_rate_by_ts = {}
        prev_count, prev_t = None, None
        for s in sorted_sensors:
            if s.step_rate is not None:
                sensor_rate_by_ts[s.timestamp] = float(s.step_rate)
            elif s.step_count is not None and prev_count is not None and prev_t is not None:
                dt = s.timestamp - prev_t
                if dt > 0:
                    sensor_rate_by_ts[s.timestamp] = max(0.0, (s.step_count - prev_count) / dt)
            if s.step_count is not None:
                prev_count = s.step_count
                prev_t = s.timestamp

        gps_speeds = []
        step_rates = []
        for i in range(1, len(trace.gps_points)):
            p0, p1 = trace.gps_points[i - 1], trace.gps_points[i]
            dt = p1.timestamp - p0.timestamp
            if dt <= 0:
                continue
            dist = geo_dist_m(p0.lat, p0.lon, p1.lat, p1.lon)
            gps_speeds.append(dist / dt)
            nearby_rates = [
                rate for ts, rate in sensor_rate_by_ts.items()
                if abs(ts - p1.timestamp) < 0.5
            ]
            if nearby_rates:
                step_rates.append(float(np.mean(nearby_rates)))
            else:
                step_rates.append(0.0)

        if len(gps_speeds) < 5 or len(step_rates) < 5:
            return RuleResult(
                rule_name=self.name, passed=False, score=0.2,
                detail="Insufficient aligned GPS-sensor samples",
            )

        valid = [
            (s, r) for s, r in zip(gps_speeds, step_rates)
            if config.speed_range[0] <= s <= config.speed_range[1]
        ]
        if len(valid) < 5:
            return RuleResult(
                rule_name=self.name, passed=True, score=0.0,
                detail="Speed range too narrow for correlation analysis",
            )
        speeds_arr = np.array([v[0] for v in valid])
        steps_arr = np.array([v[1] for v in valid])

        if np.std(steps_arr) < 1e-6:
            return RuleResult(
                rule_name=self.name, passed=False, score=0.8,
                detail="Step count is constant — sensor injection suspected",
            )
        corr = float(np.corrcoef(speeds_arr, steps_arr)[0, 1])
        if abs(corr) < config.speed_step_corr_min:
            return RuleResult(
                rule_name=self.name, passed=False, score=0.7,
                detail=f"GPS-speed vs step-count correlation {corr:.3f} "
                f"below threshold {config.speed_step_corr_min} — "
                "sensor data likely fake",
            )
        return RuleResult(
            rule_name=self.name, passed=True, score=0.0,
            detail=f"GPS-step correlation {corr:.3f} within normal range",
        )