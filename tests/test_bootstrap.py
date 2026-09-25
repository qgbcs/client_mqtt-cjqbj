import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app" / "src" / "main" / "python"))

import bootstrap


class BootstrapTests(unittest.TestCase):
    def test_writable_feature_overrides_builtin_and_reloads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "feature_dynamic.py"
            path.write_text("def run(value):\n    return 'v1:' + value\n", encoding="utf-8")
            bootstrap.init_env(directory)
            self.assertEqual(bootstrap.call_feature("dynamic", "run", "ok"), "v1:ok")
            path.write_text("def run(value):\n    return 'v2:' + value\n", encoding="utf-8")
            self.assertEqual(bootstrap.call_feature("dynamic", "run", "ok"), "v2:ok")

    def test_feature_name_is_restricted(self):
        with self.assertRaises(ValueError):
            bootstrap.load_feature("../unsafe")


if __name__ == "__main__":
    unittest.main()
