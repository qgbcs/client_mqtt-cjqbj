"""Stable runtime loader for hot-swappable Python features."""

import hashlib
import importlib
import os
import sys
import tempfile
import urllib.request

_UPDATE_DIR = None


def init_env(update_dir):
    global _UPDATE_DIR
    _UPDATE_DIR = os.path.abspath(str(update_dir))
    os.makedirs(_UPDATE_DIR, exist_ok=True)
    if _UPDATE_DIR in sys.path:
        sys.path.remove(_UPDATE_DIR)
    sys.path.insert(0, _UPDATE_DIR)
    importlib.invalidate_caches()
    return {"ok": True, "update_dir": _UPDATE_DIR}


def update_dir():
    return _UPDATE_DIR


def _module_name(feature):
    value = str(feature).strip()
    if not value.isidentifier() and not (value.startswith("feature_") and value[8:].isidentifier()):
        raise ValueError("invalid feature name")
    return value if value.startswith("feature_") else "feature_" + value


def load_feature(feature):
    module_name = _module_name(feature)
    importlib.invalidate_caches()
    module = sys.modules.get(module_name)
    if module is None:
        return importlib.import_module(module_name)
    module_file = os.path.abspath(str(getattr(module, "__file__", "")))
    if _UPDATE_DIR and module_file.startswith(_UPDATE_DIR + os.sep):
        cache_dir = os.path.join(_UPDATE_DIR, "__pycache__")
        if os.path.isdir(cache_dir):
            for filename in os.listdir(cache_dir):
                if filename.startswith(module_name + ".") and filename.endswith(".pyc"):
                    os.unlink(os.path.join(cache_dir, filename))
        sys.modules.pop(module_name, None)
        importlib.invalidate_caches()
        return importlib.import_module(module_name)
    return module


def list_features():
    names = set()
    roots = [_UPDATE_DIR, os.path.dirname(__file__)]
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for filename in os.listdir(root):
            if filename.startswith("feature_") and filename.endswith(".py"):
                names.add(filename[8:-3])
    return sorted(names)


def call_feature(feature, action="run", *args):
    module = load_feature(feature)
    function = getattr(module, str(action), None)
    if not callable(function):
        raise AttributeError(f"feature {feature!r} has no action {action!r}")
    return function(*args)


def install_feature(url, filename, sha256=""):
    """Download one feature into the writable update directory atomically."""
    if not _UPDATE_DIR:
        raise RuntimeError("bootstrap is not initialized")
    name = os.path.basename(str(filename))
    if not (name.startswith("feature_") and name.endswith(".py")):
        raise ValueError("only feature_*.py modules can be installed")
    target = os.path.join(_UPDATE_DIR, name)
    fd, temporary = tempfile.mkstemp(prefix=name + ".", dir=_UPDATE_DIR)
    try:
        with os.fdopen(fd, "wb") as output, urllib.request.urlopen(str(url), timeout=30) as response:
            while True:
                chunk = response.read(131072)
                if not chunk:
                    break
                output.write(chunk)
        if sha256:
            digest = hashlib.sha256(open(temporary, "rb").read()).hexdigest()
            if digest.lower() != str(sha256).lower():
                raise ValueError("feature checksum mismatch")
        os.replace(temporary, target)
        importlib.invalidate_caches()
        return {"ok": True, "filename": name, "sha256": hashlib.sha256(open(target, "rb").read()).hexdigest()}
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
