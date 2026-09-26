import com.android.build.gradle.internal.api.BaseVariantOutputImpl

plugins {
    alias(libs.plugins.android.application)
    id("com.chaquo.python")
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

chaquopy {
    defaultConfig {
        version = "3.12"
        pip {
            install("pip")
            install("wheel")
            install("setuptools")
            install("paho-mqtt")
            install("ecdsa")
            install("requests")
        }
    }
}

val supportedAbis = listOf("armeabi-v7a", "arm64-v8a", "x86", "x86_64")
val buildAbis = providers.gradleProperty("buildAbis").orNull
    ?.split(",")?.map { it.trim() }?.filter { it.isNotEmpty() }
    ?: listOf("arm64-v8a")
require(buildAbis.all { it in supportedAbis }) {
    "buildAbis must contain only: ${supportedAbis.joinToString(", ")}"
}

val configuredAppName = providers.gradleProperty("appName").orElse("Client MQTT").get()
val configuredApplicationId = providers.gradleProperty("applicationId")
    .orElse("com.qgb.clientmqtt").get()
val configuredVersionCode = providers.gradleProperty("versionCode").orElse("20260925").get().toInt()
val configuredVersionName = providers.gradleProperty("versionName").orElse("0.1").get()
val configuredApkBaseName = providers.gradleProperty("apkBaseName").orElse("ClientMqtt").get()
val escapedAppName = configuredAppName.replace("\\", "\\\\").replace("\"", "\\\"")

android {
    namespace = "com.qgb.clientmqtt"
    compileSdk = 36
    defaultConfig {
        applicationId = configuredApplicationId
        minSdk = 27
        targetSdk = 35
        versionCode = configuredVersionCode
        versionName = configuredVersionName
        buildConfigField("String", "APP_NAME", "\"$escapedAppName\"")
        resValue("string", "app_name", configuredAppName)
        ndk { abiFilters += buildAbis }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlin { compilerOptions { jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17) } }
    buildFeatures { compose = true; buildConfig = true }
    packaging { jniLibs { useLegacyPackaging = true } }
    splits {
        abi {
            isEnable = buildAbis.size > 1
            reset()
            if (buildAbis.size > 1) include(*buildAbis.toTypedArray())
            isUniversalApk = buildAbis.size > 1
        }
    }
}

android.applicationVariants.all {
    outputs.all {
        val abi = filters.find { it.filterType.toString() == "ABI" }?.identifier
            ?: buildAbis.singleOrNull() ?: "universal"
        (this as BaseVariantOutputImpl).outputFileName = "$configuredApkBaseName-$versionCode-$abi.apk"
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.foundation)
    implementation(libs.androidx.compose.material.icons.extended)
    implementation(libs.kotlinx.coroutines.core)
}
