package com.budaolepao.detection

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorManager
import com.budaolepao.detection.models.SensorDetail
import com.budaolepao.detection.models.SensorInfo

internal object SensorFingerprint {

    private val TARGET_TYPES = mapOf(
        Sensor.TYPE_ACCELEROMETER to "hasAccelerometer",
        Sensor.TYPE_GYROSCOPE to "hasGyroscope",
        Sensor.TYPE_MAGNETIC_FIELD to "hasMagnetometer",
        Sensor.TYPE_PRESSURE to "hasBarometer",
        Sensor.TYPE_HEART_RATE to "hasHeartRate",
        Sensor.TYPE_STEP_COUNTER to "hasStepCounter",
        Sensor.TYPE_GRAVITY to "hasGravity",
        Sensor.TYPE_ROTATION_VECTOR to "hasRotationVector",
        Sensor.TYPE_LIGHT to "hasLight",
        Sensor.TYPE_PROXIMITY to "hasProximity",
        Sensor.TYPE_AMBIENT_TEMPERATURE to "hasTemperature",
        Sensor.TYPE_RELATIVE_HUMIDITY to "hasHumidity",
        Sensor.TYPE_SIGNIFICANT_MOTION to "hasSignificantMotion",
        Sensor.TYPE_GAME_ROTATION_VECTOR to "hasGameRotationVector",
    )

    fun collect(context: Context): SensorInfo {
        val sensorManager = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val allSensors: List<Sensor> = sensorManager.getSensorList(Sensor.TYPE_ALL)

        val sensorDetails = allSensors.map { s ->
            SensorDetail(
                name = s.name,
                vendor = s.vendor,
                type = s.type,
                version = s.version,
                power = s.power,
                resolution = s.resolution,
                maxRange = s.maximumRange,
                minDelay = s.minDelay,
            )
        }

        val presentTypes = allSensors.map { it.type }.toSet()

        return SensorInfo(
            sensorCount = allSensors.size,
            sensorList = sensorDetails,
            hasAccelerometer = presentTypes.contains(Sensor.TYPE_ACCELEROMETER),
            hasGyroscope = presentTypes.contains(Sensor.TYPE_GYROSCOPE),
            hasMagnetometer = presentTypes.contains(Sensor.TYPE_MAGNETIC_FIELD),
            hasBarometer = presentTypes.contains(Sensor.TYPE_PRESSURE),
            hasHeartRate = presentTypes.contains(Sensor.TYPE_HEART_RATE),
            hasStepCounter = presentTypes.contains(Sensor.TYPE_STEP_COUNTER),
            hasGravity = presentTypes.contains(Sensor.TYPE_GRAVITY),
            hasRotationVector = presentTypes.contains(Sensor.TYPE_ROTATION_VECTOR),
            hasLight = presentTypes.contains(Sensor.TYPE_LIGHT),
            hasProximity = presentTypes.contains(Sensor.TYPE_PROXIMITY),
            hasTemperature = presentTypes.contains(Sensor.TYPE_AMBIENT_TEMPERATURE),
            hasHumidity = presentTypes.contains(Sensor.TYPE_RELATIVE_HUMIDITY),
            hasSignificantMotion = presentTypes.contains(Sensor.TYPE_SIGNIFICANT_MOTION),
            hasGameRotationVector = presentTypes.contains(Sensor.TYPE_GAME_ROTATION_VECTOR),
        )
    }
}