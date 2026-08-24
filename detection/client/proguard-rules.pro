# Budao Lepao Detection - Client Fingerprint Library
# ProGuard rules

-keepclassmembers class com.budaolepao.detection.models.** {
    <fields>;
}

-keep class com.google.gson.** { *; }
-keepclassmembers,allowobfuscation class * {
    @com.google.gson.annotations.SerializedName <fields>;
}

-dontwarn okhttp3.**
-dontwarn okio.**