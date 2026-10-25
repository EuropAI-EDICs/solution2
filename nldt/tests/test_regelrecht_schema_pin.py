from __future__ import annotations
import hashlib
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "nldt/simulation/regelrecht/schema"
PIN = SCHEMA_DIR / "pin.json"
SCHEMA = SCHEMA_DIR / "regelrecht-v0.8.11.schema.json"

class SchemaPinTests(unittest.TestCase):
    def test_pin_matches_local_bytes(self):
        pin = json.loads(PIN.read_text(encoding="utf-8"))
        self.assertEqual(pin["version"], "v0.8.11")
        digest = hashlib.sha256(SCHEMA.read_bytes()).hexdigest()
        self.assertEqual(pin["sha256"], digest)
        self.assertIn("NederlandseDigitaleDienst/regelrecht", pin["sourceUrl"])
        self.assertIn("v0.8.11", pin["sourceUrl"])

    def test_schema_title_is_v0811(self):
        doc = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertIn("0.8.11", doc.get("title", ""))

if __name__ == "__main__":
    unittest.main()
