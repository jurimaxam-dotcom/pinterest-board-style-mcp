#!/usr/bin/env python3
"""Tests fuer scripts/extract_facts.py — deterministische Pixel-Fakten (Pillow).

Laeuft im Gate via `uv run --with pillow` (test.sh). Unter plain python3 ohne Pillow
werden die Tests uebersprungen — die uv-Stufe des Gates fuehrt sie verbindlich aus.
Synthetische PNG-Fixtures (verlustfrei) machen die Erwartungen exakt pruefbar.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def color_close(hex_a, hex_b, tol=40):
    a, b = hex_to_rgb(hex_a), hex_to_rgb(hex_b)
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5 <= tol


def make_split_image(path, top_rgb, bottom_rgb, size=(120, 120)):
    img = Image.new("RGB", size, top_rgb)
    for y in range(size[1] // 2, size[1]):
        for x in range(size[0]):
            img.putpixel((x, y), bottom_rgb)
    img.save(path, "PNG")


def make_solid_image(path, rgb, size=(120, 120)):
    Image.new("RGB", size, rgb).save(path, "PNG")


@unittest.skipUnless(HAS_PIL, "Pillow fehlt — laeuft in der uv-Stufe des Gates")
class TestExtractFacts(unittest.TestCase):
    def setUp(self):
        import extract_facts as ef
        self.ef = ef
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_palette_finds_dominant_color(self):
        make_solid_image(self.dir / "01.png", (200, 40, 30))
        make_solid_image(self.dir / "02.png", (200, 40, 30))
        make_solid_image(self.dir / "03.png", (20, 40, 200))
        facts = self.ef.extract_facts(self.dir)
        self.assertTrue(facts["palette"], "Palette darf nicht leer sein")
        top = facts["palette"][0]
        self.assertTrue(color_close(top["hex"], "#c8281e"),
                        f"dominante Farbe erwartet ~#c8281e, bekam {top['hex']}")
        self.assertGreater(top["dominance"], 0.5)
        hexes = [p["hex"] for p in facts["palette"]]
        self.assertTrue(any(color_close(h, "#1428c8") for h in hexes),
                        f"Blau-Cluster fehlt in Palette: {hexes}")

    def test_dominance_values_are_shares(self):
        make_solid_image(self.dir / "01.png", (255, 255, 255))
        facts = self.ef.extract_facts(self.dir)
        total = sum(p["dominance"] for p in facts["palette"])
        self.assertAlmostEqual(total, 1.0, places=2)
        for p in facts["palette"]:
            self.assertRegex(p["hex"], r"^#[0-9a-f]{6}$")

    def test_edge_colors_per_image(self):
        make_split_image(self.dir / "01.png", (200, 30, 30), (30, 30, 200))
        facts = self.ef.extract_facts(self.dir)
        edges = facts["edgeColors"]["01"]
        self.assertTrue(color_close(edges["top"], "#c81e1e"),
                        f"top erwartet ~#c81e1e, bekam {edges['top']}")
        self.assertTrue(color_close(edges["bottom"], "#1e1ec8"),
                        f"bottom erwartet ~#1e1ec8, bekam {edges['bottom']}")

    def test_temperature_warm_and_cool(self):
        make_solid_image(self.dir / "01.png", (220, 120, 60))
        self.assertEqual(self.ef.extract_facts(self.dir)["metrics"]["temperature"], "warm")
        make_solid_image(self.dir / "01.png", (50, 90, 200))
        self.assertEqual(self.ef.extract_facts(self.dir)["metrics"]["temperature"], "cool")

    def test_saturation_and_contrast_extremes(self):
        make_solid_image(self.dir / "01.png", (128, 128, 128))
        facts = self.ef.extract_facts(self.dir)
        self.assertEqual(facts["metrics"]["saturation"], "low")
        self.assertEqual(facts["metrics"]["contrast"], "low")
        make_solid_image(self.dir / "01.png", (255, 0, 0))
        self.assertEqual(self.ef.extract_facts(self.dir)["metrics"]["saturation"], "high")
        make_split_image(self.dir / "01.png", (255, 255, 255), (0, 0, 0))
        self.assertEqual(self.ef.extract_facts(self.dir)["metrics"]["contrast"], "high")

    def test_deterministic_output(self):
        make_split_image(self.dir / "01.png", (200, 30, 30), (30, 30, 200))
        make_solid_image(self.dir / "02.png", (240, 230, 210))
        a = json.dumps(self.ef.extract_facts(self.dir), sort_keys=True)
        b = json.dumps(self.ef.extract_facts(self.dir), sort_keys=True)
        self.assertEqual(a, b)

    def test_cli_writes_facts_json(self):
        make_solid_image(self.dir / "01.png", (200, 40, 30))
        out = self.dir / "facts.json"
        rc = self.ef.main([str(self.dir), "-o", str(out)])
        self.assertEqual(rc, 0)
        facts = json.loads(out.read_text(encoding="utf-8"))
        self.assertIn("palette", facts)
        self.assertIn("metrics", facts)
        self.assertIn("edgeColors", facts)
        self.assertEqual(facts["source"]["image_count"], 1)

    def test_empty_dir_errors(self):
        with self.assertRaises(self.ef.FactsError):
            self.ef.extract_facts(self.dir)


if __name__ == "__main__":
    unittest.main()
