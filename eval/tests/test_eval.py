import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import numpy as np

from baselines.synthetic_traces import (
    generate_normal_trace,
    generate_attack_trace,
    generate_dataset,
    GPSSimulator,
)
from models.trajectory_clustering import (
    TrajectoryCluster,
    dtw_distance,
    grid_jaccard,
)
from models.behavioral_anomaly import (
    BehavioralAnomalyDetector,
    pace_analysis,
    time_anomaly,
)
from models.sensor_consistency_model import (
    SensorConsistencyModel,
    compute_gps_speeds,
)


class TestSyntheticTraces:
    def test_generate_normal(self):
        t = generate_normal_trace("test", 50)
        assert t.label == "normal"
        assert len(t.gps_points) == 50
        assert all(1 <= s <= 7 for s in t.speeds)

    def test_generate_attack(self):
        for atype in ["emulator", "script", "enhanced"]:
            t = generate_attack_trace(f"test_{atype}", 50, attack_type=atype)
            assert t.label == f"attack_{atype}"
            assert len(t.gps_points) == 50

    def test_generate_dataset(self):
        ds = generate_dataset(10, 10)
        assert len(ds) == 20
        normals = [t for t in ds if t.label == "normal"]
        attacks = [t for t in ds if "attack" in t.label]
        assert len(normals) == 10
        assert len(attacks) == 10

    def test_gps_simulator(self):
        gps = GPSSimulator()
        dx, dy = gps.step(0.4)
        assert isinstance(dx, float)
        assert isinstance(dy, float)


class TestTrajectoryClustering:
    def test_dtw_distance(self):
        a = [(106.57, 29.50), (106.58, 29.51)]
        b = [(106.57, 29.50), (106.58, 29.51)]
        d = dtw_distance(a, b)
        assert d >= 0

    def test_grid_jaccard(self):
        a = [(106.57, 29.50), (106.58, 29.51)]
        b = [(106.57, 29.50), (106.58, 29.51)]
        j = grid_jaccard(a, b)
        assert j >= 0

    def test_cluster(self):
        traces = [
            [(106.57, 29.50), (106.58, 29.51)],
            [(106.57, 29.50), (106.58, 29.51)],
            [(106.90, 30.00), (106.91, 30.01)],
        ]
        model = TrajectoryCluster(eps=500, min_samples=2)
        model.fit(traces)
        labels = model.labels()
        assert len(labels) == 3


class TestBehavioralAnomaly:
    def test_pace_normal(self):
        speeds = [3.0, 3.5, 4.0, 3.8, 4.2]
        r = pace_analysis(speeds)
        assert not r["is_suspicious"]

    def test_pace_too_constant(self):
        speeds = [4.5] * 20
        r = pace_analysis(speeds)
        assert r["is_suspicious"]

    def test_time_normal(self):
        ts = [0.0, 1.2, 2.5, 3.8, 5.0]
        r = time_anomaly(ts)
        assert not r["is_suspicious"]

    def test_time_too_regular(self):
        ts = [0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4]
        r = time_anomaly(ts)
        assert r["is_suspicious"]

    def test_detector(self):
        det = BehavioralAnomalyDetector()
        r = det.evaluate(
            [4.5] * 20, [i * 0.4 for i in range(20)],
            device_id="dev1", account_id="user1",
        )
        assert r["anomaly"]


class TestSensorConsistency:
    def test_score_normal(self):
        model = SensorConsistencyModel()
        speeds = [3.0, 3.5, 4.0, 4.5, 5.0]
        steps = [1.5, 1.8, 2.0, 2.2, 2.5]
        r = model.score(speeds, steps)
        assert not r["anomaly"]

    def test_score_uncorrelated(self):
        model = SensorConsistencyModel()
        speeds = [3.0, 3.5, 4.0, 4.5, 5.0]
        steps = [0.0, 0.0, 0.0, 0.0, 0.0]
        r = model.score(speeds, steps)
        assert r["anomaly"]

    def test_fit_and_predict(self):
        model = SensorConsistencyModel()
        model.fit([3.0, 4.0, 5.0], [1.5, 2.0, 2.5])
        pred = model.predict_step_rate(4.0)
        assert 1.5 <= pred <= 2.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])