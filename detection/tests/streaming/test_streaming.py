import math
import random
import time

import pytest

from server.models import GPSPoint
from server.streaming.window import SlidingWindow, StreamingDetector, SessionManager
from server.streaming.scorer import ProgressiveScorer


def make_point(lon, lat, ts=None, accuracy=8.0):
    return GPSPoint(lon=lon, lat=lat, accuracy=accuracy,
                    timestamp=ts or time.time())


class TestSlidingWindow:
    def test_add_and_window(self):
        w = SlidingWindow(window_sec=10, stride_sec=5)
        t0 = 1000.0
        for i in range(20):
            w.add_point(make_point(106.57, 29.50, ts=t0 + i * 0.5))
        win = w.current_window()
        assert len(win) > 0
        assert win[0].timestamp >= t0 + 10 - 10

    def test_should_evaluate(self):
        w = SlidingWindow(window_sec=10, stride_sec=5)
        assert w.should_evaluate(0.0)
        assert not w.should_evaluate(2.0)
        assert w.should_evaluate(5.0)


class TestStreamingDetector:
    def test_feed_normal(self):
        det = StreamingDetector()
        det.start_session("test1")
        t0 = time.time()
        results = []
        for i in range(30):
            p = make_point(
                106.57 + random.uniform(-0.0001, 0.0001),
                29.50 + random.uniform(-0.0001, 0.0001),
                ts=t0 + i * 0.5,
                accuracy=random.uniform(3, 15),
            )
            r = det.feed(p)
            if r:
                results.append(r)
        assert len(results) >= 2
        summary = det.summary()
        assert summary["total_windows"] >= 2

    def test_suspicious_detected(self):
        det = StreamingDetector()
        det.start_session("test2")
        t0 = time.time()
        for i in range(30):
            p = make_point(
                106.57 + 0.0001, 29.50 + 0.0001,
                ts=t0 + i * 0.4,
                accuracy=5.0,
            )
            det.feed(p)
        summary = det.summary()
        assert summary["total_windows"] > 0

    def test_trend_computation(self):
        det = StreamingDetector()
        det._scores.extend([0.1, 0.2, 0.3, 0.4, 0.5])
        assert det._compute_trend() == "rising"
        det._scores.extend([0.5, 0.4, 0.3, 0.2, 0.1])
        assert det._compute_trend() == "falling"


class TestProgressiveScorer:
    def test_normal(self):
        s = ProgressiveScorer()
        r = s.evaluate([0.1, 0.15, 0.12, 0.18, 0.14])
        assert r["level"] == "normal"

    def test_warning(self):
        s = ProgressiveScorer(early_warning_threshold=0.2, alert_threshold=0.8)
        r = s.evaluate([0.1, 0.2, 0.3, 0.35, 0.32])
        assert r["level"] == "warning"

    def test_alert(self):
        s = ProgressiveScorer(alert_threshold=0.6)
        r = s.evaluate([0.1, 0.2, 0.3, 0.7])
        assert r["level"] == "alert"

    def test_rising_trend(self):
        s = ProgressiveScorer(early_warning_threshold=0.5)
        r = s.evaluate([0.1, 0.2, 0.3, 0.4, 0.45])
        assert r["level"] == "watch"
        assert r["trend"] == "rising"

    def test_insufficient(self):
        s = ProgressiveScorer()
        r = s.evaluate([0.1])
        assert r["level"] == "normal"


class TestSessionManager:
    def test_create_and_remove(self):
        mgr = SessionManager()
        det = mgr.get_or_create("s1")
        assert det is not None
        mgr.remove("s1")
        assert "s1" not in mgr._sessions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])