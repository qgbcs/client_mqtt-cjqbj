# Protocol

## Browse request
The generated target code receives:

- `root`: configured allowed root on the target device
- `offset`: number of sorted file entries to skip
- `limit`: maximum entries for this page
- `recursive`: currently `true`

The result must be JSON with `ok`, `root`, `items`, `has_more`, and `next_offset`. Each item contains a relative path, kind, size, modified time, and optional error. RPC `r` must be a JSON string so the client never parses Python pretty repr.

## Transfer result
A file transfer RPC returns only short metadata: `ok`, `url`, `name`, `size`, `content_type`, and optional `error`. The JPEG or file bytes never appear in the MQTT response.

## Photo result
Photo RPC returns the same transfer metadata plus camera facing and capture duration. The target must convert the Java callback buffer to Python `bytes`, upload it directly, and release the camera in `finally` without creating a photo file.

## Errors
Use structured error fields and preserve the target traceback in the log channel only. Redact tokens, private keys, and authorization headers before forwarding logs to Android.

## Hot-updatable features
Feature modules use the names `feature_files`, `feature_camera`, and `feature_wifi`. The stable dispatcher calls `bootstrap.call_feature(feature, action, *args)`. Runtime updates must be `feature_*.py` files written atomically into the app-private `files/py_updates/` directory. Optional SHA-256 verification is supported by `bootstrap.install_feature`; unsigned or path-traversal filenames are rejected.

The UI catalog refresh interval is three seconds. A script is not required to ship an Android class: its `FEATURE.title` is the pager title and its `FEATURE.actions` become generic action buttons. See `FEATURE_DEVELOPMENT.md` for the complete contract.
