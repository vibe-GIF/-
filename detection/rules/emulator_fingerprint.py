from server.models import RuleResult, TraceRequest
from .base import BaseRule
from .config import EmulatorFingerprintConfig


class EmulatorFingerprintRule(BaseRule):
    name = "emulator_fingerprint"

    def evaluate(
        self, trace: TraceRequest, config: EmulatorFingerprintConfig
    ) -> RuleResult:
        fp = trace.device_fingerprint or {}
        build_str = (fp.get("build", "") or "").lower()
        sensor_count = fp.get("sensor_count", 0) or 0
        details = []
        score = 0.0

        for sig in config.emulator_build_signatures:
            if sig in build_str:
                score = max(score, 0.9)
                details.append(
                    f"Build string contains emulator signature '{sig}'"
                )
                break

        if sensor_count < config.min_sensor_count and sensor_count > 0:
            score = max(score, 0.6)
            details.append(
                f"Sensor count {sensor_count} below typical device "
                f"minimum {config.min_sensor_count}"
            )

        if not details:
            return RuleResult(
                rule_name=self.name, passed=True, score=0.0,
                detail="Device fingerprint appears genuine",
            )
        return RuleResult(
            rule_name=self.name, passed=False, score=score,
            detail="; ".join(details),
        )