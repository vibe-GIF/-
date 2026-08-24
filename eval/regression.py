"""
M5: 召回/误报回归与调优

对规则阈值进行网格搜索，在 Recall 和 FPR 之间寻找最优平衡点，
输出调优后的配置文件，并生成回归测试报告。
"""

import copy
import itertools
import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent / "detection"))

from server.models import GPSPoint, SensorFrame, TraceRequest
from rules.config import (
    DEFAULT_CONFIG,
    DetectionConfig,
    AccuracyStabilityConfig,
    MockDetectionConfig,
    NoiseSpectrumConfig,
    SensorConsistencyConfig,
    SpeedPhysiologicalConfig,
)
from rules.engine import RuleEngine
from rules.risk_scorer import RiskScorer
from baselines.synthetic_traces import TraceSample, generate_dataset


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


@dataclass
class EvalResult:
    threshold: float
    tp: int
    fn: int
    fp: int
    tn: int
    recall: float
    fpr: float
    precision: float
    f1: float
    per_type: Dict[str, float]


def evaluate_dataset(
    dataset: List[TraceSample],
    config: DetectionConfig,
    threshold: float,
) -> EvalResult:
    engine = RuleEngine(config=config)
    scorer = RiskScorer(config=config)

    results = []
    for sample in dataset:
        req = sample_to_trace_request(sample)
        rule_results = engine.evaluate(req)
        risk = scorer.score(rule_results)
        is_attack = sample.label.startswith("attack")
        results.append({
            "label": sample.label,
            "is_attack": is_attack,
            "risk": risk,
            "detected": risk > threshold,
        })

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
            per_type[label] = {"total": 0, "detected": 0}
        per_type[label]["total"] += 1
        if r["detected"]:
            per_type[label]["detected"] += 1
    per_type_recall = {
        k: v["detected"] / v["total"] if v["total"] > 0 else 0
        for k, v in per_type.items()
    }

    return EvalResult(
        threshold=threshold,
        tp=tp, fn=fn, fp=fp, tn=tn,
        recall=recall, fpr=fpr, precision=precision, f1=f1,
        per_type=per_type_recall,
    )


# ============================================================
#  阈值扫描
# ============================================================

def threshold_scan(
    dataset: List[TraceSample],
    config: DetectionConfig = None,
    thresholds: List[float] = None,
) -> List[EvalResult]:
    config = config or DEFAULT_CONFIG
    thresholds = thresholds or [round(t, 2) for t in np.arange(0.05, 0.95, 0.05)]

    results = []
    for t in thresholds:
        r = evaluate_dataset(dataset, config, t)
        results.append(r)
    return results


# ============================================================
#  规则参数网格搜索
# ============================================================

@dataclass
class TuningResult:
    params: dict
    score: float
    recall: float
    fpr: float
    f1: float


def grid_search(
    dataset: List[TraceSample],
    n_trials: int = 50,
) -> TuningResult:
    best = None
    best_score = -1.0

    for _ in range(n_trials):
        config = copy.deepcopy(DEFAULT_CONFIG)

        config.accuracy_stability.accuracy_variance_min = np.random.uniform(0.005, 0.05)
        config.speed_physiological.max_instant_speed = np.random.uniform(8.0, 15.0)
        config.speed_physiological.max_acceleration = np.random.uniform(5.0, 15.0)
        config.speed_physiological.max_speed_variance = np.random.uniform(0.05, 0.5)
        config.noise_spectrum.autocorr_threshold = np.random.uniform(0.1, 0.5)
        config.sensor_consistency.speed_step_corr_min = np.random.uniform(0.15, 0.5)

        for rule_name in [
            "mock_detection", "accuracy_stability", "speed_physiological",
            "noise_spectrum", "sensor_consistency", "emulator_fingerprint",
            "trajectory_similarity", "multi_account", "request_integrity",
        ]:
            cfg = getattr(config, rule_name)
            if hasattr(cfg, "weight"):
                cfg.weight = np.random.uniform(0.5, 2.0)

        r = evaluate_dataset(dataset, config, threshold=0.3)

        score = r.f1 - r.fpr * 2.0

        if score > best_score:
            best_score = score
            best = TuningResult(
                params={
                    "accuracy_variance_min": config.accuracy_stability.accuracy_variance_min,
                    "max_instant_speed": config.speed_physiological.max_instant_speed,
                    "max_acceleration": config.speed_physiological.max_acceleration,
                    "max_speed_variance": config.speed_physiological.max_speed_variance,
                    "autocorr_threshold": config.noise_spectrum.autocorr_threshold,
                    "speed_step_corr_min": config.sensor_consistency.speed_step_corr_min,
                },
                score=best_score,
                recall=r.recall,
                fpr=r.fpr,
                f1=r.f1,
            )

    return best


# ============================================================
#  回归测试
# ============================================================

def regression_test(
    dataset: List[TraceSample],
    config: DetectionConfig = None,
    threshold: float = 0.3,
    min_recall: float = 0.95,
    max_fpr: float = 0.05,
) -> dict:
    config = config or DEFAULT_CONFIG
    r = evaluate_dataset(dataset, config, threshold)

    passed = True
    issues = []

    if r.recall < min_recall:
        passed = False
        issues.append(f"Recall {r.recall:.2%} < min {min_recall:.2%}")
    if r.fpr > max_fpr:
        passed = False
        issues.append(f"FPR {r.fpr:.2%} > max {max_fpr:.2%}")

    return {
        "passed": passed,
        "threshold": threshold,
        "recall": r.recall,
        "fpr": r.fpr,
        "f1": r.f1,
        "issues": issues,
        "per_type": r.per_type,
    }


