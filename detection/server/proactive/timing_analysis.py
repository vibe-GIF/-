"""
请求时序分析

真实 Android 设备通过移动网络 / WiFi 连接时，请求延迟具有特定分布：
  - 蜂窝网络: 延迟 50-200ms，有抖动
  - WiFi: 延迟 10-50ms，较稳定
  - 模拟器通过数据中心 IP: 延迟 <5ms 或极其稳定

检测点：
  - 请求间隔的统计分布
  - 延迟的方差/熵
  - 批量请求的规律性
"""

import math
import time
from collections import deque
from typing import Dict, List, Optional

import numpy as np


class RequestTimingAnalyzer:
    def __init__(self, window_size: int = 50):
        self._timestamps: deque = deque(maxlen=window_size)
        self._intervals: deque = deque(maxlen=window_size)

    def record(self, timestamp: float = None):
        now = timestamp or time.time()
        if self._timestamps:
            self._intervals.append(now - self._timestamps[-1])
        self._timestamps.append(now)

    def analyze(self, intervals: List[float] = None) -> dict:
        data = intervals or list(self._intervals)
        if len(data) < 5:
            return {"score": 0.0, "anomaly": False, "reasons": ["insufficient_data"]}

        arr = np.array(data)
        mean_val = float(np.mean(arr))
        std_val = float(np.std(arr))
        cv = std_val / mean_val if mean_val > 0 else 0
        entropy = self._compute_entropy(arr)

        reasons = []
        score = 0.0

        if mean_val < 0.005:
            score = max(score, 0.6)
            reasons.append(f"mean_interval_too_low:{mean_val*1000:.1f}ms")

        if cv < 0.1 and len(data) > 10:
            score = max(score, 0.5)
            reasons.append(f"intervals_too_regular:CV={cv:.3f}")

        if entropy < 0.5:
            score = max(score, 0.4)
            reasons.append(f"low_timing_entropy:{entropy:.3f}")

        return {
            "score": round(score, 4),
            "anomaly": score > 0.3,
            "reasons": reasons,
            "mean_ms": round(mean_val * 1000, 2),
            "cv": round(cv, 4),
            "entropy": round(entropy, 4),
            "sample_count": len(data),
        }

    def _compute_entropy(self, arr: np.ndarray, bins: int = 20) -> float:
        hist, _ = np.histogram(arr, bins=bins)
        hist = hist[hist > 0]
        probs = hist / hist.sum()
        h = -float(np.sum(probs * np.log2(probs)))
        max_h = math.log2(bins)
        return h / max_h if max_h > 0 else 0.0