"""
评估指标 — 召回率/误报率统计 + 评估看板。

流程：
  1. 加载基线数据（正常 + 攻击）
  2. 运行检测规则引擎 + ML 模型
  3. 统计召回率 (Recall) 和误报率 (FPR)
  4. 输出评估报告
"""

import json
import math
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "detection"))

from server.models import GPSPoint, SensorFrame, TraceRequest
from rules.config import DEFAULT_CONFIG, DetectionConfig
from rules.engine import RuleEngine
from rules.risk_scorer import RiskScorer

from baselines.synthetic_traces import TraceSample, generate_dataset
from models.trajectory_clustering import TrajectoryCluster
from models.behavioral_anomaly import BehavioralAnomalyDetector
from models.sensor_consistency_model import SensorConsistencyModel


def geo_dist_m(lat1, lon1, lat2, lon2) -> float:
    return math.hypot(lat2 - lat1, lon2 - lon1) * 111_320


def sample_to_trace_request(sample: TraceSample) -> TraceRequest:
    gps_points = []
    sensors = []
    for i, (lon, lat, t) in enumerate(sample.gps_points):
        gps_points.append(GPSPoint(
            lon=lon, lat=lat,
            accuracy=sample.accuracy_values[i] if i < len(sample.accuracy_values) else 8.0,
            timestamp=t,
        ))
        sensors.append(SensorFrame(
            timestamp=t,
            step_count=int(sample.step_rates[i]) if i < len(sample.step_rates) else 0,
        ))
    return TraceRequest(
        trace_id=sample.trace_id,
        gps_points=gps_points,
        sensors=sensors,
        account_id="eval",
        device_fingerprint={"eval": True},
    )


class Evaluator:
    def __init__(self, config: DetectionConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.engine = RuleEngine(config=self.config)
        self.scorer = RiskScorer(config=self.config)
        self.cluster_model = TrajectoryCluster()
        self.behavior_model = BehavioralAnomalyDetector()
        self.sensor_model = SensorConsistencyModel()

    def evaluate_trace(self, trace: TraceSample) -> dict:
        req = sample_to_trace_request(trace)

        rule_results = self.engine.evaluate(req)
        rule_risk = self.scorer.score(rule_results)
        rule_verdict = self.scorer.verdict(rule_risk)

        # ML 模型评估
        coords = [(p[0], p[1]) for p in trace.gps_points]
        speeds = trace.speeds
        timestamps = trace.timestamps
        step_rates = trace.step_rates

        behavior = self.behavior_model.evaluate(speeds, timestamps)
        sensor = self.sensor_model.score(speeds, step_rates)
        ml_risk = max(
            behavior.get("risk", 0),
            sensor.get("score", 0),
        )

        combined_risk = max(rule_risk, ml_risk)
        is_attack = trace.label.startswith("attack")

        return {
            "trace_id": trace.trace_id,
            "label": trace.label,
            "is_attack": is_attack,
            "rule_risk": round(rule_risk, 4),
            "rule_verdict": rule_verdict,
            "ml_risk": round(ml_risk, 4),
            "combined_risk": round(combined_risk, 4),
            "detected": combined_risk > 0.3,
            "rule_results": {
                r.rule_name: {"passed": r.passed, "score": r.score}
                for r in rule_results
            },
            "behavior": behavior,
            "sensor_consistency": sensor,
        }

    def evaluate_dataset(self, dataset: List[TraceSample]) -> dict:
        results = [self.evaluate_trace(t) for t in dataset]

        return self._compute_metrics(results)

    def _compute_metrics(self, results: List[dict]) -> dict:
        attacks = [r for r in results if r["is_attack"]]
        normals = [r for r in results if not r["is_attack"]]

        tp = sum(1 for r in attacks if r["detected"])
        fn = len(attacks) - tp
        fp = sum(1 for r in normals if r["detected"])
        tn = len(normals) - fp

        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        per_type = {}
        for r in results:
            label = r["label"]
            if label not in per_type:
                per_type[label] = {"total": 0, "detected": 0, "avg_risk": []}
            per_type[label]["total"] += 1
            if r["detected"]:
                per_type[label]["detected"] += 1
            per_type[label]["avg_risk"].append(r["combined_risk"])

        for v in per_type.values():
            v["recall"] = v["detected"] / v["total"] if v["total"] > 0 else 0
            v["avg_risk"] = round(float(np.mean(v["avg_risk"])), 4) if v["avg_risk"] else 0

        return {
            "total_samples": len(results),
            "attacks": len(attacks),
            "normals": len(normals),
            "true_positives": tp,
            "false_negatives": fn,
            "false_positives": fp,
            "true_negatives": tn,
            "recall": round(recall, 4),
            "fpr": round(fpr, 4),
            "precision": round(precision, 4),
            "f1_score": round(f1, 4),
            "per_type": per_type,
            "threshold": 0.3,
        }


def print_report(metrics: dict):
    print("=" * 60)
    print("  Budao Lepao Detection - Evaluation Report")
    print("=" * 60)
    print(f"  Total samples:  {metrics['total_samples']}")
    print(f"  Attacks:        {metrics['attacks']}")
    print(f"  Normals:        {metrics['normals']}")
    print(f"  Threshold:      {metrics['threshold']}")
    print("-" * 60)
    print(f"  True Positives:  {metrics['true_positives']}")
    print(f"  False Negatives: {metrics['false_negatives']}")
    print(f"  False Positives: {metrics['false_positives']}")
    print(f"  True Negatives:  {metrics['true_negatives']}")
    print("-" * 60)
    print(f"  Recall (TPR):    {metrics['recall']:.2%}")
    print(f"  FPR:             {metrics['fpr']:.2%}")
    print(f"  Precision:       {metrics['precision']:.2%}")
    print(f"  F1 Score:        {metrics['f1_score']:.2%}")
    print("-" * 60)
    print("  Per-Type Recall:")
    for label, v in sorted(metrics["per_type"].items()):
        bar = "#" * int(v["recall"] * 20)
        print(f"    {label:20s}  {v['recall']:.0%}  {v['detected']}/{v['total']}  "
              f"avg_risk={v['avg_risk']:.2f}  {bar}")
    print("=" * 60)


def run_eval(n_normal: int = 20, n_attack: int = 20):
    dataset = generate_dataset(n_normal, n_attack)
    print(f"Generated {len(dataset)} traces ({n_normal} normal, {n_attack} attack)")

    # 训练传感器一致性模型
    sensor_model = SensorConsistencyModel()
    normal_speeds, normal_steps = [], []
    for t in dataset:
        if t.label == "normal":
            normal_speeds.extend(t.speeds)
            normal_steps.extend(t.step_rates)
    if normal_speeds:
        sensor_model.fit(normal_speeds, normal_steps)
        print(f"Trained sensor model on {len(normal_speeds)} normal samples")

    evaluator = Evaluator()
    evaluator.sensor_model = sensor_model

    metrics = evaluator.evaluate_dataset(dataset)
    print_report(metrics)
    return metrics


if __name__ == "__main__":
    run_eval(30, 30)