# ============================================================
#  报告生成
# ============================================================

def print_scan_table(results: List[EvalResult]):
    print(f"{'Threshold':>10}  {'Recall':>8}  {'FPR':>8}  {'F1':>8}  {'TP':>4}  {'FP':>4}")
    print("-" * 55)
    for r in results:
        print(
            f"{r.threshold:>10.2f}  "
            f"{r.recall:>7.2%}  "
            f"{r.fpr:>7.2%}  "
            f"{r.f1:>7.2%}  "
            f"{r.tp:>4}  {r.fp:>4}"
        )


def generate_report(
    scan_results: List[EvalResult],
    tuning: TuningResult,
    regression: dict,
    output_path: str = "eval_report.html",
):
    best = max(scan_results, key=lambda r: r.f1 - r.fpr * 2)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Budao Lepao - Eval Report</title>
<style>
  body {{ font-family: monospace; max-width: 900px; margin: 40px auto; padding: 20px; }}
  h1 {{ border-bottom: 2px solid #333; }}
  table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
  th, td {{ border: 1px solid #ccc; padding: 8px; text-align: center; }}
  th {{ background: #f0f0f0; }}
  .pass {{ color: green; font-weight: bold; }}
  .fail {{ color: red; font-weight: bold; }}
  .bar {{ display: inline-block; height: 20px; background: #4caf50; }}
  .bar-container {{ background: #e0e0e0; width: 200px; display: inline-block; }}
  .summary {{ display: flex; gap: 20px; }}
  .card {{ border: 1px solid #ddd; padding: 16px; border-radius: 8px; flex: 1; }}
  .card h3 {{ margin: 0 0 8px 0; }}
</style></head><body>
<h1>Budao Lepao - Detection Evaluation Report</h1>
<p>Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}</p>

<h2>Summary</h2>
<div class="summary">
  <div class="card">
    <h3>Best Threshold</h3>
    <p style="font-size: 24px;">{best.threshold:.2f}</p>
    <p>Recall: {best.recall:.1%} / FPR: {best.fpr:.1%} / F1: {best.f1:.1%}</p>
  </div>
  <div class="card">
    <h3>Regression Test</h3>
    <p style="font-size: 24px;" class="{'pass' if regression['passed'] else 'fail'}">
      {'PASS' if regression['passed'] else 'FAIL'}
    </p>
    <p>Recall: {regression['recall']:.1%} / FPR: {regression['fpr']:.1%}</p>
  </div>
  <div class="card">
    <h3>Grid Search</h3>
    <p>Best F1: {tuning.f1:.1%}</p>
    <p>Recall: {tuning.recall:.1%} / FPR: {tuning.fpr:.1%}</p>
  </div>
</div>

<h2>Threshold Scan</h2>
<table>
  <tr><th>Threshold</th><th>Recall</th><th>FPR</th><th>F1</th><th>TP</th><th>FP</th></tr>
"""
    for r in scan_results:
        html += f"<tr><td>{r.threshold:.2f}</td><td>{r.recall:.1%}</td><td>{r.fpr:.1%}</td><td>{r.f1:.1%}</td><td>{r.tp}</td><td>{r.fp}</td></tr>\n"

    html += """</table>

<h2>Per-Type Recall (best threshold)</h2>
<table>
  <tr><th>Type</th><th>Recall</th></tr>
"""
    for label, recall in sorted(best.per_type.items()):
        bar_w = int(recall * 200)
        html += f"<tr><td>{label}</td><td><div class='bar-container'><div class='bar' style='width:{bar_w}px'></div></div> {recall:.0%}</td></tr>\n"

    html += """</table>

<h2>Optimal Parameters (Grid Search)</h2>
<table>
  <tr><th>Parameter</th><th>Value</th></tr>
"""
    for k, v in tuning.params.items():
        html += f"<tr><td>{k}</td><td>{v:.4f}</td></tr>\n"

    html += f"""</table>

<h2>Regression Test</h2>
<p>Status: <span class="{'pass' if regression['passed'] else 'fail'}">{'PASSED' if regression['passed'] else 'FAILED'}</span></p>
<ul>
"""
    if regression.get("issues"):
        for issue in regression["issues"]:
            html += f"<li class='fail'>{issue}</li>\n"
    else:
        html += "<li>No issues found</li>\n"

    html += """</ul>
</body></html>"""

    Path(output_path).write_text(html, encoding="utf-8")
    print(f"Report saved to {output_path}")


# ============================================================
#  主入口
# ============================================================

def run_m5():
    print("Generating dataset...")
    dataset = generate_dataset(n_normal=50, n_attack=50)
    print(f"  {len(dataset)} traces ({sum(1 for t in dataset if t.label=='normal')} normal, "
          f"{sum(1 for t in dataset if 'attack' in t.label)} attack)")

    print("\nThreshold scan...")
    scan = threshold_scan(dataset)
    print_scan_table(scan)

    print("\nRegression test (threshold=0.3)...")
    regression = regression_test(dataset)
    status = "PASS" if regression["passed"] else "FAIL"
    print(f"  {status}: Recall={regression['recall']:.2%} FPR={regression['fpr']:.2%}")

    print("\nGrid search...")
    tuning = grid_search(dataset, n_trials=100)
    print(f"  Best: F1={tuning.f1:.2%} Recall={tuning.recall:.2%} FPR={tuning.fpr:.2%}")
    for k, v in tuning.params.items():
        print(f"    {k} = {v:.4f}")

    print("\nGenerating report...")
    generate_report(scan, tuning, regression)

    return scan, tuning, regression


if __name__ == "__main__":
    run_m5()