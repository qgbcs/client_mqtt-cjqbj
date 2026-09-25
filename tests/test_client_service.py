import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "src" / "main" / "python"))

import client_service


class ClientServiceTests(unittest.TestCase):
    def test_scan_code_is_bounded_and_json_based(self):
        code = client_service.build_scan_code("/data/data", offset=10, limit=3)
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
        code = client_service.build_photo_code(1)
        self.assertIn("bytes(data)", code)
        self.assertIn("aliyun_git.upload", code)
        self.assertNotIn('token=', code)
        self.assertNotIn('domain=', code)


if __name__ == "__main__":
    unittest.main()
