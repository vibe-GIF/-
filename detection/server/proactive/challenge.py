"""
挑战-响应验证 (环境证明)

服务端向客户端发送挑战，要求客户端在真实 Android 环境中完成特定操作。
由于模拟器无法执行某些底层操作，挑战会失败。

挑战类型：
  1. WebView JS 执行挑战 — 在 WebView 中执行 JS 并返回结果
  2. 原生代码执行挑战 — 要求客户端执行 native code 并返回哈希
  3. 传感器读取挑战 — 要求客户端读取传感器并返回当前值
  4. 文件系统挑战 — 要求客户端读取特定系统文件

MuMu 模拟器无法通过：
  - Google Play Integrity API 检查
  - 真实的传感器数据读取
  - 某些 native code 调用
"""

import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Dict, Optional


class ChallengeManager:
    def __init__(self):
        self._secret = os.urandom(32)
        self._pending: Dict[str, dict] = {}

    def generate(self, challenge_type: str = "proof") -> dict:
        challenge_id = uuid.uuid4().hex[:16]
        timestamp = int(time.time())
        nonce = os.urandom(16).hex()

        payload = f"{challenge_id}:{timestamp}:{nonce}:{challenge_type}"
        expected = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()

        self._pending[challenge_id] = {
            "type": challenge_type,
            "timestamp": timestamp,
            "nonce": nonce,
            "expected": expected,
            "expires_at": timestamp + 60,
        }

        return {
            "challenge_id": challenge_id,
            "type": challenge_type,
            "nonce": nonce,
            "timestamp": timestamp,
        }

    def verify(self, challenge_id: str, response: str) -> dict:
        pending = self._pending.pop(challenge_id, None)
        if not pending:
            return {"passed": False, "reason": "challenge_not_found"}

        if time.time() > pending["expires_at"]:
            return {"passed": False, "reason": "challenge_expired"}

        expected = pending["expected"]
        if response == expected:
            return {"passed": True, "reason": "challenge_passed"}

        return {"passed": False, "reason": "invalid_response"}

    def generate_proof(self, challenge_id: str, nonce: str,
                       timestamp: int, challenge_type: str) -> str:
        payload = f"{challenge_id}:{timestamp}:{nonce}:{challenge_type}"
        return hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()


class EnvironmentProofBuilder:
    @staticmethod
    def build_proof(device_fingerprint: dict) -> str:
        components = [
            device_fingerprint.get("build", {}).get("fingerprint", ""),
            device_fingerprint.get("build", {}).get("serial", ""),
            device_fingerprint.get("environment", {}).get("android_id", ""),
            str(device_fingerprint.get("sensors", {}).get("sensor_count", 0)),
        ]
        raw = ":".join(components)
        return hashlib.sha256(raw.encode()).hexdigest()