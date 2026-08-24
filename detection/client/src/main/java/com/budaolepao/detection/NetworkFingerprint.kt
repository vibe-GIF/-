package com.budaolepao.detection

import android.content.Context
import android.telephony.TelephonyManager
import android.net.wifi.WifiManager
import com.budaolepao.detection.models.NetworkInfo

internal object NetworkFingerprint {

    fun collect(context: Context): NetworkInfo? {
        return try {
            val tm = context.getSystemService(Context.TELEPHONY_SERVICE) as? TelephonyManager
            val wm = context.getSystemService(Context.WIFI_SERVICE) as? WifiManager

            val operator = tm?.networkOperatorName
            val networkType = when (tm?.dataNetworkType) {
                TelephonyManager.NETWORK_TYPE_LTE -> "LTE"
                TelephonyManager.NETWORK_TYPE_NR -> "5G"
                TelephonyManager.NETWORK_TYPE_UMTS -> "3G"
                TelephonyManager.NETWORK_TYPE_EDGE -> "2G"
                TelephonyManager.NETWORK_TYPE_WIFI -> "WiFi"
                else -> "unknown"
            }
            val isRoaming = tm?.isNetworkRoaming ?: false
            val hasImei = try {
                tm?.deviceId?.let { it.isNotEmpty() && it.length >= 15 } ?: false
            } catch (_: SecurityException) {
                false
            }

            val wifiMac = try {
                wm?.connectionInfo?.macAddress
            } catch (_: Exception) {
                null
            }

            NetworkInfo(
                operator = operator,
                networkType = networkType,
                isRoaming = isRoaming,
                hasImei = hasImei,
                wifiMac = wifiMac,
            )
        } catch (_: Exception) {
            null
        }
    }
}