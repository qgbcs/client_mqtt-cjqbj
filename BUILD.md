# Build

Run from the `client_mqtt/` directory:

```sh
./debug_build_secexp.sh
```

The script synchronizes `MULTI_MQTT_SOURCE` into `app/src/main/python/multi_mqtt`, verifies the copy, builds a debug APK, normalizes the archive, signs it, and writes the result under `out/debug-secexp/`. The default source is the sibling `../multi_mqtt` directory.

Useful overrides:

- `APPLICATION_ID=com.qgb.clientmqtt`
- `VERSION_CODE=...`
- `VERSION_NAME=...`
- `APP_NAME='Client MQTT'`
- `APK_BASENAME=ClientMqtt`
- `BUILD_ABIS=arm64-v8a`
- `SECEXP=1`
- `ANDROID_HOME=/path/to/sdk`
- `MULTI_MQTT_SOURCE=/path/to/multi_mqtt`

The Android SDK must provide platform 36 and a working build-tools `aapt`, `apksigner`, and Gradle wrapper environment. Chaquopy is configured for Python 3.12 because that interpreter is available in the development container; change the version only when the matching local interpreter is installed.
