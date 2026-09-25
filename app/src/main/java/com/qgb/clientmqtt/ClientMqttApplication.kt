package com.qgb.clientmqtt

import android.app.Application
import java.io.File
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform

class ClientMqttApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }
        Python.getInstance().getModule("bootstrap").callAttr(
            "init_env",
            File(filesDir, "py_updates").absolutePath
        )
        Python.getInstance().getModule("client_service").callAttr("initialize", filesDir.absolutePath)
    }
}
