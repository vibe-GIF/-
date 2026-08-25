"""
滑动窗口处理器 — 将实时 GPS 数据流切分为 10 秒窗口，
每个窗口独立评分，实现渐进式风险检测。
"""

import math
import time
from collections import deque
from typing import Callable, List, Optional, Tuple

from server.models import GPSPoint, RuleResult, TraceRequest
from rules.config import DetectionConfig
from rules.engine import RuleEngine
from rules.risk_scorer import RiskScorer


class SlidingWindow:
    def __init__(self, window_sec: float = 10.0, stride_sec: float = 5.0):
        self.window_sec = window_sec
        self.stride_sec = stride_sec
        self._points: deque = deque()
        self._last_eval_time: float = -float("inf")

    def add_point(self, point: GPSPoint):
        self._points.append(point)
        cutoff = point.timestamp - self.window_sec * 3
        while self._points and self._points[0].timestamp < cutoff:
            self._points.popleft()

    def current_window(self) -> List[GPSPoint]:
        if not self._points:
            return []
        t_end = self._points[-1].timestamp
        t_start = t_end - self.window_sec
        return [p for p in self._points if p.timestamp >= t_start]

    def should_evaluate(self, now: float) -> bool:
        if now - self._last_eval_time >= self.stride_sec:
            self._last_eval_time = now
            return True
        return False

    def window_count(self) -> int:
        return max(0, int((self._points[-1].timestamp - self._points[0].timestamp) / self.stride_sec)) if len(self._points) >= 2 else 0


class StreamingDetector:
    def __init__(self, config: DetectionConfig = None,
                 window_sec: float = 10.0, stride_sec: float = 5.0):
        self.config = config
        self.window = SlidingWindow(window_sec, stride_sec)
        self.engine = RuleEngine(config=config)
        self.scorer = RiskScorer(config=config)
        self._scores: deque = deque(maxlen=20)
        self._warnings: List[dict] = []
        self._session_id: str = ""
        self._account_id: str = ""
        self._created_at: float = time.time()

    def start_session(self, session_id: str, account_id: str = ""):
        self._session_id = session_id
        self._account_id = account_id
        self._scores.clear()
        self._warnings.clear()

    def feed(self, point: GPSPoint) -> Optional[dict]:
        self.window.add_point(point)

        if not self.window.should_evaluate(point.timestamp):
            return None

        window_points = self.window.current_window()
        if len(window_points) < 3:
            return None

        trace = TraceRequest(
            trace_id=f"{self._session_id}_w{self.window.window_count()}",
            gps_points=window_points,
            account_id=self._account_id,
        )

        results = self.engine.evaluate(trace)
        risk = self.scorer.score(results)
        self._scores.append(risk)

        avg_risk = sum(self._scores) / len(self._scores)
        trend = self._compute_trend()

        result = {
            "session_id": self._session_id,
            "window": self.window.window_count(),
            "points": len(window_points),
            "window_risk": round(risk, 4),
            "avg_risk": round(avg_risk, 4),
            "trend": trend,
            "rule_results": {
                r.rule_name: {"passed": r.passed, "score": r.score}
                for r in results
            },
        }

        if risk > 0.5:
            warning = {
                "timestamp": time.time(),
                "window": self.window.window_count(),
                "risk": risk,
                "message": f"High risk window detected ({risk:.2f})",
            }
            self._warnings.append(warning)
            result["warning"] = warning

        return result

    def _compute_trend(self) -> str:
        if len(self._scores) < 3:
            return "stable"
        recent = list(self._scores)[-3:]
        if recent[-1] > recent[0] * 1.2:
            return "rising"
        elif recent[-1] < recent[0] * 0.8:
            return "falling"
        return "stable"

    def summary(self) -> dict:
        return {
            "session_id": self._session_id,
            "total_windows": len(self._scores),
            "avg_risk": round(sum(self._scores) / len(self._scores), 4) if self._scores else 0.0,
            "max_risk": round(max(self._scores), 4) if self._scores else 0.0,
            "warnings": len(self._warnings),
            "warning_details": self._warnings[-5:] if self._warnings else [],
            "final_verdict": "suspicious" if (self._scores and sum(self._scores) / len(self._scores) > 0.3) else "normal",
        }


class SessionManager:
    def __init__(self):
        self._sessions: dict = {}

    def get_or_create(self, session_id: str, config: DetectionConfig = None) -> StreamingDetector:
        if session_id not in self._sessions:
            self._sessions[session_id] = StreamingDetector(config=config)
            self._sessions[session_id].start_session(session_id)
        return self._sessions[session_id]

    def remove(self, session_id: str):
        self._sessions.pop(session_id, None)

    def cleanup(self, max_age_sec: float = 300):
        now = time.time()
        stale = [
            sid for sid, det in self._sessions.items()
            if now - getattr(det, "_created_at", now) > max_age_sec
        ]
        for sid in stale:
            self.remove(sid)