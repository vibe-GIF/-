"""
统一检测管线 — 将规则引擎 + 主动探测 + 流式检测合并为一个入口。
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from server.models import GPSPoint, TraceRequest
from rules.config import DEFAULT_CONFIG
from rules.engine import RuleEngine
from rules.risk_scorer import RiskScorer
from server.streaming.window import StreamingDetector, SessionManager
from server.streaming.scorer import ProgressiveScorer
from server.proactive.tls_fingerprint import TLSFingerprint, TLSFingerprintDetector
from server.proactive.tcp_stack import TCPStackInfo, TCPStackDetector
from server.proactive.timing_analysis import RequestTimingAnalyzer
from server.proactive.integrator import ProactiveDetector


class UnifiedDetector:
    def __init__(self):
        self.config = DEFAULT_CONFIG
        self.engine = RuleEngine(config=self.config)
        self.scorer = RiskScorer(config=self.config)
        self.proactive = ProactiveDetector()
        self.session_manager = SessionManager()
        self.progressive = ProgressiveScorer()
        self.timing = RequestTimingAnalyzer()

    def detect_trace(self, trace: TraceRequest) -> dict:
        rule_results = self.engine.evaluate(trace)
        risk = self.scorer.score(rule_results)
        verdict = self.scorer.verdict(risk)
        return {
            "trace_id": trace.trace_id,
            "risk": round(risk, 4),
            "verdict": verdict,
            "rule_results": {
                r.rule_name: {"passed": r.passed, "score": r.score}
                for r in rule_results
            },
        }

    def detect_proactive(self, tls_fp: dict = None, tcp_info: dict = None,
                         timing_intervals: list = None) -> dict:
        tls = TLSFingerprint(**tls_fp) if tls_fp else None
        tcp = TCPStackInfo(**tcp_info) if tcp_info else None
        result = self.proactive.analyze_all(
            tls_fp=tls, tcp_info=tcp, timing_intervals=timing_intervals,
        )
        return result

    def start_session(self, session_id: str, account_id: str = ""):
        det = self.session_manager.get_or_create(session_id)
        det.start_session(session_id, account_id)
        return det

    def feed(self, session_id: str, point: GPSPoint) -> dict:
        det = self.session_manager.get_or_create(session_id)
        result = det.feed(point)
        if result:
            scores = list(det._scores)
            level = self.progressive.evaluate(scores)
            result["progressive_level"] = level
        return result

    def session_summary(self, session_id: str) -> dict:
        det = self.session_manager._sessions.get(session_id)
        if not det:
            return {"error": "session_not_found"}
        summary = det.summary()
        summary["progressive_level"] = self.progressive.evaluate(list(det._scores))
        return summary

    def record_timing(self):
        self.timing.record()

    def full_detect(self, trace: TraceRequest,
                    tls_fp: dict = None, tcp_info: dict = None,
                    timing_intervals: list = None) -> dict:
        trace_result = self.detect_trace(trace)
        proactive_result = self.detect_proactive(tls_fp, tcp_info, timing_intervals)
        return {
            "trace": trace_result,
            "proactive": proactive_result,
            "combined_risk": round(
                max(trace_result["risk"], proactive_result.get("score", 0)), 4
            ),
        }