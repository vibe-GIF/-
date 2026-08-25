from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class GPSPoint(BaseModel):
    lon: float
    lat: float
    accuracy: float
    altitude: Optional[float] = None
    bearing: Optional[float] = None
    speed: Optional[float] = None
    is_mocked: Optional[bool] = False
    timestamp: float


class SensorFrame(BaseModel):
    timestamp: float
    accel_x: Optional[float] = None
    accel_y: Optional[float] = None
    accel_z: Optional[float] = None
    gyro_x: Optional[float] = None
    gyro_y: Optional[float] = None
    gyro_z: Optional[float] = None
    pressure: Optional[float] = None
    step_count: Optional[int] = None
    step_rate: Optional[float] = None


class TraceRequest(BaseModel):
    trace_id: str
    gps_points: List[GPSPoint] = Field(..., min_length=2)
    sensors: Optional[List[SensorFrame]] = None
    device_fingerprint: Optional[dict] = None
    account_id: Optional[str] = None
    campus_id: Optional[str] = None
    uploaded_at: Optional[float] = None
    total_steps: Optional[int] = None
    accel_variance: Optional[float] = None


class RuleResult(BaseModel):
    rule_name: str
    passed: bool
    score: float
    detail: str
    applicable: bool = True


class DetectionResponse(BaseModel):
    trace_id: str
    overall_risk: float
    verdict: str
    rule_results: List[RuleResult]
    processed_at: float