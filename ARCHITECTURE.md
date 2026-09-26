# Architecture

## Android
`app/src/main/java/com/qgb/clientmqtt/` owns the Compose UI, permissions, lifecycle, settings, and Python bridge. The home screen uses a left-edge drawer for feature scripts and target topics, plus a horizontal pager for feature pages. Android-only settings such as script-root selection and permissions are separate from target connection settings.

## Python
`app/src/main/python/bootstrap.py` is the stable loader. `client_service.py` owns generic RPC, JSON, configuration, and transfer bridges. Domain-specific target code generation and actions live in independently replaceable `feature_files.py`, `feature_camera.py`, and `feature_wifi.py`.

At startup, the app creates the selected script root's writable `py_updates/` and puts it first on `sys.path`. Chaquopy may package bundled Python modules without their `.py` source files, so `bootstrap.py` keeps a static catalog for the built-in files, camera, and Wi-Fi features and imports them by module name. A downloaded `feature_*.py` in `py_updates/` overrides a bundled module, including one already loaded, and is used on the next call. The APK itself remains immutable. Target records with stable IDs are stored in `client_mqtt.json`; each request topic carries its own remote root, private key, timeout, and signature-fallback option. Shared Aliyun JSON lives at the config root and is used by every target. Both forms save edits automatically, and the UI polls the file once per second for external edits.

The Compose pager polls `client_service.feature_catalog()` every three seconds. Each descriptor becomes one side-swipe page titled from the script manifest. The UI communicates with scripts only through `client_service.call_feature(name, action, *args)`; the dispatcher catches Python `BaseException` from a feature and returns structured JSON so it cannot escape through Chaquopy into the Activity. Features return JSON for UI display. Photo actions return short transfer metadata, after which Compose downloads and previews the image outside MQTT. Native/JVM fatal errors remain outside the Python exception boundary.

## MQTT
The generated `multi_mqtt` directory contains upstream flat modules. `client_service.py` loads `multi_mqtt.py` as a flat module and imports sibling `client_mqtt.py` at top level; do not load it as `multi_mqtt.client_mqtt`, because Chaquopy does not treat it as a package. Do not hand-edit this generated directory. The client sends short RPC code and receives short JSON metadata only; shared Aliyun configuration is initialized in the target interpreter before feature code runs. Camera RPC generation and capture behavior live in `feature_camera.py`; the Compose camera page only dispatches its action and displays returned media.

When an external script root is selected, the app can install missing feature modules directly into its `py_updates/` using GitHub with timeouts, host fallback, exponential retry, atomic writes, and a UI-polled operation log.

## Remote device
RPC code runs on the target device. Directory browsing uses bounded `os.walk` and `os.stat`. File content and photos are uploaded through the target device's `aliyun_git` module, then downloaded by the client.

## Data flow
- Browse: Android -> Python -> MQTT RPC -> target filesystem -> JSON page -> Android.
- Download/view: Android -> RPC upload request -> short URL metadata -> client HTTP download -> memory preview or selected local file.
- Photo: Android -> RPC camera code -> in-memory JPEG -> target-side Aliyun upload -> short metadata -> client HTTP download -> memory image.
