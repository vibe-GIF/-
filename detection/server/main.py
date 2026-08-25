import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from server.models import DetectionResponse, RuleResult, TraceRequest
from rules.config import DEFAULT_CONFIG, DetectionConfig
from rules.engine import RuleEngine
from rules.risk_scorer import RiskScorer

app = FastAPI(title="Budao Lepao Detection API", version="0.1.0")
engine = RuleEngine(config=DEFAULT_CONFIG)
scorer = RiskScorer(config=DEFAULT_CONFIG)


class HealthResponse(BaseModel):
    status: str
    rules: List[str]


@app.get("/")
def index():
    from fastapi.responses import HTMLResponse
    html = """
    <html><head><title>Budao Lepao Detection</title>
    <style>body{font-family:monospace;background:#111;color:#eee;padding:40px}
    h1{color:#6f6}a{color:#6cf}li{margin:6px}</style></head>
    <body><h1>Budao Lepao Detection API</h1>
    <p>Service running. Endpoints:</p>
    <ul>
      <li><a href="/health">GET /health</a> - health check</li>
      <li>POST /api/detect - trace detection</li>
      <li>POST /api/detect/batch - batch detection</li>
      <li>POST /api/fingerprint - fingerprint check</li>
      <li>POST /api/proactive/detect - proactive probe</li>
      <li>POST /api/streaming/start|feed|summary|stop - streaming</li>
      <li>POST /api/challenge/generate|verify - challenge</li>
    </ul>
    </body></html>
    """
    return HTMLResponse(content=html)


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(
        status="ok",
        rules=list(engine._rules.keys()),
    )


@app.post("/api/detect", response_model=DetectionResponse)
def detect(trace: TraceRequest):
    if len(trace.gps_points) < 2:
        raise HTTPException(status_code=400, detail="At least 2 GPS points required")
    rule_results = engine.evaluate(trace)
    risk = scorer.score(rule_results)
    verdict = scorer.verdict(risk)
    return DetectionResponse(
        trace_id=trace.trace_id,
        overall_risk=round(risk, 4),
        verdict=verdict,
        rule_results=rule_results,
        processed_at=time.time(),
    )


@app.post("/api/detect/batch", response_model=List[DetectionResponse])
def detect_batch(traces: List[TraceRequest]):
    responses = []
    for trace in traces:
        rule_results = engine.evaluate(trace)
        risk = scorer.score(rule_results)
        verdict = scorer.verdict(risk)
        responses.append(
            DetectionResponse(
                trace_id=trace.trace_id,
                overall_risk=round(risk, 4),
                verdict=verdict,
                rule_results=rule_results,
                processed_at=time.time(),
            )
        )
    return responses


@app.post("/api/fingerprint")
def fingerprint(data: dict):
    fp = data.get("build", {})
    sensors = data.get("sensors", {})
    env = data.get("environment", {})

    reasons = []
    is_emulator = False

    build_str = " ".join(str(v) for v in fp.values()).lower()
    emu_sigs = ["sdk_phone", "emu64", "generic", "vbox", "mumu"]
    for sig in emu_sigs:
        if sig in build_str:
            reasons.append(f"build_sig:{sig}")
            is_emulator = True

    sensor_count = sensors.get("sensor_count", 0)
    if sensor_count < 8 and sensor_count > 0:
        reasons.append(f"low_sensors:{sensor_count}")
        is_emulator = True

    props = env.get("props", {})
    for prop, val in props.items():
        if prop in ("ro.kernel.qemu",) and val == "1":
            reasons.append(f"suspicious_prop:{prop}={val}")
            is_emulator = True

    if env.get("is_emulator"):
        reasons.extend(env.get("emulator_reasons", []))
        is_emulator = True

    return {
        "status": "ok",
        "is_emulator": is_emulator,
        "risk_score": 0.9 if is_emulator else 0.0,
        "reasons": reasons,
    }


from .proactive.tls_fingerprint import TLSFingerprint, TLSFingerprintDetector
from .proactive.tcp_stack import TCPStackInfo, TCPStackDetector
from .proactive.timing_analysis import RequestTimingAnalyzer
from .proactive.challenge import ChallengeManager, EnvironmentProofBuilder
from .proactive.integrator import ProactiveDetector
from .streaming.window import SessionManager, StreamingDetector
from .streaming.scorer import ProgressiveScorer

proactive = ProactiveDetector()
timing_analyzer = RequestTimingAnalyzer()
session_manager = SessionManager()
progressive_scorer = ProgressiveScorer()


@app.post("/api/proactive/detect")
def proactive_detect(data: dict):
    tls_fp = None
    if "tls" in data:
        tls_fp = TLSFingerprint(**data["tls"])

    tcp_info = None
    if "tcp" in data:
        tcp_info = TCPStackInfo(**data["tcp"])

    intervals = data.get("timing_intervals")

    result = proactive.analyze_all(
        tls_fp=tls_fp,
        tcp_info=tcp_info,
        timing_intervals=intervals,
    )

    return {
        "status": "ok",
        "proactive_score": result["score"],
        "is_emulator": result["anomaly"],
        "reasons": result["reasons"],
        "details": {k: v for k, v in result["details"].items()},
    }


@app.post("/api/challenge/generate")
def generate_challenge():
    ch = proactive.challenge.generate("proof")
    return ch


@app.post("/api/challenge/verify")
def verify_challenge(data: dict):
    challenge_id = data.get("challenge_id", "")
    response = data.get("response", "")
    result = proactive.challenge.verify(challenge_id, response)
    return result


@app.post("/api/streaming/start")
def streaming_start(data: dict):
    session_id = data.get("session_id", f"run_{int(time.time())}")
    account_id = data.get("account_id", "")
    det = session_manager.get_or_create(session_id)
    det.start_session(session_id, account_id)
    return {"session_id": session_id, "status": "started"}


@app.post("/api/streaming/feed")
def streaming_feed(data: dict):
    session_id = data.get("session_id", "")
    point = GPSPoint(**data.get("point", {}))
    det = session_manager.get_or_create(session_id)
    result = det.feed(point)
    if result:
        level = progressive_scorer.evaluate(list(det._scores))
        result["progressive_level"] = level
    return {
        "status": "ok",
        "result": result,
        "pending": result is None,
    }


@app.post("/api/streaming/summary")
def streaming_summary(data: dict):
    session_id = data.get("session_id", "")
    det = session_manager._sessions.get(session_id)
    if not det:
        return {"error": "session_not_found"}
    return det.summary()


@app.post("/api/streaming/stop")
def streaming_stop(data: dict):
    session_id = data.get("session_id", "")
    det = session_manager._sessions.get(session_id)
    if not det:
        return {"error": "session_not_found"}
    summary = det.summary()
    summary["progressive_level"] = progressive_scorer.evaluate(
        list(det._scores)
    )
    session_manager.remove(session_id)
    summary["session_ended"] = True
    return summary


@app.middleware("http")
async def record_timing(request, call_next):
    timing_analyzer.record()
    response = await call_next(request)
    return response


if __name__ == "__main__":
    import uvicorn
    print("Detection server at http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)