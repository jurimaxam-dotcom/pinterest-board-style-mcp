#!/usr/bin/env python3
"""Tests fuer den erweiterten Design-System-Export mit Bild-Assets."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import tokens_to_ds as tds  # noqa: E402

FIX = REPO / "tests" / "fixtures"
RICH_TOKENS = FIX / "rich.tokens.json"
RICH_IMAGES = FIX / "cache" / "rich-demo"


class TestDesignSystemAssets(unittest.TestCase):
    def test_build_copies_images_when_dir_supplied(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            doc = json.loads(RICH_TOKENS.read_text(encoding="utf-8"))
            tds.build(doc, "", out, images_dir=RICH_IMAGES)
            images_dir = out / "images"
            self.assertTrue(images_dir.is_dir())
            self.assertEqual(
                [p.name for p in sorted(images_dir.iterdir(), key=lambda p: p.name)],
                ["01.jpg", "02.jpg", "03.jpg"],
            )
            for name in ("01.jpg", "02.jpg", "03.jpg"):
                self.assertEqual((images_dir / name).read_bytes(), (RICH_IMAGES / name).read_bytes())

    def test_main_errors_for_missing_images_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            missing = Path(tmp) / "missing-images"
            self.assertEqual(tds.main([str(RICH_TOKENS), "--out", str(out), "--images", str(missing)]), 2)


if __name__ == "__main__":
    unittest.main()
