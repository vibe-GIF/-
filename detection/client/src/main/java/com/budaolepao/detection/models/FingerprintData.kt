package com.budaolepao.detection.models

import com.google.gson.annotations.SerializedName

data class DeviceFingerprint(
    @SerializedName("build") val build: BuildInfo,
    @SerializedName("sensors") val sensors: SensorInfo,
    @SerializedName("environment") val environment: EnvironmentInfo,
    @SerializedName("network") val network: NetworkInfo? = null,
    @SerializedName("collected_at") val collectedAt: Long = System.currentTimeMillis(),
)

data class BuildInfo(
    @SerializedName("brand") val brand: String,
    @SerializedName("manufacturer") val manufacturer: String,
    @SerializedName("model") val model: String,
    @SerializedName("device") val device: String,
    @SerializedName("product") val product: String,
    @SerializedName("hardware") val hardware: String,
    @SerializedName("fingerprint") val fingerprint: String,
    @SerializedName("build_type") val buildType: String,
    @SerializedName("build_tags") val buildTags: String,
    @SerializedName("android_version") val androidVersion: String,
    @SerializedName("sdk_int") val sdkInt: Int,
    @SerializedName("serial") val serial: String,
    @SerializedName("host") val host: String,
    @SerializedName("user") val user: String,
    @SerializedName("display") val display: String,
    @SerializedName("board") val board: String,
    @SerializedName("bootloader") val bootloader: String,
    @SerializedName("radio_version") val radioVersion: String?,
    @SerializedName("kernel_qemu") val kernelQemu: Boolean,
    @SerializedName("cpu_abi") val cpuAbi: String,
    @SerializedName("cpu_abi2") val cpuAbi2: String?,
    @SerializedName("supported_abis") val supportedAbis: List<String>,
    @SerializedName("is_debuggable") val isDebuggable: Boolean,
)

data class SensorInfo(
    @SerializedName("sensor_count") val sensorCount: Int,
    @SerializedName("sensor_list") val sensorList: List<SensorDetail>,
    @SerializedName("has_accelerometer") val hasAccelerometer: Boolean,
    @SerializedName("has_gyroscope") val hasGyroscope: Boolean,
    @SerializedName("has_magnetometer") val hasMagnetometer: Boolean,
    @SerializedName("has_barometer") val hasBarometer: Boolean,
    @SerializedName("has_heart_rate") val hasHeartRate: Boolean,
    @SerializedName("has_step_counter") val hasStepCounter: Boolean,
    @SerializedName("has_gravity") val hasGravity: Boolean,
    @SerializedName("has_rotation_vector") val hasRotationVector: Boolean,
    @SerializedName("has_light") val hasLight: Boolean,
    @SerializedName("has_proximity") val hasProximity: Boolean,
    @SerializedName("has_temperature") val hasTemperature: Boolean,
    @SerializedName("has_humidity") val hasHumidity: Boolean,
    @SerializedName("has_significant_motion") val hasSignificantMotion: Boolean,
    @SerializedName("has_game_rotation_vector") val hasGameRotationVector: Boolean,
)

data class SensorDetail(
    @SerializedName("name") val name: String,
    @SerializedName("vendor") val vendor: String,
    @SerializedName("type") val type: Int,
    @SerializedName("version") val version: Int,
    @SerializedName("power") val power: Float,
    @SerializedName("resolution") val resolution: Float,
    @SerializedName("max_range") val maxRange: Float,
    @SerializedName("min_delay") val minDelay: Int,
)

data class EnvironmentInfo(
    @SerializedName("device_id") val deviceId: String?,
    @SerializedName("android_id") val androidId: String?,
    @SerializedName("is_emulator") val isEmulator: Boolean,
    @SerializedName("emulator_reasons") val emulatorReasons: List<String>,
    @SerializedName("has_emulator_files") val hasEmulatorFiles: Boolean,
    @SerializedName("emulator_files_found") val emulatorFilesFound: List<String>,
    @SerializedName("running_processes") val runningProcesses: List<String>,
    @SerializedName("has_debug_app") val hasDebugApp: Boolean,
    @SerializedName("is_rooted") val isRooted: Boolean,
    @SerializedName("has_xposed") val hasXposed: Boolean,
    @SerializedName("has_frida") val hasFrida: Boolean,
    @SerializedName("is_monkey_running") val isMonkeyRunning: Boolean,
    @SerializedName("props") val suspiciousProps: Map<String, String>,
    @SerializedName("env_proof") val envProof: String?,
)

data class NetworkInfo(
    @SerializedName("operator") val operator: String?,
    @SerializedName("network_type") val networkType: String?,
    @SerializedName("is_roaming") val isRoaming: Boolean,
    @SerializedName("has_imei") val hasImei: Boolean,
    @SerializedName("wifi_mac") val wifiMac: String?,
)