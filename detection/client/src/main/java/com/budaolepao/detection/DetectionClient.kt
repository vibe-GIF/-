package com.budaolepao.detection

import com.budaolepao.detection.models.DeviceFingerprint
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class DetectionClient(private val baseUrl: String = "http://10.0.2.2:8000") {

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    private val gson = Gson()
    private val jsonMediaType = "application/json".toMediaType()

    suspend fun sendFingerprint(fingerprint: DeviceFingerprint): Result<DetectionResponse> {
        return withContext(Dispatchers.IO) {
            try {
                val json = gson.toJson(fingerprint)
                val body = json.toRequestBody(jsonMediaType)
                val request = Request.Builder()
                    .url("$baseUrl/api/fingerprint")
                    .post(body)
                    .build()

                val response = client.newCall(request).execute()
                val responseBody = response.body?.string() ?: "{}"

                if (response.isSuccessful) {
                    val result = gson.fromJson(responseBody, DetectionResponse::class.java)
                    Result.success(result)
                } else {
                    Result.failure(Exception("HTTP ${response.code}: $responseBody"))
                }
            } catch (e: Exception) {
                Result.failure(e)
            }
        }
    }

    data class DetectionResponse(
        val status: String,
        val is_emulator: Boolean,
        val risk_score: Double,
        val reasons: List<String>,
    )
}