import sys, time, math
sys.path.insert(0, 'detection')
from server.models import GPSPoint, SensorFrame, TraceRequest
from rules.config import DEFAULT_CONFIG
from rules.engine import RuleEngine
from rules.risk_scorer import RiskScorer

def make_point(lon, lat, accuracy=8.0, ts=None):
    return GPSPoint(lon=lon, lat=lat, accuracy=accuracy, timestamp=ts or time.time())

def make_trace(points, sensors=None, account='a', fp=None):
    return TraceRequest(trace_id='t', gps_points=points, sensors=sensors or [], account_id=account, device_fingerprint=fp or {})

engine = RuleEngine(config=DEFAULT_CONFIG)
scorer = RiskScorer(config=DEFAULT_CONFIG)

t0 = time.time()
lat, lon = 29.50, 106.57
points = []
for i in range(100):
    lat += 0.00005
    lon += 0.00005
    ts = t0 + i * 0.4
    points.append(make_point(lon, lat, accuracy=5.0, ts=ts))
trace = make_trace(points, sensors=None, account='user2', fp={'build':'sdk_phone_arm64','sensor_count':3,'device_id':'dev2'})
results = engine.evaluate(trace)
for r in results:
    print(f"{r.rule_name:20s} passed={r.passed} score={r.score:.3f}")
risk = scorer.score(results)
print('risk', risk, 'verdict', scorer.verdict(risk))
