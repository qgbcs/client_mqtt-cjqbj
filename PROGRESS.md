# Progress

## Current state
- Phase: feature implementation complete; device integration validation remains.
- Completed: Android Compose app with feature pager, left-edge drawer for scripts and targets, online status, permissions, and local script-root selection.
- Completed: per-topic target configuration with stable IDs; request topic, remote root, Aliyun JSON, private key, timeout, and signature fallback are automatically saved and refreshed from external file edits.
- Completed: Python service, bounded remote scan pagination, file transfer, in-memory photo capture, Wi-Fi query, and runtime feature loading.
- Completed: compatible loading of the vendored flat `multi_mqtt.py` library from the app's same-name directory; generated library files remain build-synchronized.
- Completed: static catalog for the three Chaquopy-bundled features, even when the APK has no loose `.py` source entries.
- Completed: Python installer for missing files/camera/wifi scripts in an external `py_updates/`, with alternate GitHub URLs, timeouts, retries, atomic writes, and a visible polling log.
- Completed: moved camera target-code generation into `feature_camera.py`; the Activity only dispatches capture actions.
- Completed: moved Wi-Fi query generation and bounded scan/upload generation into `feature_wifi.py` and `feature_files.py`; `client_service` no longer exposes those feature-specific helpers.
- Completed: feature actions return explicit JSON; Compose formats Wi-Fi data and downloads/decodes photo URLs for preview.
- Completed: target Wi-Fi RPC to `sys/device/k12` returned `192.168.1.106`.
- Completed: Python tests pass (`17/17`); `./debug_build_secexp.sh` generated and verified `out/com.qgb.client-20260916-arm64-v8a.apk` after the independent feature refactor.
- Pending: install and exercise the app UI on Android; validate two responders, pagination, file/Aliyun transfer, both cameras, permissions, external storage, and runtime feature installation.

## Last validation
- `bash -n debug_build_secexp.sh`: passed.
- `python3 -m unittest discover -s tests`: passed (`17/17`) after moving Wi-Fi, scan, and upload code generation into their feature modules.
- Wi-Fi feature RPC through `feature_wifi.info()` for `sys/device/k12`: passed; returned `192.168.1.106` and MAC metadata.
- `./debug_build_secexp.sh`: passed; APK signature and package metadata verified.
- Kotlin `:app:compileDebugKotlin`: passed; only existing deprecation warnings remain.
- Kotlin/Python workspace diagnostics and `git diff --check`: passed.
- Full Android UI/device integration suite, including live external-file refresh and GitHub download on a device: not run.

## Next step
Install the generated APK and validate external script downloads on the target network, the visible retry log, feature override, camera capture/preview, and remaining device workflows.
