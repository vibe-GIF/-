import math

import numpy as np

from server.models import RuleResult, TraceRequest
from .base import BaseRule
from .config import NoiseSpectrumConfig


def geo_dist_m(lat1, lon1, lat2, lon2) -> float:
    return math.hypot(lat2 - lat1, lon2 - lon1) * 111_320


class NoiseSpectrumRule(BaseRule):
    name = "noise_spectrum"

    def evaluate(
        self, trace: TraceRequest, config: NoiseSpectrumConfig
    ) -> RuleResult:
        points = trace.gps_points
        if len(points) < config.window_size + 2:
            return RuleResult(
                rule_name=self.name, passed=True, score=0.0,
                detail=f"Too few points ({len(points)}) for spectrum analysis",
            )
        displacements = []
        for i in range(1, len(points)):
            dist = geo_dist_m(
                points[i - 1].lat, points[i - 1].lon,
                points[i].lat, points[i].lon,
            )
            displacements.append(dist)
        arr = np.array(displacements)
        arr = arr - np.mean(arr)
        if np.std(arr) < 1e-8:
            return RuleResult(
                rule_name=self.name, passed=False, score=1.0,
                detail="Zero-variance displacement — GPS injection artifact",
            )
        autocorr = np.correlate(arr, arr, mode="full")
        autocorr = autocorr[autocorr.size // 2:]
        autocorr = autocorr / autocorr[0]
        lag_1 = float(autocorr[1]) if len(autocorr) > 1 else 0
        lag_2 = float(autocorr[2]) if len(autocorr) > 2 else 0
        mean_ac = float(np.mean(autocorr[1:6])) if len(autocorr) > 5 else 0.0

        score = 0.0
        details = []
        if abs(lag_1) < config.autocorr_threshold:
            score = max(score, 0.5)
            details.append(
                f"Lag-1 autocorrelation {lag_1:.3f} near zero — "
                "white noise, not real GPS drift"
            )
        if abs(mean_ac) < config.autocorr_threshold * 0.3 and abs(lag_1) < config.autocorr_threshold:
            score = max(score, 0.4)
            details.append(
                f"Short-lag autocorrelation {mean_ac:.3f} suspiciously low"
            )
        if not details:
            return RuleResult(
                rule_name=self.name, passed=True, score=0.0,
                detail=f"Autocorr lag-1={lag_1:.3f}, lag-2={lag_2:.3f}, "
                f"mean={mean_ac:.3f} — realistic noise spectrum",
            )
        return RuleResult(
            rule_name=self.name, passed=False, score=score,
            detail="; ".join(details),
        )