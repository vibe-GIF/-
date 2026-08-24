from abc import ABC, abstractmethod
from typing import Any, Dict

from server.models import RuleResult, TraceRequest


class BaseRule(ABC):
    name: str

    @abstractmethod
    def evaluate(self, trace: TraceRequest, config: Any) -> RuleResult:
        ...

    def normalize_score(self, raw: float, max_val: float = 1.0) -> float:
        return max(0.0, min(1.0, raw / max_val))