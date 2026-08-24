package com.budaolepao.detection

import android.content.Context
import android.os.Build
import android.provider.Settings
import com.budaolepao.detection.models.EnvironmentInfo
import java.io.File

internal object EnvironmentFingerprint {

    private val EMULATOR_BUILD_SIGNATURES = listOf(
        "sdk_phone", "emu64", "generic", "vbox86p", "vbox86tp",
        "google_sdk", "sdk_gphone", "sdk_x86", "sdk_arm",
    )

    private val EMULATOR_PROPS = mapOf(
        "ro.kernel.qemu" to "1",
        "ro.hardware" to "ranchu",
        "ro.product.model" to "MuMu",
        "ro.product.manufacturer" to "unknown",
        "ro.product.brand" to "Android",
        "ro.build.type" to "userdebug",
        "ro.build.tags" to "test-keys",
    )

    private val EMULATOR_FILES = listOf(
        "/system/bin/qemu-props",
        "/system/bin/qemu-adb",
        "/system/lib/libc_malloc_debug_qemu.so",
        "/system/lib64/libc_malloc_debug_qemu.so",
        "/system/bin/microvirt",
        "/system/bin/mumu",
        "/data/local/tmp/mumu",
        "/system/xbin/mumu",
        "/system/app/EmulatorICS",
        "/system/app/EmulatorKitkat",
    )

    private val EMULATOR_PROCESSES = listOf(
        "qemu", "emu64", "mumu", "microvirt",
    )

    fun collect(context: Context): EnvironmentInfo {
        val reasons = mutableListOf<String>()
        val suspiciousProps = mutableMapOf<String, String>()
        val emulatorFilesFound = mutableListOf<String>()

        val buildStr = listOf(
            Build.BRAND, Build.MANUFACTURER, Build.MODEL,
            Build.DEVICE, Build.PRODUCT, Build.FINGERPRINT,
            Build.HARDWARE, Build.TYPE, Build.TAGS,
        ).joinToString(" ").lowercase()

        for (sig in EMULATOR_BUILD_SIGNATURES) {
            if (buildStr.contains(sig)) {
                reasons.add("build_contains_$sig")
            }
        }

        for ((prop, expected) in EMULATOR_PROPS) {
            val value = getProp(prop)
            if (value != null) {
                suspiciousProps[prop] = value
                if (value.contains(expected, ignoreCase = true)) {
                    reasons.add("prop_${prop}=${value}")
                }
            }
        }

        for (path in EMULATOR_FILES) {
            if (File(path).exists()) {
                emulatorFilesFound.add(path)
                reasons.add("emulator_file_$path")
            }
        }

        val runningProcesses = getRunningProcesses()
        for (proc in runningProcesses) {
            for (sig in EMULATOR_PROCESSES) {
                if (proc.contains(sig, ignoreCase = true)) {
                    reasons.add("process_$proc")
                    break
                }
            }
        }

        val isEmulator = reasons.isNotEmpty()

        val androidId = try {
            Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
        } catch (_: Exception) {
            null
        }

        val deviceId = try {
            Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID)
        } catch (_: Exception) {
            null
        }

        val isRooted = checkRoot()
        val hasXposed = checkXposed()
        val hasFrida = checkFrida()
        val isMonkeyRunning = checkMonkey()
        val hasDebugApp = (context.applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0

        val envProof = if (isEmulator) null else generateEnvProof()

        return EnvironmentInfo(
            deviceId = deviceId,
            androidId = androidId,
            isEmulator = isEmulator,
            emulatorReasons = reasons,
            hasEmulatorFiles = emulatorFilesFound.isNotEmpty(),
            emulatorFilesFound = emulatorFilesFound,
            runningProcesses = runningProcesses,
            hasDebugApp = hasDebugApp,
            isRooted = isRooted,
            hasXposed = hasXposed,
            hasFrida = hasFrida,
            isMonkeyRunning = isMonkeyRunning,
            suspiciousProps = suspiciousProps,
            envProof = envProof,
        )
    }

    private fun getProp(name: String): String? {
        return try {
            val cls = Class.forName("android.os.SystemProperties")
            val method = cls.getMethod("get", String::class.java, String::class.java)
            method.invoke(null, name, "") as? String
        } catch (_: Exception) {
            null
        }.takeIf { it?.isNotEmpty() == true }
    }

    private fun getRunningProcesses(): List<String> {
        return try {
            val procFile = File("/proc/self/status")
            if (procFile.exists()) {
                val lines = procFile.readLines()
                lines.filter { it.startsWith("Name:") || it.startsWith("Groups:") }
            } else emptyList()
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun checkRoot(): Boolean {
        val paths = listOf(
            "/system/app/Superuser.apk",
            "/sbin/su",
            "/system/bin/su",
            "/system/xbin/su",
            "/data/local/xbin/su",
            "/data/local/bin/su",
            "/system/sd/xbin/su",
            "/system/bin/failsafe/su",
            "/data/local/su",
            "/su/bin/su",
        )
        return paths.any { File(it).exists() }
    }

    private fun checkXposed(): Boolean {
        return try {
            Class.forName("de.robv.android.xposed.XposedBridge")
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun checkFrida(): Boolean {
        return try {
            val fridaFiles = listOf(
                "/data/local/tmp/frida-server",
                "/data/local/tmp/re.frida.server",
            )
            fridaFiles.any { File(it).exists() }
        } catch (_: Exception) {
            false
        }
    }

    private fun checkMonkey(): Boolean {
        return try {
            val cls = Class.forName("android.app.ActivityManager")
            val method = cls.getDeclaredMethod("getCurrentUser")
            method.isAccessible = true
            false
        } catch (_: Exception) {
            false
        }
    }

    private fun generateEnvProof(): String {
        val components = listOf(
            Build.BOARD, Build.BOOTLOADER, Build.BRAND,
            Build.DEVICE, Build.DISPLAY, Build.FINGERPRINT,
            Build.HARDWARE, Build.HOST, Build.ID,
            Build.MANUFACTURER, Build.MODEL, Build.PRODUCT,
            Build.SERIAL, Build.TAGS, Build.TYPE, Build.USER,
        )
        val raw = components.joinToString(":")
        val digest = java.security.MessageDigest.getInstance("SHA-256")
        return digest.digest(raw.toByteArray()).joinToString("") { "%02x".format(it) }
    }
}