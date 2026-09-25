# Progress

## Current state
- Phase: project bootstrap.
- Completed: copied the Android/Chaquopy template into the `client_mqtt/` project root.
- Completed: configured `app/src/main/python/multi_mqtt` as the only project-local library copy.
- Completed: changed the build identity to `ClientMqtt` and removed the external `.gitmodules` sync dependency.
- Completed: added local sync verification to `debug_build_secexp.sh`.
- Completed: replaced the copied input-method entry with a ClientMqtt application and Compose pager.
- Completed: added bounded remote scan code generation with `has_more` and `next_offset`.
- Completed: added in-memory photo and target Wi-Fi RPC code generators without embedding Aliyun credentials.
- Completed: added bounded scan pagination to the Compose file list and JSON response parsing.
- Completed: added target-side upload and client-side Aliyun download helpers for file transfer.
- Completed: split files, camera, and Wi-Fi into independent `feature_*.py` modules.
- Completed: added stable `bootstrap.py` with writable `files/py_updates` override and SHA-256 checked installation.
- Completed: Android pages dispatch through the feature loader instead of importing feature implementations directly.
- Completed: split files, camera, and Wi-Fi into independent Python feature modules.
- Completed: added immutable bootstrap plus writable `files/py_updates` hot-reload path.
- Completed: full root-level `./debug_build_secexp.sh` succeeded with Chaquopy Python 3.12.
- Completed: generated `out/debug-secexp/ClientMqtt-20260925-arm64-v8a.apk` and verified its signature and package id.
- Completed: focused Python tests pass (`5/5`), including runtime replacement and reload.
- In progress: validate runtime feature replacement on an Android device.
- In progress: finish Python callback/log plumbing, file transfer, image display, and device polling.
- Pending: persist all settings through the UI, add focused tests, and run device validation.
- Pending: decode downloaded image bytes in the UI, persist all settings, add periodic online polling, and run device validation.

## Last validation
- `bash -n debug_build_secexp.sh`: passed.
- Local `multi_mqtt` and generated Python copy comparison: passed.
- Python service syntax and generated-code checks: passed.
- Android `:app:compileDebugKotlin`: passed, with a deprecation warning for `ScrollableTabRow`.
- Full root-level APK build: passed; NDK strip warnings come from the container SDK mismatch.
- Device integration tests: not run yet.

## Next step
Connect the remaining capture/download callbacks and settings persistence, then run a device-oriented validation.
