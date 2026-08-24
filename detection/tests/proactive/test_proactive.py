import pytest

from server.proactive.tls_fingerprint import (
    TLSFingerprint,
    TLSFingerprintDetector,
    compute_ja3,
)
from server.proactive.tcp_stack import TCPStackInfo, TCPStackDetector
from server.proactive.timing_analysis import RequestTimingAnalyzer
from server.proactive.challenge import ChallengeManager, EnvironmentProofBuilder
from server.proactive.integrator import ProactiveDetector


class TestTLSFingerprint:
    def test_emulator_ja3_detected(self):
        det = TLSFingerprintDetector()
        fp = TLSFingerprint(ja3="d5f0e0c0b1e0c0b1e0c0b1e0c0b1e0c")
        r = det.analyze(fp)
        assert r["anomaly"]
        assert any("emulator" in reason for reason in r["reasons"])

    def test_unknown_ja3_scored(self):
        det = TLSFingerprintDetector()
        fp = TLSFingerprint(ja3="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
        r = det.analyze(fp)
        assert r["score"] >= 0.2

    def test_clean_android_ja3(self):
        det = TLSFingerprintDetector()
        fp = TLSFingerprint(
            ja3="6734f37431670b3ab4292b8f60f29984",
            user_agent="okhttp/4.12.0 (Android 14)",
        )
        r = det.analyze(fp)
        assert not r["anomaly"]

    def test_compute_ja3(self):
        ja3 = compute_ja3(
            tls_version=771,
            cipher_suites=[4865, 4866, 4867],
            extensions=[0, 23, 65281],
            elliptic_curves=[29, 23, 24],
            ec_point_formats=[0],
        )
        assert len(ja3) == 32
        assert isinstance(ja3, str)


class TestTCPStack:
    def test_windows_ttl_detected(self):
        det = TCPStackDetector()
        info = TCPStackInfo(ttl=128, window_size=65535, window_scaling=8, mss=1460, tcp_timestamp=True)
        r = det.analyze(info)
        assert r["anomaly"]
        assert any("windows" in reason for reason in r["reasons"])

    def test_android_ttl_passes(self):
        det = TCPStackDetector()
        info = TCPStackInfo(ttl=64, window_size=29200, window_scaling=7, mss=1440, tcp_timestamp=True)
        r = det.analyze(info)
        assert not r["anomaly"]

    def test_timestamp_disabled(self):
        det = TCPStackDetector()
        info = TCPStackInfo(ttl=64, window_size=29200, window_scaling=7, mss=1440, tcp_timestamp=False)
        r = det.analyze(info)
        assert r["anomaly"]

    def test_no_data(self):
        det = TCPStackDetector()
        r = det.analyze(TCPStackInfo())
        assert not r["anomaly"]


class TestTimingAnalysis:
    def test_regular_intervals_detected(self):
        analyzer = RequestTimingAnalyzer()
        intervals = [0.4] * 20
        r = analyzer.analyze(intervals)
        assert r["anomaly"]

    def test_natural_intervals_pass(self):
        analyzer = RequestTimingAnalyzer()
        import random
        intervals = [random.uniform(0.5, 2.0) for _ in range(20)]
        r = analyzer.analyze(intervals)
        assert not r["anomaly"]

    def test_insufficient_data(self):
        analyzer = RequestTimingAnalyzer()
        r = analyzer.analyze([0.4, 0.5])
        assert not r["anomaly"]

    def test_record(self):
        analyzer = RequestTimingAnalyzer()
        import time
        for _ in range(10):
            analyzer.record(time.time())
            time.sleep(0.01)
        r = analyzer.analyze()
        assert r["sample_count"] >= 5


class TestChallenge:
    def test_challenge_verify_passes(self):
        mgr = ChallengeManager()
        ch = mgr.generate("proof")
        proof = mgr.generate_proof(ch["challenge_id"], ch["nonce"],
                                    ch["timestamp"], ch["type"])
        r = mgr.verify(ch["challenge_id"], proof)
        assert r["passed"]

    def test_challenge_wrong_response_fails(self):
        mgr = ChallengeManager()
        ch = mgr.generate("proof")
        r = mgr.verify(ch["challenge_id"], "wrong")
        assert not r["passed"]

    def test_challenge_not_found(self):
        mgr = ChallengeManager()
        r = mgr.verify("nonexistent", "proof")
        assert not r["passed"]

    def test_env_proof_builder(self):
        fp = {
            "build": {"fingerprint": "test/fingerprint", "serial": "abc123"},
            "environment": {"android_id": "def456"},
            "sensors": {"sensor_count": 12},
        }
        proof = EnvironmentProofBuilder.build_proof(fp)
        assert len(proof) == 64


class TestProactiveDetector:
    def test_full_analysis(self):
        det = ProactiveDetector()
        r = det.analyze_all(
            tls_fp=TLSFingerprint(ja3="d5f0e0c0b1e0c0b1e0c0b1e0c0b1e0c"),
            tcp_info=TCPStackInfo(ttl=128, window_size=65535, window_scaling=8, mss=1460, tcp_timestamp=True),
            timing_intervals=[0.4] * 20,
        )
        assert r["anomaly"]
        assert r["score"] > 0.3
        assert len(r["reasons"]) >= 3

    def test_clean_analysis(self):
        det = ProactiveDetector()
        r = det.analyze_all(
            tls_fp=TLSFingerprint(
                ja3="6734f37431670b3ab4292b8f60f29984",
                user_agent="okhttp/4.12.0 (Android 14)",
            ),
            tcp_info=TCPStackInfo(ttl=64, window_size=29200, window_scaling=7, mss=1440, tcp_timestamp=True),
            timing_intervals=[0.5, 0.8, 1.2, 0.6, 1.5, 0.9, 1.1, 0.7, 1.3, 0.4],
        )
        assert not r["anomaly"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])