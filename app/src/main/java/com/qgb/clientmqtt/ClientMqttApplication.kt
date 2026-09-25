package com.qgb.clientmqtt

import android.app.Application
import android.os.Build
import android.os.Environment
import java.io.File
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

class ClientMqttApplication : Application() {
    private fun scriptRoot(): File {
        val preferences = getSharedPreferences("client_mqtt", MODE_PRIVATE)
        val useExternal = preferences.getBoolean("use_external_scripts", false)
        val external = File(Environment.getExternalStorageDirectory(), "apm/client_mqtt")
        val externalAvailable = Build.VERSION.SDK_INT < Build.VERSION_CODES.R || Environment.isExternalStorageManager()
        return if (useExternal && externalAvailable) external else File(filesDir, "client_mqtt")
    }

    override fun onCreate() {
        super.onCreate()
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }
        val root = scriptRoot()
        root.mkdirs()
        Python.getInstance().getModule("bootstrap").callAttr(
            "init_env",
            File(root, "py_updates").absolutePath
        )
        Python.getInstance().getModule("client_service").callAttr("initialize", root.absolutePath)
    }
}
