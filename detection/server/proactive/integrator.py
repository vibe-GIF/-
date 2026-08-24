"""
主动探测集成器 — 将 TLS 指纹、TCP 栈指纹、时序分析、挑战验证
整合为统一的风险评分。
"""

from typing import Dict, List, Optional

from .tls_fingerprint import TLSFingerprint, TLSFingerprintDetector
from .tcp_stack import TCPStackInfo, TCPStackDetector
from .timing_analysis import RequestTimingAnalyzer
from .challenge import ChallengeManager


class ProactiveDetector:
    def __init__(self):
        self.tls = TLSFingerprintDetector()
        self.tcp = TCPStackDetector()
        self.timing = RequestTimingAnalyzer()
        self.challenge = ChallengeManager()

    def analyze_all(self, tls_fp: TLSFingerprint = None,
                    tcp_info: TCPStackInfo = None,
                    timing_intervals: List[float] = None) -> dict:
        results = {}
        total_score = 0.0
        all_reasons = []

        if tls_fp:
            r = self.tls.analyze(tls_fp)
            results["tls_fingerprint"] = r
            total_score += r["score"]
            all_reasons.extend(r["reasons"])

        if tcp_info:
            r = self.tcp.analyze(tcp_info)
            results["tcp_stack"] = r
            total_score += r["score"]
            all_reasons.extend(r["reasons"])

        if timing_intervals:
            r = self.timing.analyze(timing_intervals)
            results["timing"] = r
            total_score += r["score"]
            all_reasons.extend(r["reasons"])

        n = len(results) if results else 1
        avg_score = total_score / n if results else 0.0

        return {
            "score": round(avg_score, 4),
            "anomaly": avg_score > 0.3,
            "reasons": all_reasons,
            "details": results,
        }