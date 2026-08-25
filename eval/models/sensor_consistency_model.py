"""
传感器一致性模型 — 预测 GPS 速度与步频的联合相关性打分。
"""

import math
from typing import List, Tuple

import numpy as np
from sklearn.linear_model import LinearRegression


def geo_dist_m(lat1, lon1, lat2, lon2) -> float:
    """球面近似距离（米），经度按 cos(lat) 缩放。"""
    avg_lat = math.radians((lat1 + lat2) / 2.0)
    d_lat = (lat2 - lat1) * 111_320
    d_lon = (lon2 - lon1) * 111_320 * math.cos(avg_lat)
    return math.hypot(d_lat, d_lon)


class SensorConsistencyModel:
    def __init__(self):
        self._model = LinearRegression()
        self._fitted = False

    def fit(self, gps_speeds: List[float], step_rates: List[float]):
        X = np.array(gps_speeds).reshape(-1, 1)
        y = np.array(step_rates)
        self._model.fit(X, y)
        self._fitted = True

    def predict_step_rate(self, gps_speed: float) -> float:
        if not self._fitted:
            return 1.2 + (gps_speed - 1.0) / 4.0 * 1.6
        return float(self._model.predict(np.array([[gps_speed]]))[0])

    def score(self, gps_speeds: List[float], step_rates: List[float]) -> dict:
        if len(gps_speeds) < 5 or len(step_rates) < 5:
            return {"score": 0.0, "anomaly": False, "reason": "insufficient_data"}

        speeds_arr = np.array(gps_speeds)
        steps_arr = np.array(step_rates)

        if np.std(speeds_arr) < 1e-6 or np.std(steps_arr) < 1e-6:
            return {"score": 0.8, "anomaly": True, "reason": "zero_variance"}

        corr = float(np.corrcoef(speeds_arr, steps_arr)[0, 1])

        if abs(corr) < 0.3:
            return {
                "score": min(1.0, 0.7 + (0.3 - abs(corr))),
                "anomaly": True,
                "reason": f"low_correlation:r={corr:.3f}",
            }

        if self._fitted:
            predicted = self._model.predict(speeds_arr.reshape(-1, 1))
            residuals = np.abs(steps_arr - predicted)
            mae = float(np.mean(residuals))
            if mae > 1.0:
                return {
                    "score": min(1.0, mae / 3.0),
                    "anomaly": True,
                    "reason": f"high_prediction_error:MAE={mae:.3f}",
                }

        return {
            "score": round(1.0 - abs(corr), 3),
            "anomaly": False,
            "reason": f"normal_correlation:r={corr:.3f}",
        }


def compute_gps_speeds(
    points: List[Tuple[float, float, float]]
) -> List[float]:
    speeds = []
    for i in range(1, len(points)):
        lon1, lat1, t1 = points[i - 1]
        lon2, lat2, t2 = points[i]
        dt = t2 - t1
        if dt <= 0:
            continue
        dist = geo_dist_m(lat1, lon1, lat2, lon2)
        speeds.append(dist / dt)
    return speeds