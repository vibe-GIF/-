package com.budaolepao.detection

import android.os.Build
import com.budaolepao.detection.models.BuildInfo

internal object BuildFingerprint {

    fun collect(): BuildInfo {
        val serial: String = try {
            Build::class.java.getField("SERIAL").get(null) as? String ?: "unknown"
        } catch (_: Exception) {
            "unknown"
        }

        val kernelQemu = try {
            val prop = execGetProp("ro.kernel.qemu")
            prop == "1"
        } catch (_: Exception) {
            false
        }

        val supportedAbis: List<String> = if (Build.VERSION.SDK_INT >= 21) {
            Build.SUPPORTED_ABIS.toList()
        } else {
            listOf(Build.CPU_ABI, Build.CPU_ABI2).filterNotNull()
        }

        val isDebuggable = try {
            val appFlags = android.app.ActivityManager::class.java
                .getMethod("getRunningAppProcesses")
                .invoke(null)
            false
        } catch (_: Exception) {
            true
        }

        return BuildInfo(
            brand = Build.BRAND,
            manufacturer = Build.MANUFACTURER,
            model = Build.MODEL,
            device = Build.DEVICE,
            product = Build.PRODUCT,
            hardware = Build.HARDWARE,
            fingerprint = Build.FINGERPRINT,
            buildType = Build.TYPE,
            buildTags = Build.TAGS,
            androidVersion = Build.VERSION.RELEASE,
            sdkInt = Build.VERSION.SDK_INT,
            serial = serial,
            host = Build.HOST,
            user = Build.USER,
            display = Build.DISPLAY,
            board = Build.BOARD,
            bootloader = Build.BOOTLOADER,
            radioVersion = Build.getRadioVersion(),
            kernelQemu = kernelQemu,
            cpuAbi = Build.CPU_ABI,
            cpuAbi2 = Build.CPU_ABI2,
            supportedAbis = supportedAbis,
            isDebuggable = isDebuggable,
        )
    }

    private fun execGetProp(name: String): String? {
        return try {
            val cls = Class.forName("android.os.SystemProperties")
            val method = cls.getMethod("get", String::class.java)
            method.invoke(null, name) as? String
        } catch (_: Exception) {
            null
        }
    }
}