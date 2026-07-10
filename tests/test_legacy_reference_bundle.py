from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


REFERENCE_ROOT = Path(__file__).resolve().parents[1] / "references" / "legacy_0324"


class LegacyReferenceBundleTests(unittest.TestCase):
    def test_files_match_source_manifest(self) -> None:
        manifest = json.loads(
            (REFERENCE_ROOT / "SOURCE_MANIFEST.json").read_text(encoding="utf-8")
        )

        for item in manifest["files"]:
            path = REFERENCE_ROOT / item["path"]
            with self.subTest(path=item["path"]):
                self.assertTrue(path.is_file())
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(), item["sha256"])

    def test_old_device_configs_are_not_copied(self) -> None:
        self.assertEqual(list(REFERENCE_ROOT.rglob("config_plane_*.py")), [])


if __name__ == "__main__":
    unittest.main()
