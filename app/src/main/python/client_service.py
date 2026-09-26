"""Client-side bridge for MQTT RPC and remote file operations."""

import json
import base64
import copy
import importlib
import importlib.util
import os
import sys
import threading
import uuid
from pathlib import PurePosixPath

import time
_STATE = {
    "files_dir": None,
    "lock": threading.RLock(),
    "selected_topic": None,
    "selected_device_id": None,
    "last_config": None,
    "operation_logs": [],
}
_DEFAULT_DEVICE = {
    "name": "Target",
    "request_topic": "sys/device/request",
    "private_key": "",
    "allow_no_server_pubkey_response": True,
    "timeout": 10,
    "remote_root": "/data/data",
    "aliyun": {},
}
_CONFIG_NAME = "client_mqtt.json"
_BUILTIN_FEATURE_SOURCES = {
    "feature_files.py": (
        "https://github.com/cjqbj/client_mqtt-cjqbj/raw/refs/heads/main/app/src/main/python/feature_files.py",
        "https://raw.githubusercontent.com/cjqbj/client_mqtt-cjqbj/main/app/src/main/python/feature_files.py",
    ),
    "feature_camera.py": (
        "https://github.com/cjqbj/client_mqtt-cjqbj/raw/refs/heads/main/app/src/main/python/feature_camera.py",
        "https://raw.githubusercontent.com/cjqbj/client_mqtt-cjqbj/main/app/src/main/python/feature_camera.py",
    ),
    "feature_wifi.py": (
        "https://github.com/cjqbj/client_mqtt-cjqbj/raw/refs/heads/main/app/src/main/python/feature_wifi.py",
        "https://raw.githubusercontent.com/cjqbj/client_mqtt-cjqbj/main/app/src/main/python/feature_wifi.py",
    ),
}


def call_feature(feature, action="run", *args):
    """Dispatch through the stable bootstrap so feature modules can be replaced."""
    import bootstrap
    return bootstrap.call_feature(feature, action, *args)


def _mqtt_client_module():
    module_dir = os.path.join(os.path.dirname(__file__), "multi_mqtt")
    source_file = os.path.join(module_dir, "multi_mqtt.py")
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    package = sys.modules.get("multi_mqtt")
    package_file = os.path.abspath(str(getattr(package, "__file__", "")))
    if package_file != os.path.abspath(source_file) or not hasattr(package, "MultiMQTTManager"):
        for name in tuple(sys.modules):
            if name == "multi_mqtt" or name.startswith("multi_mqtt."):
                sys.modules.pop(name, None)
        spec = importlib.util.spec_from_file_location(
            "multi_mqtt", source_file, submodule_search_locations=[module_dir]
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"Unable to load MQTT library from {source_file}")
        package = importlib.util.module_from_spec(spec)
        sys.modules["multi_mqtt"] = package
        spec.loader.exec_module(package)
    return importlib.import_module("multi_mqtt.client_mqtt")


def feature_catalog():
    import bootstrap
    return json.dumps(bootstrap.describe_features(), ensure_ascii=False)


def install_feature(url, filename, sha256=""):
    import bootstrap
    return bootstrap.install_feature(url, filename, sha256)


def _append_operation_log(message):
    entry = f"{time.strftime('%H:%M:%S')} {message}"
    with _STATE["lock"]:
        logs = _STATE.setdefault("operation_logs", [])
        logs.append(entry)
        del logs[:-200]
    return entry


def operation_logs():
    with _STATE["lock"]:
        return json.dumps(list(_STATE.get("operation_logs", [])), ensure_ascii=False)


