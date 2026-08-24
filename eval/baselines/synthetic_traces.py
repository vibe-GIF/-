"""
生成合成轨迹数据，用于 ML 模型训练和评估指标校准。

三类数据：
  1. normal   — 真实学生轨迹（带自然波动）
  2. attack   — 攻击 PoC 轨迹（模拟器/脚本生成）
  3. abnormal — 异常但非攻击（如骑车、代跑）
"""

import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np


@dataclass
class TraceSample:
    trace_id: str
    label: str
    gps_points: List[Tuple[float, float, float]]
    speeds: List[float]
    step_rates: List[float]
    accuracy_values: List[float]
    timestamps: List[float]
    campus_id: str = "default"


def _ou_process(n: int, dt: float, theta: float, sigma: float) -> np.ndarray:
    x = np.zeros(n)
    for i in range(1, n):
        x[i] = x[i-1] + theta * (-x[i-1]) * dt + sigma * math.sqrt(dt) * random.gauss(0, 1)
    return x


def generate_normal_trace(trace_id: str, n_points: int = 200) -> TraceSample:
    lat, lon = 29.50 + random.uniform(-0.01, 0.01), 106.57 + random.uniform(-0.01, 0.01)
    points = []
    speeds = []
    step_rates = []
    accuracies = []
    timestamps = []
    t = 0.0

    for i in range(n_points):
        speed = 3.0 + 2.0 * math.sin(i * 0.05) + random.gauss(0, 0.3)
        speed = max(1.0, min(6.0, speed))
        speeds.append(speed)

        dt = random.uniform(0.8, 1.5)
        t += dt
        timestamps.append(t)

        dist = speed * dt
        bearing = random.uniform(0, 2 * math.pi)
        lat += dist * math.cos(bearing) / 111_320
        lon += dist * math.sin(bearing) / (111_320 * math.cos(math.radians(lat)))
        lat += random.gauss(0, 2e-6)
        lon += random.gauss(0, 2e-6)

        points.append((lon, lat, t))

        step_rate = 1.2 + (speed - 1.0) / 4.0 * 1.6
        step_rates.append(step_rate + random.gauss(0, 0.1))

        accuracy = 5.0 + 5.0 * random.random() + 3.0 * math.sin(i * 0.05)
        accuracies.append(accuracy)

    return TraceSample(
        trace_id=trace_id, label="normal",
        gps_points=points, speeds=speeds,
        step_rates=step_rates, accuracy_values=accuracies,
        timestamps=timestamps,
    )


def generate_attack_trace(trace_id: str, n_points: int = 200,
                          attack_type: str = "emulator") -> TraceSample:
    lat, lon = 29.50, 106.57
    route = [
        (106.5733, 29.5089), (106.5743, 29.5092),
        (106.5756, 29.5085), (106.5743, 29.5080),
        (106.5711, 29.5083), (106.5735, 29.5086),
    ]

    points = []
    speeds = []
    step_rates = []
    accuracies = []
    timestamps = []
    t = 0.0
    idx = 0
    seg_dist = 0.0

    gps = GPSSimulator() if attack_type == "enhanced" else None

    for i in range(n_points):
        if attack_type == "emulator":
            speed = 4.5 + random.uniform(-0.5, 0.5)
            dt = 0.4
            step_rate = 0.0
            accuracy = 8.0
        elif attack_type == "script":
            speed = 4.5
            dt = 0.4
            step_rate = 0.0
            accuracy = 10.0
        elif attack_type == "enhanced":
            speed = 4.0 + 0.8 * math.sin(i * 0.05)
            dt = max(0.1, random.lognormvariate(-1.0, 0.25))
            step_rate = 1.2 + (speed - 1.0) / 4.0 * 1.6
            env = math.sin(i * 0.01) * 0.5 + 0.5
            accuracy = 5.0 + 8.0 * env + random.gauss(0, 0.5)
        else:
            speed = 4.5
            dt = 0.4
            step_rate = 0.0
            accuracy = 8.0

        t += dt
        timestamps.append(t)
        speeds.append(speed)

        lon1, lat1 = route[idx]
        lon2, lat2 = route[(idx + 1) % len(route)]
        seg_len = math.hypot(lat2 - lat1, lon2 - lon1) * 111_320

        move = speed * dt
        seg_dist += move

        while seg_dist >= seg_len and seg_len > 0:
            seg_dist -= seg_len
            idx = (idx + 1) % len(route)
            lon1, lat1 = route[idx]
            lon2, lat2 = route[(idx + 1) % len(route)]
            seg_len = math.hypot(lat2 - lat1, lon2 - lon1) * 111_320

        ratio = seg_dist / seg_len if seg_len > 0 else 0
        base_lon = lon1 + (lon2 - lon1) * ratio
        base_lat = lat1 + (lat2 - lat1) * ratio

        if attack_type == "enhanced" and gps:
            lat_off = 1.5 * math.sin(i * 0.05) / 111_320
            lon_off = 1.5 * math.sin(i * 0.05 + 3.0) / (111_320 * math.cos(math.radians(lat1)))
            base_lat += lat_off
            base_lon += lon_off
            dx, dy = gps.step(dt)
            d_lat, d_lon = dy / 111_320, dx / (111_320 * math.cos(math.radians(base_lat)))
            base_lat += d_lat
            base_lon += d_lon

        points.append((base_lon, base_lat, t))
        step_rates.append(step_rate)
        accuracies.append(accuracy)

    return TraceSample(
        trace_id=trace_id, label=f"attack_{attack_type}",
        gps_points=points, speeds=speeds,
        step_rates=step_rates, accuracy_values=accuracies,
        timestamps=timestamps,
    )


class GPSSimulator:
    def __init__(self):
        self._ou_x = 0.0
        self._ou_y = 0.0

    def step(self, dt: float) -> Tuple[float, float]:
        theta, sigma = 0.8, 1.5
        self._ou_x += theta * (-self._ou_x) * dt + sigma * math.sqrt(dt) * random.gauss(0, 1)
        self._ou_y += theta * (-self._ou_y) * dt + sigma * math.sqrt(dt) * random.gauss(0, 1)
        return self._ou_x * 2.0, self._ou_y * 2.0


def generate_dataset(n_normal: int = 50, n_attack: int = 30) -> List[TraceSample]:
    dataset = []
    for i in range(n_normal):
        dataset.append(generate_normal_trace(f"normal_{i}"))
    for i in range(n_attack):
        at = ["emulator", "script", "enhanced"][i % 3]
        dataset.append(generate_attack_trace(f"attack_{i}", attack_type=at))
    return dataset


if __name__ == "__main__":
    ds = generate_dataset(10, 6)
    for t in ds:
        print(f"{t.trace_id:20s} label={t.label:20s}  points={len(t.gps_points)}")