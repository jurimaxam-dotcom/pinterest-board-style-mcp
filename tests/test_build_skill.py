#!/usr/bin/env python3
"""Gate fuer Stufe 2 — build_style_skill.py (deterministisches Paket-Assembly, stdlib, KEIN Netz).

Prueft die in der Spec gelisteten Invarianten gegen eine reiche Token-Fixture
(tests/fixtures/rich.tokens.json + tests/fixtures/cache/rich-demo/) sowie graceful
degradation gegen die committeten Beispiel-Tokens ohne die neuen Stufe-1-Felder.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import build_style_skill as bss   # noqa: E402

FIX = REPO / "tests" / "fixtures"
RICH_TOKENS = FIX / "rich.tokens.json"
RICH_CACHE = FIX / "cache" / "rich-demo"
MINIMAL_TOKENS = REPO / "examples" / "homedepot-bath-ideas-and-inspiration.tokens.json"

EXPECTED_FILES = [
    "SKILL.md", "readme.md", "styles.css", "README-INSTALL.md",
    "tokens/colors.css", "tokens/typography.css", "tokens/radius.css",
    "tokens/spacing.css", "tokens/shadow.css",
]


def _build(out_dir, tokens=RICH_TOKENS, cache=RICH_CACHE):
    return bss.build_skill(tokens, cache, out_dir)


class TestPackageStructure(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "pkg"
        _build(self.out)

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_expected_files_exist(self):
        for rel in EXPECTED_FILES:
            self.assertTrue((self.out / rel).is_file(), f"fehlt: {rel}")

    def test_images_dir_not_empty(self):
        imgs = list((self.out / "images").glob("*.jpg"))
        self.assertGreaterEqual(len(imgs), 1, "images/ ist leer")

    def test_images_copied_byte_for_byte(self):
        for src in sorted(RICH_CACHE.glob("*.jpg")):
            dst = self.out / "images" / src.name
            self.assertTrue(dst.is_file(), f"Bild nicht kopiert: {src.name}")
            self.assertEqual(dst.read_bytes(), src.read_bytes())

    def test_styles_css_only_imports(self):
        for line in (self.out / "styles.css").read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("/*") or s.startswith("*"):
                continue
            self.assertTrue(s.startswith("@import"), f"Nicht-@import-Zeile in styles.css: {s!r}")

    def test_colors_css_has_core_roles_and_accent_palette(self):
        css = (self.out / "tokens" / "colors.css").read_text(encoding="utf-8")
        for role in ("background", "surface", "text", "primary", "accent", "muted"):
            self.assertIn(f"--color-{role}:", css, f"Kernrolle fehlt: --color-{role}")
        self.assertIn("--accent-0:", css, "Akzent-Palette (--accent-*) fehlt in colors.css")

    def test_typography_css_has_font_vars_with_fallback_stack(self):
        css = (self.out / "tokens" / "typography.css").read_text(encoding="utf-8")
        self.assertIn("--font-heading:", css)
        self.assertIn("--font-body:", css)
        # Fallback-Stack = mehrere durch Komma getrennte Familien
        heading_line = next(l for l in css.splitlines() if "--font-heading:" in l)
        self.assertIn(",", heading_line, "Font-Stack ohne Fallback-Familien")

    def test_readme_renders_motif_inventory(self):
        md = (self.out / "readme.md").read_text(encoding="utf-8")
        self.assertIn("Hairpin-Bein", md, "Motiv-Name fehlt im readme")
        self.assertIn("decoration", md, "UI-Rolle des Motivs fehlt im readme")

    def test_skill_md_frontmatter_valid(self):
        text = (self.out / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"), "SKILL.md beginnt nicht mit Frontmatter")
        block = text.split("---\n", 2)[1]
        self.assertRegex(block, r"(?m)^name:\s*\S+")
        self.assertRegex(block, r"(?m)^description:\s*\S+")


class TestDeterminism(unittest.TestCase):
    def test_byte_deterministic_across_two_builds(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            pa, pb = Path(a) / "pkg", Path(b) / "pkg"
            _build(pa)
            _build(pb)
            files_a = sorted(p.relative_to(pa) for p in pa.rglob("*") if p.is_file())
            files_b = sorted(p.relative_to(pb) for p in pb.rglob("*") if p.is_file())
            self.assertEqual(files_a, files_b, "Unterschiedliche Dateilisten")
            for rel in files_a:
                self.assertEqual((pa / rel).read_bytes(), (pb / rel).read_bytes(),
                                 f"Nicht-deterministisch: {rel}")


class TestGracefulDegradation(unittest.TestCase):
    """Alte Tokens ohne webfonts/accentPalette/motifs duerfen NICHT crashen."""
    def test_minimal_tokens_build_without_rich_fields(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "pkg"
            # Cache irrelevant fuer die alten Tokens -> die rich-Fixture-Bilder reichen
            bss.build_skill(MINIMAL_TOKENS, RICH_CACHE, out)
            for rel in EXPECTED_FILES:
                self.assertTrue((out / rel).is_file(), f"fehlt bei minimal: {rel}")
            # Font-Vars werden aus typography.classification abgeleitet, auch ohne webfonts
            typo = (out / "tokens" / "typography.css").read_text(encoding="utf-8")
            self.assertIn("--font-body:", typo)


class TestCli(unittest.TestCase):
    def test_broken_json_exits_2(self):
        with tempfile.TemporaryDirectory() as t:
            bad = Path(t) / "bad.tokens.json"
            bad.write_text("{ this is not json", encoding="utf-8")
            self.assertEqual(bss.main([str(bad), str(RICH_CACHE), str(Path(t) / "pkg")]), 2)

    def test_missing_args_exits_2(self):
        self.assertEqual(bss.main([]), 2)

    def test_valid_cli_run_exits_0(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(
                bss.main([str(RICH_TOKENS), str(RICH_CACHE), str(Path(t) / "pkg")]), 0)


if __name__ == "__main__":
    unittest.main()