def install_builtin_features(script_root, retries=4, timeout=15):
    """Install missing bundled feature scripts into a chosen script root."""
    import bootstrap

    update_dir = os.path.join(os.path.abspath(str(script_root)), "py_updates")
    os.makedirs(update_dir, exist_ok=True)
    with _STATE["lock"]:
        _STATE.setdefault("operation_logs", []).clear()
    _append_operation_log(f"Installing built-in features into {update_dir}")
    results = []

    for filename, urls in _BUILTIN_FEATURE_SOURCES.items():
        destination = os.path.join(update_dir, filename)
        if os.path.isfile(destination):
            try:
                with open(destination, "rb") as feature_file:
                    compile(feature_file.read(), filename, "exec")
                _append_operation_log(f"{filename}: already present; skipped")
                results.append({"filename": filename, "ok": True, "skipped": True})
                continue
            except (OSError, SyntaxError):
                _append_operation_log(f"{filename}: existing file is invalid; downloading replacement")

        try:
            result = bootstrap.install_feature(
                urls[0],
                filename,
                update_dir=update_dir,
                retries=retries,
                timeout=timeout,
                fallback_urls=urls[1:],
                progress=_append_operation_log,
            )
            results.append(result)
        except Exception as error:
            detail = f"{type(error).__name__}: {error}"[:300]
            _append_operation_log(f"{filename}: failed: {detail}")
            results.append({"filename": filename, "ok": False, "error": detail})

    installed = sum(bool(item.get("ok")) for item in results)
    _append_operation_log(f"Finished: {installed}/{len(results)} feature files ready")
    return json.dumps({
        "ok": installed == len(results),
        "update_dir": update_dir,
        "results": results,
        "logs": json.loads(operation_logs()),
    }, ensure_ascii=False)


def initialize(files_dir):
    _STATE["files_dir"] = str(files_dir)
    path = os.path.join(_STATE["files_dir"], _CONFIG_NAME)
    _STATE["config_path"] = path
    if not os.path.isfile(path):
        save_config({"devices": [_DEFAULT_DEVICE.copy()], "scan_limit": 100, "remote_root": "/data/data"})
    with _STATE["lock"]:
        config = load_config()
        devices = [item for item in config.get("devices", []) if isinstance(item, dict)]
        if not devices:
            devices = [_DEFAULT_DEVICE.copy()]
        for device in devices:
            device.setdefault("id", uuid.uuid4().hex)
            device.setdefault("remote_root", config.get("remote_root", "/data/data"))
            device.setdefault("aliyun", config.get("aliyun", {}))
        config["devices"] = devices
        config.pop("remote_root", None)
        config.pop("aliyun", None)
        save_config(config)
        _STATE["selected_device_id"] = devices[0]["id"]
        _STATE["selected_topic"] = devices[0].get("request_topic", _DEFAULT_DEVICE["request_topic"])
    return {"ok": True, "files_dir": _STATE["files_dir"]}


def update_settings(values):
    with _STATE["lock"]:
        config = load_config()
        if isinstance(values, str):
            values = json.loads(values)
        config.update(dict(values or {}))
        save_config(config)
        return json.dumps(config, ensure_ascii=False)


def device_catalog():
    config = load_config()
    devices = config.get("devices") or [_DEFAULT_DEVICE.copy()]
    changed = False
    for device in devices:
        if not device.get("id"):
            device["id"] = uuid.uuid4().hex
            changed = True
        device.setdefault("remote_root", config.get("remote_root", "/data/data"))
        device.setdefault("aliyun", config.get("aliyun", {}))
    if changed:
        config["devices"] = devices
        save_config(config)
    return json.dumps(devices, ensure_ascii=False)


def device_settings(device_ref=None):
    selected = _device_config(device_ref)
    return json.dumps(selected, ensure_ascii=False)


def select_device(device_ref):
    selected = _device_config(device_ref)
    _STATE["selected_device_id"] = selected["id"]
    _STATE["selected_topic"] = selected["request_topic"]
    return json.dumps({"ok": True, "device": selected}, ensure_ascii=False)


