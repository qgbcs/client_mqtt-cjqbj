# Feature Script Development

## File location

A feature is a Python file named `feature_<name>.py`.

- Bundled feature: `app/src/main/python/feature_<name>.py`
- Runtime feature: `<script-root>/py_updates/feature_<name>.py`
- Runtime feature files override bundled files with the same name.
- The selected script root is internal app storage by default, or `/sdcard/apm/client_mqtt/` after the user authorizes external storage and enables it in Settings.

## Required manifest

```python
FEATURE = {
    "name": "demo",
    "title": "Demo",
    "version": 1,
    "actions": ["run"],
}
```

The `title` becomes the side pager title. If omitted, the filename name is used. `actions` controls the buttons shown on the generic page.

## Action API

Each action is a top-level function with positional arguments:

```python
import json


def run():
    return json.dumps({"ok": True, "message": "hello"}, ensure_ascii=False)
```

The main app calls the stable Python bridge:

```text
client_service.call_feature(feature_name, action_name, *args)
```

A feature must not import Compose or Android Activity classes. It returns JSON or a short string. Long files and images must use `client_service.upload_remote`, `download_transfer`, or the target-side Aliyun flow; never return large bytes through MQTT.

## Shared services

- `client_service.rpc(code)` sends short target control code through MQTT.
- `client_service.scan_remote(...)` performs bounded target file scanning.
- `client_service.upload_remote(path)` returns short transfer metadata.
- `client_service.download_transfer(url, config, save_to)` downloads outside MQTT.
- `client_service.update_settings(...)` persists settings beside the active script root.

## Runtime installation

A downloaded module is installed atomically and optionally verified:

```python
client_service.install_feature(url, "feature_demo.py", sha256)
```

Only `feature_*.py` filenames are accepted. The module is discovered on the next catalog refresh and loaded on its next action call. Do not execute untrusted scripts without verifying the SHA-256 digest and transport authentication.

## UI communication

The UI never imports feature modules directly. It polls `client_service.feature_catalog()`, creates a pager entry for each descriptor, and invokes actions through `client_service.call_feature`. This keeps the Android APK stable while allowing feature scripts to evolve independently.
