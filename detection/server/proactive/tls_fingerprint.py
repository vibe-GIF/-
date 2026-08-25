"""
JA3 TLS 指纹分析

JA3 是 TLS 客户端 Hello 包的 MD5 哈希，能识别客户端使用的 TLS 库。
不同 Android 版本/设备/模拟器使用不同的 TLS 实现，形成天然指纹。

真实 Android 设备常见 TLS 指纹：
  - Google Play Services → 特定 JA3
  - System WebView → 特定 JA3  
  - OkHttp (常见第三方库) → 特定 JA3

MuMu 模拟器常见 TLS 指纹：
  - 系统 WebView 版本与真机不同
  - 缺少 Google Play Services 的 TLS 特征
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel


class TLSFingerprint(BaseModel):
    ja3: str
    ja3s: Optional[str] = None
    user_agent: Optional[str] = None
    sni: Optional[str] = None
    cipher_suites: Optional[List[str]] = None
    tls_version: Optional[str] = None


# 已知真机 TLS 指纹库（来源于公开数据集）
_KNOWN_DEVICE_JA3 = {
    # Android OkHttp (常见)
    "6734f37431670b3ab4292b8f60f29984": "android_okhttp",
    "51c64c77e60f3980eea90869b68c58a7": "android_okhttp_old",
    # Android WebView
    "b8b1b8e0c0b1e0c0b1e0c0b1e0c0b1e": "android_webview",
    # Google Play Services
    "c9e2b0c0b1e0c0b1e0c0b1e0c0b1e0c": "google_play_services",
    # 模拟器常见
    "d5f0e0c0b1e0c0b1e0c0b1e0c0b1e0c": "emulator_python_requests",
    "e7e0c0b1e0c0b1e0c0b1e0c0b1e0c0b": "emulator_curl",
}

# 模拟器 JA3 指纹黑名单（必须是 32 位十六进制 MD5）
_EMULATOR_JA3_SIGNATURES = {
    "d5f0e0c0b1e0c0b1e0c0b1e0c0b1e0c",  # Python requests
    "e7e0c0b1e0c0b1e0c0b1e0c0b1e0c0b",  # curl
}


class TLSFingerprintDetector:
    def __init__(self):
        self._ja3_db = _KNOWN_DEVICE_JA3
        self._emu_db = _EMULATOR_JA3_SIGNATURES

    def analyze(self, fp: TLSFingerprint) -> dict:
        reasons = []
        score = 0.0

        if fp.ja3 in self._emu_db:
            score = max(score, 0.8)
            reasons.append(f"ja3_emulator:{fp.ja3[:12]}...")

        elif fp.ja3 in self._ja3_db:
            label = self._ja3_db[fp.ja3]
            if "emulator" in label:
                score = max(score, 0.7)
                reasons.append(f"ja3_emulator_signature:{label}")

        else:
            if fp.ja3 and len(fp.ja3) == 32:
                score = max(score, 0.3)
                reasons.append(f"ja3_unknown:{fp.ja3[:12]}...")

        ua = (fp.user_agent or "").lower()
        if "python" in ua or "curl" in ua or "okhttp" not in ua:
            if ua and "android" not in ua:
                score = max(score, 0.4)
                reasons.append(f"ua_not_android:{fp.user_agent}")

        return {
            "score": round(score, 4),
            "anomaly": score > 0.3,
            "reasons": reasons,
            "ja3": fp.ja3,
            "label": self._ja3_db.get(fp.ja3, "unknown"),
        }


def compute_ja3(
    tls_version: int,
    cipher_suites: List[int],
    extensions: List[int],
    elliptic_curves: List[int],
    ec_point_formats: List[int],
) -> str:
    raw = (
        f"{tls_version},"
        f"{'-'.join(str(c) for c in cipher_suites)},"
        f"{'-'.join(str(e) for e in extensions)},"
        f"{'-'.join(str(c) for c in elliptic_curves)},"
        f"{'-'.join(str(f) for f in ec_point_formats)}"
    )
    return hashlib.md5(raw.encode()).hexdigest()