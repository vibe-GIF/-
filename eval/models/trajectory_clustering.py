"""
轨迹聚类模型 — 基于 DBSCAN 对轨迹相似度聚类，标记离群/重复轨迹。

特征：
  - 轨迹间的 DTW (Dynamic Time Warping) 距离
  - 或基于网格的 Jaccard 相似度
"""

import math
from typing import List, Tuple

import numpy as np
from sklearn.cluster import DBSCAN


def geo_dist_m(lat1, lon1, lat2, lon2) -> float:
    """球面近似距离（米），经度按 cos(lat) 缩放。"""
    avg_lat = math.radians((lat1 + lat2) / 2.0)
    d_lat = (lat2 - lat1) * 111_320
    d_lon = (lon2 - lon1) * 111_320 * math.cos(avg_lat)
    return math.hypot(d_lat, d_lon)


def dtw_distance(trace_a: List[Tuple[float, float]],
                 trace_b: List[Tuple[float, float]]) -> float:
    m, n = len(trace_a), len(trace_b)
    dtw = np.full((m + 1, n + 1), np.inf)
    dtw[0, 0] = 0.0
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            cost = geo_dist_m(
                trace_a[i - 1][1], trace_a[i - 1][0],
                trace_b[j - 1][1], trace_b[j - 1][0],
            )
            dtw[i, j] = cost + min(dtw[i - 1, j], dtw[i, j - 1], dtw[i - 1, j - 1])
    return dtw[m, n] / max(m, n)


def grid_jaccard(trace_a: List[Tuple[float, float]],
                 trace_b: List[Tuple[float, float]],
                 grid_size: int = 100) -> float:
    def to_grid(pts):
        # 经度按纬度缩放，网格在物理空间上近似均匀，避免不同纬度比例失真
        cells = set()
        for lon, lat in pts:
            col = int(lon * grid_size * math.cos(math.radians(lat)))
            row = int(lat * grid_size)
            cells.add((col, row))
        return cells
    ga, gb = to_grid(trace_a), to_grid(trace_b)
    intersection = ga & gb
    union = ga | gb
    return len(intersection) / len(union) if union else 0.0


class TrajectoryCluster:
    def __init__(self, eps: float = 500.0, min_samples: int = 2,
                 metric: str = "dtw"):
        self.eps = eps
        self.min_samples = min_samples
        self.metric = metric
        self.model: DBSCAN = None
        self._traces: List = []

    def fit(self, traces: List[List[Tuple[float, float]]]):
        self._traces = traces
        n = len(traces)
        if n < self.min_samples:
            self.model = None
            return

        dist_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(i + 1, n):
                if self.metric == "dtw":
                    d = dtw_distance(traces[i], traces[j])
                elif self.metric == "jaccard":
                    d = 1.0 - grid_jaccard(traces[i], traces[j])
                else:
                    d = dtw_distance(traces[i], traces[j])
                dist_matrix[i, j] = d
                dist_matrix[j, i] = d

        self.model = DBSCAN(
            eps=self.eps, min_samples=self.min_samples,
            metric="precomputed",
        ).fit(dist_matrix)

    def labels(self) -> np.ndarray:
        if self.model is None:
            return np.array([-1] * len(self._traces))
        return self.model.labels_

    def outliers(self) -> List[int]:
        return [i for i, l in enumerate(self.labels()) if l == -1]

    def cluster_sizes(self) -> dict:
        labels = self.labels()
        return {int(l): int((labels == l).sum()) for l in set(labels) if l >= 0}

    def largest_cluster(self) -> Tuple[int, List[int]]:
        labels = self.labels()
        non_outliers = [l for l in labels if l >= 0]
        if not non_outliers:
            return -1, []
        majority = max(set(non_outliers), key=non_outliers.count)
        members = [i for i, l in enumerate(labels) if l == majority]
        return int(majority), members