def update_device_settings(existing_device, values):
    if isinstance(values, str):
        values = json.loads(values)
    if not isinstance(values, dict):
        raise ValueError("device settings must be a JSON object")
    values = dict(values)
    request_topic = str(values.get("request_topic", "")).strip()
    if not request_topic:
        raise ValueError("request_topic is required")
    aliyun = values.get("aliyun", {})
    if not isinstance(aliyun, dict):
        raise ValueError("aliyun must be a JSON object")
    aliyun_draft = values.pop("aliyun_json_draft", None)
    if aliyun_draft is not None and not isinstance(aliyun_draft, str):
        raise ValueError("aliyun_json_draft must be a string")
    timeout_draft = values.pop("timeout_draft", None)
    if timeout_draft is not None and not isinstance(timeout_draft, str):
        raise ValueError("timeout_draft must be a string")

    with _STATE["lock"]:
        config = load_config()
        devices = config.get("devices") or []
        selected = next((
            device for device in devices
            if device.get("id") == existing_device or device.get("request_topic") == existing_device
        ), None)
        if selected is None:
            selected = _DEFAULT_DEVICE.copy()
            selected["id"] = uuid.uuid4().hex
            devices.append(selected)
        selected.update(values)
        selected["id"] = selected.get("id") or uuid.uuid4().hex
        selected["request_topic"] = request_topic
        selected["name"] = str(values.get("name") or request_topic.rsplit("/", 1)[-1])
        selected["remote_root"] = str(values.get("remote_root", "/data/data"))
        if "aliyun" in values:
            selected["aliyun"] = aliyun
        else:
            selected.setdefault("aliyun", {})
        if aliyun_draft is None:
            selected.pop("aliyun_json_draft", None)
        else:
            selected["aliyun_json_draft"] = aliyun_draft
        if timeout_draft is None:
            selected.pop("timeout_draft", None)
        else:
            selected["timeout_draft"] = timeout_draft
        config["devices"] = devices
        save_config(config)
        _STATE["selected_device_id"] = selected["id"]
        _STATE["selected_topic"] = request_topic
        return json.dumps(selected, ensure_ascii=False)


def load_config():
    path = _STATE.get("config_path")
    if not path or not os.path.isfile(path):
        return {"devices": [_DEFAULT_DEVICE.copy()], "scan_limit": 100, "remote_root": "/data/data"}
    with _STATE["lock"]:
        try:
            with open(path, "r", encoding="utf-8") as config_file:
                value = json.load(config_file)
            if isinstance(value, dict):
                _STATE["last_config"] = copy.deepcopy(value)
                return value
        except (OSError, ValueError):
            pass
        previous = _STATE.get("last_config")
        if isinstance(previous, dict):
            return copy.deepcopy(previous)
        return {"devices": [_DEFAULT_DEVICE.copy()], "scan_limit": 100, "remote_root": "/data/data"}


def save_config(value):
    path = _STATE.get("config_path")
    if not path:
        return {"ok": False, "error": "service is not initialized"}
    with _STATE["lock"]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        temporary = path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as config_file:
            json.dump(value, config_file, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
        _STATE["last_config"] = copy.deepcopy(value)
    return {"ok": True}


def _device_config(device=None):
    config = load_config()
    devices = config.get("devices") or [_DEFAULT_DEVICE.copy()]
    device_ref = device or _STATE.get("selected_device_id") or _STATE.get("selected_topic")
    selected = next((
        item for item in devices
        if item.get("id") == device_ref or item.get("request_topic") == device_ref
    ), None)
    selected = selected or devices[0]
    merged = _DEFAULT_DEVICE.copy()
    merged.update(selected)
    return merged


def rpc(code, device=None):
    """Execute short control code through the existing MQTT racing client."""
    client_mqtt = _mqtt_client_module()
    selected = _device_config(device)
    private_key = selected.get("private_key") or None
    aliyun = json.dumps(selected.get("aliyun") or {}, ensure_ascii=False)
    code = (
        "import sys\n"
        f"sys.__dict__.setdefault('_qgb_dict', {{}}).setdefault('aliyun_git', {{}}).update({aliyun})\n"
        + code
    )
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
    _set_aliyun_config(config or _device_config().get("aliyun", {}))
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
