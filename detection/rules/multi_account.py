import time

from server.models import RuleResult, TraceRequest
from .base import BaseRule
from .config import MultiAccountConfig


class MultiAccountRule(BaseRule):
    """多账号检测：同一设备关联账号数 > 阈值。带 TTL 衰减，防止跨会话永久累积误报。"""

    name = "multi_account"

    _device_accounts: dict = {}  # device_id -> {account_id: last_seen_ts}

    def _prune(self, now: float, ttl: float):
        stale_devices = []
        for device_id, accounts in self._device_accounts.items():
            for account in list(accounts.keys()):
                if now - accounts[account] > ttl:
                    del accounts[account]
            if not accounts:
                stale_devices.append(device_id)
        for device_id in stale_devices:
            del self._device_accounts[device_id]

    def evaluate(
        self, trace: TraceRequest, config: MultiAccountConfig
    ) -> RuleResult:
        fp = trace.device_fingerprint or {}
        device_id = fp.get("device_id") or fp.get("android_id") or "unknown"
        account = trace.account_id or "unknown"
        now = time.time()

        self._prune(now, config.state_ttl_sec)

        accounts = self._device_accounts.setdefault(device_id, {})
        accounts[account] = now

        account_count = len(accounts)
        if account_count > config.max_accounts_per_device:
            return RuleResult(
                rule_name=self.name, passed=False, score=0.8,
                detail=f"Device {device_id} associated with {account_count} "
                f"accounts in {config.state_ttl_sec:.0f}s "
                f"(limit: {config.max_accounts_per_device})",
            )
        return RuleResult(
            rule_name=self.name, passed=True, score=0.0,
            detail=f"Device has {account_count} recent account(s), within limit",
        )
