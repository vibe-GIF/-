"""
行为离群检测 — 分析配速分布、上传时间规律、设备-账号关联。
"""

import math
from collections import defaultdict
from typing import Dict, List, Tuple

import numpy as np


def geo_dist_m(lat1, lon1, lat2, lon2) -> float:
    return math.hypot(lat2 - lat1, lon2 - lon1) * 111_320


def pace_analysis(speeds: List[float]) -> dict:
    if not speeds:
        return {"mean_pace": 0, "pace_cv": 0, "is_suspicious": False}
    arr = np.array(speeds)
    mean_speed = float(np.mean(arr))
    cv = float(np.std(arr) / mean_speed) if mean_speed > 0 else 0

    is_suspicious = False
    reasons = []

    if mean_speed > 6.0:
        is_suspicious = True
        reasons.append(f"avg_speed_too_high:{mean_speed:.2f}m/s")
    if cv < 0.05:
        is_suspicious = True
        reasons.append(f"pace_too_consistent:CV={cv:.3f}")

    return {
        "mean_speed": round(mean_speed, 3),
        "pace_cv": round(cv, 3),
        "is_suspicious": is_suspicious,
        "reasons": reasons,
    }


def time_anomaly(timestamps: List[float]) -> dict:
    if len(timestamps) < 2:
        return {"is_suspicious": False, "reasons": []}
    intervals = np.diff(timestamps)
    mean_interval = float(np.mean(intervals))
    cv = float(np.std(intervals) / mean_interval) if mean_interval > 0 else 0

    is_suspicious = False
    reasons = []

    if cv < 0.05 and len(intervals) > 5:
        is_suspicious = True
        reasons.append(f"upload_interval_too_regular:CV={cv:.3f}")

    return {
        "mean_interval": round(mean_interval, 3),
        "interval_cv": round(cv, 3),
        "is_suspicious": is_suspicious,
        "reasons": reasons,
    }


class DeviceAccountGraph:
    def __init__(self):
        self._device_accounts: Dict[str, set] = defaultdict(set)

    def add(self, device_id: str, account_id: str):
        self._device_accounts[device_id].add(account_id)

    def device_account_count(self, device_id: str) -> int:
        return len(self._device_accounts.get(device_id, set()))

    def multi_account_devices(self, threshold: int = 3) -> List[Tuple[str, int]]:
        return [
            (d, len(accts)) for d, accts in self._device_accounts.items()
            if len(accts) >= threshold
        ]


class BehavioralAnomalyDetector:
    def __init__(self, max_accounts_per_device: int = 3):
        self.graph = DeviceAccountGraph()
        self.max_accounts = max_accounts_per_device

    def evaluate(self, speeds: List[float], timestamps: List[float],
                 device_id: str = None, account_id: str = None) -> dict:
        results = {"anomaly": False, "reasons": [], "scores": {}}

        pace = pace_analysis(speeds)
        time_anom = time_anomaly(timestamps)

        if pace["is_suspicious"]:
            results["anomaly"] = True
            results["reasons"].extend(pace["reasons"])
        results["scores"]["pace"] = pace

        if time_anom["is_suspicious"]:
            results["anomaly"] = True
            results["reasons"].extend(time_anom["reasons"])
        results["scores"]["time"] = time_anom

        if device_id and account_id:
            self.graph.add(device_id, account_id)
            count = self.graph.device_account_count(device_id)
            if count > self.max_accounts:
                results["anomaly"] = True
                results["reasons"].append(
                    f"multi_account:{device_id}={count}accounts"
                )

        results["risk"] = len(results["reasons"]) / 5.0
        return results