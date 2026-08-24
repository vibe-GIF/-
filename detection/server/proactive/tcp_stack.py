"""
TCP/IP 协议栈指纹

不同操作系统和网络栈在 TCP 握手时有不同的默认参数：
  - TTL (Time To Live)
  - 初始窗口大小 (Initial Window Size)
  - TCP 时间戳选项
  - MSS (Maximum Segment Size)
  - WS (Window Scaling)

真实 Android 设备特征：
  - TTL: 64 (Linux 默认)
  - 初始窗口: 29200 / 5840 / 65535
  - 支持 TCP 时间戳

模拟器特征：
  - Windows 宿主机 → TTL=128 (如果走 NAT)
  - 特定虚拟化网卡 → 窗口值异常
  - 某些模拟器禁用了 TCP 时间戳
"""

from typing import Dict, Optional

from pydantic import BaseModel


class TCPStackInfo(BaseModel):
    src_ip: Optional[str] = None
    ttl: Optional[int] = None
    window_size: Optional[int] = None
    mss: Optional[int] = None
    window_scaling: Optional[int] = None
    tcp_timestamp: Optional[bool] = None
    sack_permitted: Optional[bool] = None
    client_ip: Optional[str] = None


# 真实 Android TCP 栈参数范围
ANDROID_TTL_RANGE = (60, 68)
ANDROID_WINDOW_RANGE = (5800, 66000)
ANDROID_WINDOW_SCALING = (7, 8)
ANDROID_MSS_TYPICAL = (1400, 1460)


class TCPStackDetector:
    def analyze(self, info: TCPStackInfo) -> dict:
        reasons = []
        score = 0.0

        if info.ttl is not None:
            if info.ttl >= 120:
                score = max(score, 0.5)
                reasons.append(f"ttl_likely_windows:{info.ttl}")
            elif info.ttl < 60:
                score = max(score, 0.4)
                reasons.append(f"ttl_too_low:{info.ttl}")
            elif not (ANDROID_TTL_RANGE[0] <= info.ttl <= ANDROID_TTL_RANGE[1]):
                score = max(score, 0.2)
                reasons.append(f"ttl_non_android:{info.ttl}")

        if info.window_scaling is not None:
            if not (ANDROID_WINDOW_SCALING[0] <= info.window_scaling <= ANDROID_WINDOW_SCALING[1]):
                score = max(score, 0.3)
                reasons.append(f"window_scaling_anomaly:{info.window_scaling}")

        if info.tcp_timestamp is not None and not info.tcp_timestamp:
            score = max(score, 0.4)
            reasons.append("tcp_timestamp_disabled")

        if info.mss is not None:
            if not (ANDROID_MSS_TYPICAL[0] <= info.mss <= ANDROID_MSS_TYPICAL[1]):
                score = max(score, 0.3)
                reasons.append(f"mss_anomaly:{info.mss}")

        if info.src_ip and info.client_ip and info.src_ip != info.client_ip:
            score = max(score, 0.2)
            reasons.append(f"ip_mismatch:src={info.src_ip}/client={info.client_ip}")

        return {
            "score": round(score, 4),
            "anomaly": score > 0.3,
            "reasons": reasons,
        }