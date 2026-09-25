# Architecture

## Android
`app/src/main/java/com/qgb/clientmqtt/` owns the Compose UI, permissions, lifecycle, settings, and Python bridge.

## Python
`app/src/main/python/bootstrap.py` is the stable loader. `client_service.py` owns shared RPC/configuration helpers, while `feature_files.py`, `feature_camera.py`, and `feature_wifi.py` are independent replaceable features.

At startup, the app creates private writable `files/py_updates/` and puts it first on `sys.path`. A downloaded `feature_*.py` there overrides the bundled feature and is reloaded on the next call. The APK itself remains immutable.

## MQTT
The copied `multi_mqtt` package handles the existing racing request/response protocol. The client sends short RPC code and receives short JSON metadata only.

## Remote device
RPC code runs on the target device. Directory browsing uses bounded `os.walk` and `os.stat`. File content and photos are uploaded through the target device's `aliyun_git` module, then downloaded by the client.

## Data flow
- Browse: Android -> Python -> MQTT RPC -> target filesystem -> JSON page -> Android.
- Download/view: Android -> RPC upload request -> short URL metadata -> client HTTP download -> memory preview or selected local file.
- Photo: Android -> RPC camera code -> in-memory JPEG -> target-side Aliyun upload -> short metadata -> client HTTP download -> memory image.
