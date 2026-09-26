import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "src" / "main" / "python"))

import client_service
import feature_camera
import feature_files
import feature_wifi


class ClientServiceTests(unittest.TestCase):
    def test_mqtt_loader_uses_flat_modules_not_package_submodules(self):
        previous_file = client_service.__file__
        previous_path = list(sys.path)
        previous_modules = {
            name: module for name, module in sys.modules.items()
            if name == "multi_mqtt" or name.startswith("multi_mqtt.") or name == "client_mqtt"
        }
        with tempfile.TemporaryDirectory() as directory:
            module_dir = Path(directory) / "multi_mqtt"
            module_dir.mkdir()
            (module_dir / "multi_mqtt.py").write_text("class MultiMQTTManager: pass\n", encoding="utf-8")
            (module_dir / "client_mqtt.py").write_text(
                "from multi_mqtt import MultiMQTTManager\ndef rpc(*args, **kwargs): return {'ok': True}\n",
                encoding="utf-8",
            )
            try:
                client_service.__file__ = str(Path(directory) / "client_service.py")
                for name in tuple(sys.modules):
                    if name == "multi_mqtt" or name.startswith("multi_mqtt.") or name == "client_mqtt":
                        sys.modules.pop(name, None)

                module = client_service._mqtt_client_module()

                self.assertEqual(module.__name__, "client_mqtt")
                self.assertEqual(Path(module.__file__), module_dir / "client_mqtt.py")
                self.assertTrue(module.rpc()["ok"])
            finally:
                client_service.__file__ = previous_file
                sys.path[:] = previous_path
                for name in tuple(sys.modules):
                    if name == "multi_mqtt" or name.startswith("multi_mqtt.") or name == "client_mqtt":
                        sys.modules.pop(name, None)
                sys.modules.update(previous_modules)

    def test_broken_runtime_feature_returns_json_instead_of_raising(self):
        import bootstrap

        previous_update_dir = bootstrap._UPDATE_DIR
        previous_path = list(sys.path)
        previous_module = sys.modules.pop("feature_broken", None)
        with tempfile.TemporaryDirectory() as directory:
            try:
                bootstrap.init_env(directory)
                Path(directory, "feature_broken.py").write_text(
                    "FEATURE = {'name': 'broken'}\ndef run():\n    raise RuntimeError('plugin failed')\n",
                    encoding="utf-8",
                )

                result = json.loads(client_service.call_feature("broken", "run"))

                self.assertFalse(result["ok"])
                self.assertEqual(result["feature"], "broken")
                self.assertEqual(result["error"], "RuntimeError: plugin failed")

                Path(directory, "feature_broken.py").write_text(
                    "FEATURE = {'name': 'broken'}\ndef run():\n    raise SystemExit('plugin exit')\n",
                    encoding="utf-8",
                )
                result = json.loads(client_service.call_feature("broken", "run"))
                self.assertEqual(result["error"], "SystemExit: plugin exit")
            finally:
                bootstrap._UPDATE_DIR = previous_update_dir
                sys.path[:] = previous_path
                sys.modules.pop("feature_broken", None)
                if previous_module is not None:
                    sys.modules["feature_broken"] = previous_module

    def test_rpc_passes_private_key_expression_to_mqtt_normalizer(self):
        previous_state = client_service._STATE.copy()
        with tempfile.TemporaryDirectory() as files_dir:
            try:
                client_service.initialize(files_dir)
                client_service.update_device_settings("sys/device/request", {
                    "request_topic": "sys/device/key-test",
                    "private_key": "2**64",
                })
                mqtt_module = mock.Mock()
                mqtt_module.rpc.return_value = {"ok": True, "r": "{}"}
                with mock.patch.object(client_service, "_mqtt_client_module", return_value=mqtt_module):
                    client_service.rpc("r = {}")

                self.assertEqual(mqtt_module.rpc.call_args.kwargs["client_private_key_bytes"], "2**64")
            finally:
                client_service._STATE.clear()
                client_service._STATE.update(previous_state)

    def test_scan_code_is_bounded_and_json_based(self):
        code = feature_files.build_scan_code("/data/data", offset=10, limit=3)
        ast.parse(code)
        self.assertIn("has_more", code)
        self.assertIn("next_offset", code)
        self.assertIn("len(items) >= start + limit", code)

    def test_path_cannot_escape_root(self):
        self.assertEqual(
            client_service.normalize_relative_path("/data/data", "logs/today.txt"),
            "/data/data/logs/today.txt",
        )
        with self.assertRaises(ValueError):
            client_service.normalize_relative_path("/data/data", "../secret")

    def test_photo_code_has_no_mqtt_payload_or_aliyun_secret(self):
        code = feature_camera.build_photo_code(1)
        self.assertIn("bytes(data)", code)
        self.assertIn("aliyun_git.upload", code)
        self.assertNotIn('token=', code)
        self.assertNotIn('domain=', code)

    def test_feature_rpc_generators_are_owned_by_features(self):
        self.assertFalse(hasattr(client_service, "build_wifi_code"))
        self.assertFalse(hasattr(client_service, "scan_remote"))
        self.assertFalse(hasattr(client_service, "build_scan_code"))
        self.assertFalse(hasattr(client_service, "upload_remote"))
        wifi_code = feature_wifi.build_wifi_code()
        ast.parse(wifi_code)
        self.assertIn('"mac"', wifi_code)
        self.assertIn('"ip"', wifi_code)
        ast.parse(feature_files.build_upload_code("/data/file.txt"))

    def test_wifi_feature_returns_json_for_the_app_ui(self):
        response = {"r": json.dumps({"ok": True, "wifi": {"ip": "192.168.1.11"}})}
        with mock.patch.object(client_service, "rpc", return_value=response):
            result = json.loads(feature_wifi.info())
        self.assertEqual(result["wifi"]["ip"], "192.168.1.11")

        timeout = {"ok": False, "error": "RPC timeout"}
        with mock.patch.object(client_service, "rpc", return_value=timeout):
            result = json.loads(feature_wifi.info())
        self.assertEqual(result, timeout)

    def test_parse_json_result_preserves_structured_rpc_errors(self):
        response = {"ok": False, "error": "RPC timeout", "elapsed_ms": 5000}
        self.assertEqual(client_service.parse_json_result(response), response)

    def test_files_feature_actions_use_shared_rpc_and_return_json(self):
        page = {"ok": True, "items": [], "has_more": False, "next_offset": 0}
        with mock.patch.object(client_service, "rpc", return_value={"r": json.dumps(page)}) as rpc_call:
            result = json.loads(feature_files.scan("/data", 0, 20))
        self.assertEqual(result, page)
        self.assertIn("os.walk", rpc_call.call_args.args[0])

        transfer = {"ok": True, "url": "https://example.invalid/file", "name": "file"}
        with mock.patch.object(client_service, "rpc", return_value={"r": json.dumps(transfer)}) as rpc_call:
            result = json.loads(feature_files.upload("/data/file"))
        self.assertEqual(result, transfer)
        self.assertIn("aliyun_git.upload", rpc_call.call_args.args[0])

    def test_camera_feature_returns_json_metadata_for_the_app_ui(self):
        capture = {"ok": True, "url": "https://example.invalid/photo.jpg", "facing": 1}
        with mock.patch.object(client_service, "rpc", return_value={"r": json.dumps(capture)}) as rpc_call:
            result = json.loads(feature_camera.capture(1))
        self.assertEqual(result, capture)
        self.assertIn("Camera.open(1)", rpc_call.call_args.args[0])

    def test_device_settings_are_isolated_by_request_topic(self):
        previous_state = client_service._STATE.copy()
        with tempfile.TemporaryDirectory() as files_dir:
            try:
                client_service.initialize(files_dir)
                client_service.update_device_settings("sys/device/request", {
                    "request_topic": "sys/device/one",
                    "remote_root": "/data/one",
                })
                client_service.update_device_settings("", {
                    "request_topic": "sys/device/two",
                    "remote_root": "/data/two",
                })
                client_service.update_aliyun_settings({"aliyun": {"bucket": "shared"}})

                client_service.select_device("sys/device/one")
                first = json.loads(client_service.device_settings())
                client_service.select_device("sys/device/two")
                second = json.loads(client_service.device_settings())

                self.assertEqual(first["remote_root"], "/data/one")
                self.assertEqual(second["remote_root"], "/data/two")
                self.assertNotIn("aliyun", first)
                self.assertNotIn("aliyun", second)
                self.assertEqual(json.loads(client_service.aliyun_settings())["aliyun"], {"bucket": "shared"})
            finally:
                client_service._STATE.clear()
                client_service._STATE.update(previous_state)

    def test_device_id_survives_topic_rename_and_external_file_edit(self):
        previous_state = client_service._STATE.copy()
        with tempfile.TemporaryDirectory() as files_dir:
            try:
                client_service.initialize(files_dir)
                created = json.loads(client_service.update_device_settings("sys/device/request", {
                    "request_topic": "sys/device/old",
                    "remote_root": "/data/old",
                    "aliyun": {"bucket": "before"},
                }))
                device_id = created["id"]
                renamed = json.loads(client_service.update_device_settings(device_id, {
                    "request_topic": "sys/device/new",
                    "remote_root": "/data/new",
                    "aliyun": {"bucket": "after"},
                }))
                self.assertEqual(renamed["id"], device_id)
                self.assertEqual(len(json.loads(client_service.device_catalog())), 1)

                config_path = client_service._STATE["config_path"]
                with open(config_path, "r", encoding="utf-8") as config_file:
                    config = json.load(config_file)
                config["devices"][0]["remote_root"] = "/data/external-edit"
                with open(config_path, "w", encoding="utf-8") as config_file:
                    json.dump(config, config_file)

                refreshed = json.loads(client_service.device_settings(device_id))
                self.assertEqual(refreshed["request_topic"], "sys/device/new")
                self.assertEqual(refreshed["remote_root"], "/data/external-edit")
            finally:
                client_service._STATE.clear()
                client_service._STATE.update(previous_state)

    def test_incomplete_aliyun_draft_keeps_last_valid_global_config(self):
        previous_state = client_service._STATE.copy()
        with tempfile.TemporaryDirectory() as files_dir:
            try:
                client_service.initialize(files_dir)
                client_service.update_aliyun_settings({"aliyun": {"bucket": "valid"}})
                saved = json.loads(client_service.update_aliyun_settings({"aliyun_json_draft": "{"}))

                self.assertEqual(saved["aliyun"], {"bucket": "valid"})
                self.assertEqual(saved["aliyun_json_draft"], "{")
            finally:
                client_service._STATE.clear()
                client_service._STATE.update(previous_state)

    def test_initialize_migrates_legacy_per_topic_aliyun_to_shared_setting(self):
        previous_state = client_service._STATE.copy()
        with tempfile.TemporaryDirectory() as files_dir:
            try:
                path = Path(files_dir) / "client_mqtt.json"
                path.write_text(json.dumps({
                    "devices": [{
                        "request_topic": "sys/device/one",
                        "aliyun": {"bucket": "legacy"},
                    }]
                }), encoding="utf-8")

                client_service.initialize(files_dir)
                config = client_service.load_config()

                self.assertEqual(config["aliyun"], {"bucket": "legacy"})
                self.assertNotIn("aliyun", config["devices"][0])
            finally:
                client_service._STATE.clear()
                client_service._STATE.update(previous_state)

    def test_device_catalog_assigns_id_to_external_target(self):
        previous_state = client_service._STATE.copy()
        with tempfile.TemporaryDirectory() as files_dir:
            try:
                client_service.initialize(files_dir)
                config_path = client_service._STATE["config_path"]
                with open(config_path, "r", encoding="utf-8") as config_file:
                    config = json.load(config_file)
                config["devices"].append({"request_topic": "sys/device/external"})
                with open(config_path, "w", encoding="utf-8") as config_file:
                    json.dump(config, config_file)

                devices = json.loads(client_service.device_catalog())
                added = next(device for device in devices if device["request_topic"] == "sys/device/external")
                self.assertTrue(added["id"])
                self.assertEqual(added["remote_root"], "/data/data")
                with open(config_path, "r", encoding="utf-8") as config_file:
                    saved = json.load(config_file)
                self.assertEqual(saved["devices"][1]["id"], added["id"])
            finally:
                client_service._STATE.clear()
                client_service._STATE.update(previous_state)

    def test_builtin_feature_installer_writes_scripts_and_logs_progress(self):
        previous_state = client_service._STATE.copy()
        with tempfile.TemporaryDirectory() as script_root:
            try:
                import bootstrap

                def install(url, filename, update_dir, progress, **kwargs):
                    Path(update_dir, filename).write_text(
                        f"FEATURE = {{'name': '{filename[8:-3]}'}}\n",
                        encoding="utf-8",
                    )
                    progress(f"{filename}: installed for test")
                    return {"filename": filename, "ok": True}

                with mock.patch.object(bootstrap, "install_feature", side_effect=install) as download:
                    result = json.loads(client_service.install_builtin_features(script_root))
                    self.assertTrue(result["ok"])
                    self.assertEqual(len(result["results"]), 3)
                    self.assertTrue(all(item["ok"] for item in result["results"]))
                    self.assertTrue(any("installed for test" in item for item in result["logs"]))
                    self.assertEqual(download.call_count, 3)

                    second = json.loads(client_service.install_builtin_features(script_root))
                    self.assertTrue(all(item.get("skipped") for item in second["results"]))
                    self.assertEqual(download.call_count, 3)
            finally:
                client_service._STATE.clear()
                client_service._STATE.update(previous_state)


if __name__ == "__main__":
    unittest.main()
