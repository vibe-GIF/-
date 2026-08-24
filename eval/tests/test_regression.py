"""
M5 回归测试 — 确保调优不破坏已有检测能力。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import numpy as np

from baselines.synthetic_traces import generate_dataset, generate_normal_trace, generate_attack_trace
from regression import (
    evaluate_dataset,
    threshold_scan,
    regression_test,
    grid_search,
)
from rules.config import DEFAULT_CONFIG, DetectionConfig


@pytest.fixture
def dataset():
    return generate_dataset(n_normal=10, n_attack=10)


class TestThresholdScan:
    def test_scan_returns_results(self, dataset):
        results = threshold_scan(dataset, thresholds=[0.1, 0.3, 0.5])
        assert len(results) == 3
        for r in results:
            assert 0 <= r.recall <= 1
            assert 0 <= r.fpr <= 1
            assert 0 <= r.f1 <= 1

    def test_higher_threshold_lower_fpr(self, dataset):
        results = threshold_scan(dataset, thresholds=[0.1, 0.5, 0.9])
        fprs = [r.fpr for r in results]
        assert fprs[0] >= fprs[-1]


class TestRegressionTest:
    def test_passes_with_default_config(self, dataset):
        r = regression_test(dataset, threshold=0.3, min_recall=0.5, max_fpr=0.5)
        assert r["passed"]

    def test_fails_with_strict_requirements(self, dataset):
        r = regression_test(dataset, threshold=0.3, min_recall=1.0, max_fpr=0.0)
        assert not r["passed"] or (r["recall"] == 1.0 and r["fpr"] == 0.0)


class TestGridSearch:
    def test_returns_result(self, dataset):
        result = grid_search(dataset, n_trials=10)
        assert result is not None
        assert 0 <= result.recall <= 1
        assert 0 <= result.fpr <= 1
        assert result.params


class TestEdgeCases:
    def test_all_normal(self):
        ds = [generate_normal_trace(f"n_{i}", 50) for i in range(10)]
        r = regression_test(ds, threshold=0.3)
        assert r["fpr"] < 0.5

    def test_all_attack(self):
        ds = [generate_attack_trace(f"a_{i}", 50) for i in range(10)]
        r = regression_test(ds, threshold=0.3, min_recall=0.0)
        assert r["recall"] > 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])