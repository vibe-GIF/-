"""
渐进式风险评分 — 基于窗口序列的趋势分析。
"""

from typing import List


class ProgressiveScorer:
    def __init__(self, early_warning_threshold: float = 0.4,
                 alert_threshold: float = 0.6,
                 min_windows_for_verdict: int = 3):
        self.early_warning = early_warning_threshold
        self.alert = alert_threshold
        self.min_windows = min_windows_for_verdict

    def evaluate(self, window_scores: List[float]) -> dict:
        if not window_scores:
            return {"level": "unknown", "reason": "no_data"}

        n = len(window_scores)
        latest = window_scores[-1]
        avg = sum(window_scores) / n

        if n >= self.min_windows:
            trend = self._trend(window_scores)
        else:
            trend = "insufficient"

        if latest >= self.alert:
            return {"level": "alert", "reason": f"instant_risk={latest:.2f}", "trend": trend}
        if avg >= self.early_warning:
            return {"level": "warning", "reason": f"avg_risk={avg:.2f}", "trend": trend}
        if n >= self.min_windows and trend == "rising":
            return {"level": "watch", "reason": "risk_trend_rising", "trend": trend}

        return {"level": "normal", "reason": f"avg_risk={avg:.2f}", "trend": trend}

    def _trend(self, scores: List[float]) -> str:
        if len(scores) < 3:
            return "insufficient"
        half = len(scores) // 2
        first_half = sum(scores[:half]) / half
        second_half = sum(scores[half:]) / (len(scores) - half)
        if second_half > first_half * 1.3:
            return "rising"
        elif second_half < first_half * 0.7:
            return "falling"
        return "stable"