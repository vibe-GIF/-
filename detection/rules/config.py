from dataclasses import dataclass, field
from typing import Dict


@dataclass
class RuleConfig:
    enabled: bool = True
    weight: float = 1.0


@dataclass
class MockDetectionConfig(RuleConfig):
    mock_mark_threshold: int = 1


@dataclass
class AccuracyStabilityConfig(RuleConfig):
    accuracy_variance_min: float = 0.01
    window_size: int = 10


@dataclass
class SpeedPhysiologicalConfig(RuleConfig):
    max_instant_speed: float = 12.0
    max_acceleration: float = 10.0
    max_speed_variance: float = 0.1


@dataclass
class NoiseSpectrumConfig(RuleConfig):
    window_size: int = 50
    autocorr_threshold: float = 0.3


@dataclass
class SensorConsistencyConfig(RuleConfig):
    speed_step_corr_min: float = 0.3
    speed_range: tuple = (1.0, 6.0)


@dataclass
class EmulatorFingerprintConfig(RuleConfig):
    emulator_build_signatures: tuple = (
        "sdk_phone_arm64", "sdk_phone_armv7",
        "sdk_gphone64", "emu64", "generic",
        "vbox86p", "vbox86tp",
    )
    min_sensor_count: int = 8


@dataclass
class TrajectorySimilarityConfig(RuleConfig):
    jaccard_threshold: float = 0.9
    grid_size: int = 100


@dataclass
class MultiAccountConfig(RuleConfig):
    max_accounts_per_device: int = 3


@dataclass
class RequestIntegrityConfig(RuleConfig):
    require_env_proof: bool = True


@dataclass
class ZoneEnforcementConfig(RuleConfig):
    zone_bounds: tuple = ()
    max_outside_ratio: float = 0.1


@dataclass
class CheckpointConfig(RuleConfig):
    checkpoints: tuple = ()
    checkpoint_radius_m: float = 30.0
    min_checkpoints: int = 1


@dataclass
class StepDistanceConfig(RuleConfig):
    stride_length_m: float = 0.7
    min_gps_m: float = 500.0
    min_steps: int = 100
    max_ratio: float = 2.5
    min_ratio: float = 0.4


@dataclass
class DetectionConfig:
    mock_detection: MockDetectionConfig = field(
        default_factory=MockDetectionConfig
    )
    accuracy_stability: AccuracyStabilityConfig = field(
        default_factory=AccuracyStabilityConfig
    )
    speed_physiological: SpeedPhysiologicalConfig = field(
        default_factory=SpeedPhysiologicalConfig
    )
    noise_spectrum: NoiseSpectrumConfig = field(
        default_factory=NoiseSpectrumConfig
    )
    sensor_consistency: SensorConsistencyConfig = field(
        default_factory=SensorConsistencyConfig
    )
    emulator_fingerprint: EmulatorFingerprintConfig = field(
        default_factory=EmulatorFingerprintConfig
    )
    trajectory_similarity: TrajectorySimilarityConfig = field(
        default_factory=TrajectorySimilarityConfig
    )
    multi_account: MultiAccountConfig = field(
        default_factory=MultiAccountConfig
    )
    request_integrity: RequestIntegrityConfig = field(
        default_factory=RequestIntegrityConfig
    )
    zone_enforcement: ZoneEnforcementConfig = field(
        default_factory=ZoneEnforcementConfig
    )
    checkpoint: CheckpointConfig = field(
        default_factory=CheckpointConfig
    )
    step_distance: StepDistanceConfig = field(
        default_factory=StepDistanceConfig
    )

    risk_thresholds: Dict[str, float] = field(
        default_factory=lambda: {
            "low": 0.3,
            "medium": 0.6,
            "high": 0.8,
        }
    )


DEFAULT_CONFIG = DetectionConfig()