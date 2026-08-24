from typing import Dict, List, Type

from server.models import RuleResult, TraceRequest
from .base import BaseRule
from .config import DEFAULT_CONFIG, DetectionConfig
from .mock_detection import MockDetectionRule
from .accuracy_stability import AccuracyStabilityRule
from .speed_physiological import SpeedPhysiologicalRule
from .noise_spectrum import NoiseSpectrumRule
from .sensor_consistency import SensorConsistencyRule
from .emulator_fingerprint import EmulatorFingerprintRule
from .trajectory_similarity import TrajectorySimilarityRule
from .multi_account import MultiAccountRule
from .request_integrity import RequestIntegrityRule


class RuleEngine:
    def __init__(self, config: DetectionConfig = None):
        self.config = config or DEFAULT_CONFIG
        self._rules: Dict[str, BaseRule] = {}
        self._register_defaults()

    def _register_defaults(self):
        rule_classes: List[Type[BaseRule]] = [
            MockDetectionRule,
            AccuracyStabilityRule,
            SpeedPhysiologicalRule,
            NoiseSpectrumRule,
            SensorConsistencyRule,
            EmulatorFingerprintRule,
            TrajectorySimilarityRule,
            MultiAccountRule,
            RequestIntegrityRule,
        ]
        for cls in rule_classes:
            rule = cls()
            self._rules[rule.name] = rule

    def register(self, rule: BaseRule):
        self._rules[rule.name] = rule

    def evaluate(self, trace: TraceRequest) -> List[RuleResult]:
        results = []
        for name, rule in self._rules.items():
            rule_config = getattr(self.config, name, None)
            if rule_config is None or not rule_config.enabled:
                continue
            result = rule.evaluate(trace, rule_config)
            results.append(result)
        return results