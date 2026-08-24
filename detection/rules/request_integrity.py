from server.models import RuleResult, TraceRequest
from .base import BaseRule
from .config import RequestIntegrityConfig


class RequestIntegrityRule(BaseRule):
    name = "request_integrity"

    def evaluate(
        self, trace: TraceRequest, config: RequestIntegrityConfig
    ) -> RuleResult:
        fp = trace.device_fingerprint or {}
        if config.require_env_proof:
            has_env_proof = bool(fp.get("env_proof") or fp.get("runtime_signature"))
            if not has_env_proof:
                return RuleResult(
                    rule_name=self.name, passed=False, score=0.9,
                    detail="Missing runtime environment proof — "
                    "possible replay attack",
                )
        return RuleResult(
            rule_name=self.name, passed=True, score=0.0,
            detail="Request integrity checks passed",
        )