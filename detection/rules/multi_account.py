from server.models import RuleResult, TraceRequest
from .base import BaseRule
from .config import MultiAccountConfig


class MultiAccountRule(BaseRule):
    name = "multi_account"

    _device_accounts: dict = {}

    def evaluate(
        self, trace: TraceRequest, config: MultiAccountConfig
    ) -> RuleResult:
        fp = trace.device_fingerprint or {}
        device_id = fp.get("device_id") or fp.get("android_id") or "unknown"
        account = trace.account_id or "unknown"

        if device_id not in self._device_accounts:
            self._device_accounts[device_id] = set()
        self._device_accounts[device_id].add(account)

        account_count = len(self._device_accounts[device_id])
        if account_count > config.max_accounts_per_device:
            return RuleResult(
                rule_name=self.name, passed=False, score=0.8,
                detail=f"Device {device_id} associated with {account_count} "
                f"accounts (limit: {config.max_accounts_per_device})",
            )
        return RuleResult(
            rule_name=self.name, passed=True, score=0.0,
            detail=f"Device has {account_count} account(s), within limit",
        )