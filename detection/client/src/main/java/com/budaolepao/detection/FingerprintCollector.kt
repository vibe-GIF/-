package com.budaolepao.detection

import android.content.Context
import com.budaolepao.detection.models.DeviceFingerprint

class FingerprintCollector(private val context: Context) {

    fun collect(): DeviceFingerprint {
        val build = BuildFingerprint.collect()
        val sensors = SensorFingerprint.collect(context)
        val environment = EnvironmentFingerprint.collect(context)
        val network = NetworkFingerprint.collect(context)

        return DeviceFingerprint(
            build = build,
            sensors = sensors,
            environment = environment,
            network = network,
        )
    }
}